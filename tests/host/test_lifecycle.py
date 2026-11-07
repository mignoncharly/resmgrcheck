"""Actual Phase 5 QNX vectors; all mutated records are synthetic host checks."""
import copy
import json
from pathlib import Path
import unittest

from resmgrcheck.contracts import Invalid, Plan, Profile, canonical, load, loads
from resmgrcheck.evaluator import evaluate, evaluate_persistent

ROOT = Path(__file__).resolve().parents[2] / 'docs/evidence/phase5'


class Lifecycle(unittest.TestCase):
    def vector(self, tag):
        return (load(ROOT / (tag + '-plan.json')),
                (ROOT / (tag + '-events.jsonl')).read_bytes(),
                load(ROOT / (tag + '-status.json')))

    def alter(self, tag, mutate):
        plan, raw, _ = self.vector(tag)
        rows = [loads(line) for line in raw.splitlines()]
        mutate(rows)
        sequences = {}
        for row in rows[1:]:
            key = (row['producer'], row['pid'])
            sequences[key] = sequences.get(key, 0) + 1
            row['seq'] = sequences[key]
        return evaluate(plan, b''.join(canonical(r) + b'\n' for r in rows)).data

    def test_actual_complete_native_matrix(self):
        index = json.loads((ROOT / 'index.json').read_text())
        self.assertEqual(len(index['cases']), 40)
        self.assertFalse(index['raw_debug_only'])
        for case in index['cases']:
            result = evaluate_persistent(*self.vector(case['case'])).data
            self.assertEqual((result['verdict'], result['reasons']),
                             (case['verdict'], case['reasons']), case['case'])

    def test_twenty_cycles_same_instance_fresh_clients_and_retained_job(self):
        for service in ('sensor', 'job'):
            plan, raw, status = self.vector(service + '-repeat-corrected')
            rows = [loads(line) for line in raw.splitlines()]
            result = evaluate_persistent(plan, raw, status).data
            self.assertEqual([c['verdict'] for c in result['cycles']], ['PASS'] * 20)
            self.assertEqual(len([r for r in rows if r.get('event') == 'ready']), 1)
            timers = [r for r in rows if r.get('event') == 'deadline']
            self.assertEqual(len({r['pid'] for r in timers}), 20)
            states = [r for r in rows if r.get('event') == 'control_result' and r['data']['operation'] == 'state']
            self.assertEqual([r['data']['unblocks'] for r in states], list(range(1, 21)))
            self.assertTrue(all(r['data']['pending'] == 0 for r in states))
            if service == 'job':
                self.assertTrue(all(r['data']['facts'] == {'job_exists': 1, 'job_ready': 0} for r in states))

    def test_accumulation_stops_without_erasing_earlier_cycles(self):
        for service in ('sensor', 'job'):
            result = evaluate_persistent(*self.vector(service + '-repeat-retain-third')).data
            self.assertEqual([c['verdict'] for c in result['cycles']], ['PASS', 'PASS', 'FAIL'] + ['NOT_RUN'] * 17)
            self.assertIn('pending_state_not_released', result['cycles'][2]['reasons'])

    def test_unknown_probe_state_stops_and_placeholder_is_not_state_evidence(self):
        for service in ('sensor', 'job'):
            plan, raw, status = self.vector(service + '-repeat-corrected-probe')
            result = evaluate_persistent(plan, raw, status).data
            self.assertEqual([c['verdict'] for c in result['cycles']], ['PASS', 'ERROR'] + ['NOT_RUN'] * 18)
            rows = [loads(line) for line in raw.splitlines()]
            end = next(r for r in rows if r.get('event') == 'cycle_end' and r['cycle'] == 2)
            self.assertEqual(end['data']['state_observed'], 0)
            self.assertFalse(any(a['id'] == 'pending_state_cleanup' and a['verdict'] == 'PASS' for a in result['cycles'][1]['assertions']))

    def test_cleanup_failure_retains_cycle_failure_and_separate_recovery(self):
        for service in ('sensor', 'job'):
            tag = service + '-repeat-ignore-unblock-cleanup'
            result = evaluate_persistent(*self.vector(tag)).data
            self.assertEqual(result['verdict'], 'ERROR')
            self.assertEqual(result['cycles'][0]['verdict'], 'FAIL')
            self.assertIn('cleanup_failed', result['reasons'])
            self.assertIn('cancellation_not_completed', result['reasons'])
            self.assertFalse(self.vector(tag)[2]['cleanup_ok'])
            self.assertEqual(load(ROOT / (tag + '-recovery.json'))['all_reaped'], 1)

    def test_successful_kill_request_is_not_observed_departure(self):
        for service in ('sensor', 'job'):
            plan, raw, status = self.vector(service + '-departure-ignore-unblock')
            result = evaluate_persistent(plan, raw, status).data
            self.assertEqual(result['reasons'], ['departure_unobserved'])
            self.assertEqual(result['verdict'], 'ERROR')
            self.assertTrue(status['cleanup_ok'])  # Later reap cannot meet earlier bound.
            self.assertEqual(next(a for a in result['assertions'] if a['id'] == 'fresh_client_health')['verdict'], 'NOT_RUN')

    def test_descriptor_and_final_ocb_defaults_are_required(self):
        def missing_default(rows):
            pending = next(r for r in rows if r.get('event') == 'operation_armed' and r['data']['operation'] == 'depart')
            ocb = next(r['data']['ocb'] for r in rows if r.get('event') == 'request_ocb' and r['data']['client_pid'] == pending['pid'])
            rows.remove(next(r for r in rows if r.get('event') == 'close_dup_default' and r['data']['ocb'] == ocb))
        result = self.alter('job-departure-corrected', missing_default)
        self.assertEqual(result['verdict'], 'ERROR')
        self.assertIn('ocb_lifetime_unestablished', result['reasons'])

    def test_synthetic_close_marker_must_match_receive_id(self):
        def change(rows):
            next(r for r in rows if r.get('event') == 'close_dup')['data']['synthetic'] = 1
        self.assertEqual(self.alter('sensor-departure-corrected', change)['verdict'], 'ERROR')

    def test_missing_wait_status_cannot_establish_death(self):
        def change(rows):
            pid = next(r['pid'] for r in rows if r.get('event') == 'operation_armed' and r['data']['operation'] == 'depart')
            rows.remove(next(r for r in rows if r.get('event') == 'process_exit' and r['data']['child_pid'] == pid))
        self.assertEqual(self.alter('job-departure-corrected', change)['verdict'], 'ERROR')

    def test_counter_reset_is_detected(self):
        def change(rows):
            next(r for r in rows if r.get('event') == 'control_result' and r['data']['operation'] == 'state' and r['cycle'] == 2)['data']['unblocks'] = 0
        result = self.alter('job-repeat-corrected', change)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('counter_reset', result['reasons'])

    def test_required_completion_barrier_cannot_be_missing(self):
        def change(rows):
            rows.remove(next(r for r in rows if r.get('event') == 'barrier_wait'))
        result = self.alter('job-complete-first-corrected', change)
        self.assertEqual(result['verdict'], 'ERROR')
        self.assertIn('ordering_unestablished', result['reasons'])

    def test_stale_notification_cannot_match_later_request(self):
        def change(rows):
            next(r for r in rows if r.get('event') == 'stale_checked')['data']['matched'] = 1
        result = self.alter('sensor-cancel-first-corrected', change)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('stale_notification_unsafe', result['reasons'])

    def test_stale_payload_cannot_satisfy_fresh_request(self):
        def change(rows):
            pid = next(r['data']['child_pid'] for r in rows if r.get('event') == 'ordering_stage' and r['data']['name'] == 'fresh_terminal')
            next(r for r in rows if r.get('event') == 'result' and r['pid'] == pid)['data']['facts']['value'] -= 1
        result = self.alter('job-cancel-first-corrected', change)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('stale_result', result['reasons'])

    def test_missing_unmatched_notification_cannot_pass(self):
        def change(rows):
            rows[:] = [r for r in rows if r.get('event') != 'unmatched_unblock']
        self.assertNotEqual(self.alter('job-cancel-first-corrected', change)['verdict'], 'PASS')

    def test_duplicate_attempt_fails_even_when_kernel_rejects_it(self):
        result = evaluate_persistent(*self.vector('job-complete-first-duplicate-terminal')).data
        self.assertEqual(result['reasons'], ['duplicate_terminal_attempt'])
        self.assertEqual(result['verdict'], 'FAIL')

    def test_strict_family_reset_cycle_and_distinct_payload_contract(self):
        plan, _, _ = self.vector('job-repeat-corrected')
        for key, value in [('cycles', 21), ('reset', 'new-instance')]:
            p = copy.deepcopy(plan['profile']); p['suite'][key] = value
            with self.assertRaises(Invalid): Profile.parse(p)
        p = copy.deepcopy(plan); p['cycle'] = 2
        with self.assertRaises(Invalid): Plan.parse(p)
        p = copy.deepcopy(plan); p['case_id'] = 'departure'
        with self.assertRaises(Invalid): Plan.parse(p)
        order = self.vector('job-complete-first-corrected')[0]['profile']
        order['expectations']['next_health'] = order['expectations']['health']
        with self.assertRaises(Invalid): Profile.parse(order)

    def test_new_shared_paths_do_not_branch_on_service_names(self):
        project = ROOT.parents[2]
        for name in ('resmgrcheck/scenarios.py', 'native/common/scenario_v1.h'):
            content = (project / name).read_text().lower()
            self.assertNotIn('sensor', content)
            self.assertNotIn('job', content)


if __name__ == '__main__':
    unittest.main()
