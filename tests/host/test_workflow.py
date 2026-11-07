"""Host-only CLI/planning/containment checks; no fabricated QNX execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from resmgrcheck.contracts import Invalid, Profile, canonical, load
from resmgrcheck.deployment import Deployment, engine_info
from resmgrcheck.transport import Target, Transport, TransportError
from resmgrcheck.workflow import (Request, finalize, initialize, inspect_execution,
                                 make_request, run_id, suite_profiles)

ROOT = Path(__file__).resolve().parents[2]


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.path = Path(self.temp.name)
        self.deployment = Deployment.parse(load(ROOT / 'tests/data/deployment-v1.json'))
        config = load(ROOT / 'config/targets.example.json')
        config['targets']['lab']['recipe_id'] = self.deployment.data['recipe_id']
        config['targets']['lab']['ssh_alias'] = 'resmgrcheck-test-nonexistent'
        self.configuration = self.path / 'target.json'; self.configuration.write_bytes(canonical(config))
        self.target = Target.read('lab', self.configuration)
        self.profile = Profile.parse(load(ROOT / 'profiles/job.json'))

    def tearDown(self): self.temp.cleanup()

    def test_lifecycle_covers_every_required_family_and_twenty_cycles(self):
        profiles = suite_profiles(self.profile, 'lifecycle')
        self.assertEqual([p.data['suite']['required'][0] for p in profiles],
                         ['timeout', 'signal', 'departure', 'repeat', 'complete-first', 'cancel-first'])
        self.assertEqual(profiles[3].data['suite']['cycles'], 20)
        self.assertEqual(profiles[3].data['suite']['reset'], 'same-instance')
        self.assertEqual(profiles[4].data['expectations']['state_after'], {'job_exists': 1, 'job_ready': 1})
        self.assertEqual(profiles[4].data['expectations']['next_health'], {'job_id': 1, 'value': 421})

    def test_suite_does_not_discard_missing_required_capability(self):
        p = load(ROOT / 'profiles/sensor-unsupported-capability.json')
        for profile in suite_profiles(Profile.parse(p), 'lifecycle'):
            self.assertIn('error-probe', profile.data['capabilities']['required'])

    def test_strict_ids_and_request_contract_source_bindings(self):
        for value in ('../x', '-bad', 'x;id', 'x' * 41, 'x/y'):
            with self.assertRaises(Invalid): run_id(value)
        request = make_request(self.target, self.profile, 'lifecycle', 'fixed', self.deployment, 'host-test')
        for mutation in (lambda d: d['cases'].reverse(),
                         lambda d: d['cases'][0].update(run_id='someone-else'),
                         lambda d: d['target_identity'].update(uid=1),
                         lambda d: d.update(command='sh')):
            value = copy.deepcopy(request.data); mutation(value)
            with self.assertRaises(Invalid): Request.parse(value)

    def test_unknown_configuration_fields_and_unsafe_aliases_rejected(self):
        original = load(self.configuration)
        for change in (lambda d: d['targets']['lab'].update(ssh_alias='-oProxyCommand=id'),
                       lambda d: d['targets']['lab'].update(root='/etc'),
                       lambda d: d['targets']['lab'].update(password='not-a-real-password'),
                       lambda d: d.update(schema_version=2)):
            value = copy.deepcopy(original); change(value); self.configuration.write_bytes(canonical(value))
            with self.assertRaises(Invalid): Target.read('lab', self.configuration)

    def test_deployment_hash_and_executable_scope_cannot_be_changed_silently(self):
        for change in (lambda d: d['files']['runner'].update(sha256='0'*64),
                       lambda d: d.update(directory='/tmp/other'),
                       lambda d: d['files'].update(unknown={'sha256':'0'*64, 'bytes':1})):
            value = copy.deepcopy(self.deployment.data); change(value)
            with self.assertRaises(Invalid): Deployment.parse(value)

    def test_unknown_launch_does_not_infer_execution_or_cleanup(self):
        request = make_request(self.target, self.profile, 'lifecycle', 'fixed', self.deployment, 'host-unknown')
        output = self.path / 'partial'; state = initialize(output, request)
        state['cases']['timeout'] = 'launch-requested'; state['error'] = 'TransportError'
        summary = finalize(output, request, state)
        self.assertEqual(summary['execution_exit'], 2)
        self.assertEqual([r['verdict'] for r in summary['cases']], ['ERROR'] + ['NOT_RUN'] * 5)
        _, _, results = inspect_execution(output)
        self.assertEqual(next(a['verdict'] for a in results[0].data['assertions'] if a['id'] == 'remote_cleanup'), 'NOT_RUN')
        self.assertFalse(list(output.rglob('bundle.json')))

    def test_empty_unexecuted_required_suite_cannot_pass(self):
        request = make_request(self.target, self.profile, 'lifecycle', 'fixed', self.deployment, 'host-empty')
        output = self.path / 'empty'; state = initialize(output, request)
        value = finalize(output, request, state)
        self.assertEqual(value['execution_exit'], 3)
        self.assertTrue(all(r['verdict'] == 'NOT_RUN' for r in value['cases']))

    def test_uncollected_case_cannot_be_relabelled_pass(self):
        request = make_request(self.target, self.profile, 'profile', 'fixed', self.deployment, 'host-tamper')
        output = self.path / 'tamper'; state = initialize(output, request); finalize(output, request, state)
        path = output / 'result.json'; value = load(path); value['cases'][0]['verdict'] = 'PASS'; path.write_bytes(canonical(value))
        with self.assertRaises(Invalid): inspect_execution(output)

    def test_occupied_output_keeps_existing_bytes_without_contacting_target(self):
        output = self.path / 'occupied'; output.mkdir(); (output / 'unrelated').write_bytes(b'preserve')
        p = subprocess.run([sys.executable, '-m', 'resmgrcheck', 'run', '--target', 'lab', '--config', str(self.configuration),
                            '--profile', 'profiles/sensor.json', '--out', str(output)], capture_output=True, timeout=5, cwd=ROOT)
        self.assertEqual(p.returncode, 2); self.assertIn(b'already exists', p.stderr)
        self.assertEqual({f.name: f.read_bytes() for f in output.iterdir()}, {'unrelated': b'preserve'})

    def test_field_specific_errors_and_no_default_traceback(self):
        profile = load(ROOT / 'profiles/job.json'); profile['timing']['operation_ms'] = True
        path = self.path / 'invalid.json'; path.write_bytes(canonical(profile))
        p = subprocess.run([sys.executable, '-m', 'resmgrcheck', 'validate', str(path)], capture_output=True, cwd=ROOT)
        self.assertEqual(p.returncode, 2); self.assertIn(b'timing.operation_ms', p.stderr)
        self.assertNotIn(b'Traceback', p.stderr)

    def test_external_scope_requires_explicit_read_only_contract(self):
        profile = load(ROOT / 'profiles/job-external.json'); Profile.parse(profile)
        for change in (lambda p: p['service'].update(mode='managed-fixture'),
                       lambda p: p['expectations'].update(require_unblock=True),
                       lambda p: p['suite'].update(reset='new-instance')):
            altered = copy.deepcopy(profile); change(altered)
            with self.assertRaises(Invalid): Profile.parse(altered)

    def test_native_capability_description_is_narrow(self):
        entries = [{'id': k, 'fixture': r.fixture, 'capabilities': ['state', 'health']} for k, r in __import__('resmgrcheck.registrations', fromlist=['REGISTRY']).REGISTRY.items()]
        value = {'kind': 'engine-info', 'schema_version': 1, 'adapter_abi': 1, 'adapters': entries}
        self.assertEqual(set(engine_info(canonical(value))), {'sensor-v1', 'job-v1'})
        entries[1] = entries[0]
        with self.assertRaises(Invalid): engine_info(canonical(value))

    def test_host_transport_timeout_reaps_only_its_owned_local_child(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        try:
            transport = Transport(self.target); started = time.monotonic()
            with self.assertRaises(TransportError):
                transport.call([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=.1)
            self.assertLess(time.monotonic() - started, 2)
            self.assertIsNotNone(transport.record[-1]['exit']); self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate(); unrelated.wait(timeout=2)

    def test_fast_completed_transport_cannot_hide_oversized_stderr(self):
        transport = Transport(self.target)
        with self.assertRaises(Invalid):
            transport.call([sys.executable, '-c', 'import os; os.write(2, b"x" * (1024 * 1024 + 1))'])
        self.assertIsNotNone(transport.record[-1]['exit'])
        self.assertEqual(transport.record[-1]['exit'], 0)
        self.assertNotEqual(transport.record[-1]['error'], None)

    def test_offline_report_cannot_replace_execution_inputs_or_results(self):
        from resmgrcheck.reports import report
        request = make_request(self.target, self.profile, 'profile', 'fixed', self.deployment, 'host-report')
        output = self.path / 'report'; state = initialize(output, request); finalize(output, request, state)
        for name in ('request.json', 'replay.json', 'result.json', 'cases/timeout/result.json'):
            before = (output / name).read_bytes()
            with self.assertRaises(Invalid): report(output, output / name)
            self.assertEqual((output / name).read_bytes(), before)
        report(output, output / 'report.html')
        self.assertIn('NOT_RUN', (output / 'report.html').read_text())

    def test_unowned_signal_evidence_never_passes_or_erases_service_failures(self):
        from resmgrcheck.evaluator import evaluate
        from resmgrcheck.contracts import loads
        root = ROOT / 'docs/evidence/phase5-clean-lifecycle'
        for tag in ('sensor-timeout-corrected', 'sensor-timeout-ignore-unblock'):
            plan = load(root / (tag + '-plan.json'))
            rows = [loads(line) for line in (root / (tag + '-events.jsonl')).read_bytes().splitlines()]
            signal_event = copy.deepcopy(next(r for r in rows if r.get('event') == 'signal_sent'))
            signal_event['data']['child_pid'] = '2147483647'; signal_event['ns'] = rows[-1]['ns']
            rows.insert(-1, signal_event)
            sequences = {}
            for row in rows[1:]:
                key = (row['producer'], row['pid']); sequences[key] = sequences.get(key, 0) + 1; row['seq'] = sequences[key]
            result = evaluate(plan, b''.join(canonical(r) + b'\n' for r in rows)).data
            self.assertEqual(result['verdict'], 'ERROR'); self.assertIn('evidence_invalid', result['reasons'])
            if 'ignore-unblock' in tag:
                self.assertIn('cancellation_not_completed', result['reasons'])
                self.assertIn('pending_state_not_released', result['reasons'])


if __name__ == '__main__': unittest.main()
