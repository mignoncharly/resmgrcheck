"""Actual QNX signal vectors; all altered records below are synthetic."""
import copy
import json
from pathlib import Path
import unittest
from resmgrcheck.contracts import Profile,Plan,Invalid,canonical,load,loads
from resmgrcheck.evaluator import evaluate,evaluate_persistent

ROOT=Path(__file__).resolve().parents[2]/'docs/evidence/phase5-signal'

class Signals(unittest.TestCase):
    def setUp(self):
        self.plan=load(ROOT/'job-signal-fixed-plan.json')
        self.raw=(ROOT/'job-signal-fixed-events.jsonl').read_bytes()
        self.records=[loads(s) for s in self.raw.splitlines()]
    def altered(self,mutate):
        records=copy.deepcopy(self.records);mutate(records)
        sequences={}
        for r in records[1:]:
            key=(r['producer'],r['pid']);sequences[key]=sequences.get(key,0)+1;r['seq']=sequences[key]
        return evaluate(self.plan,b''.join(canonical(r)+b'\n' for r in records)).data
    def test_actual_signal_and_affected_timeout_matrix(self):
        index=json.loads((ROOT/'index.json').read_text());self.assertEqual(len(index['cases']),11)
        for case in index['cases']:
            tag=case['case'];plan=load(ROOT/(tag+'-plan.json'));raw=(ROOT/(tag+'-events.jsonl')).read_bytes()
            result=evaluate_persistent(plan,raw,load(ROOT/(tag+'-status.json'))).data
            self.assertEqual((result['verdict'],result['reasons']),(case['verdict'],case['reasons']),tag)
    def test_strict_signal_profile_and_plan(self):
        Profile.parse(self.plan['profile'])
        for change in (lambda p:p['expectations'].update(cancel_error='ETIMEDOUT'),
                       lambda p:p['suite'].update(retry=1),lambda p:p['suite'].update(signal_mode='unknown'),
                       lambda p:p['capabilities']['required'].remove('signal')):
            profile=copy.deepcopy(self.plan['profile']);change(profile)
            with self.assertRaises(Invalid):Profile.parse(profile)
        plan=copy.deepcopy(self.plan);plan['case_id']='timeout'
        with self.assertRaises(Invalid):Plan.parse(plan)
    def test_flags_mask_retry_or_timer_cannot_be_ignored(self):
        for key in ('flags','retry','timeout_armed','masked'):
            def change(records):next(r for r in records if r.get('event')=='signal_setup')['data'][key]=1
            self.assertEqual(self.altered(change)['verdict'],'ERROR',key)
    def test_missing_handler_observation_invalidates_conclusion(self):
        def change(records):records.remove(next(r for r in records if r.get('event')=='signal_handler_observed'))
        result=self.altered(change);self.assertEqual(result['verdict'],'ERROR');self.assertIn('evidence_incomplete',result['reasons'])
    def test_signal_number_is_bound_to_target_header_value(self):
        def change(records):
            for r in records:
                if r.get('event') in ('signal_setup','signal_handler_observed','trigger_requested') or (r.get('event')=='signal_sent' and r['data']['signal']==records[0]['signal_codes']['SIGUSR1']):r['data']['signal']+=1
        self.assertEqual(self.altered(change)['verdict'],'ERROR')
    def test_unrelated_timeout_is_a_specific_service_failure(self):
        def change(records):
            value=next(r for r in records if r.get('event')=='result' and r['data']['operation']=='signal')['data']
            value.update(raw_errno=records[0]['error_codes']['ETIMEDOUT'],api_error=records[0]['error_codes']['ETIMEDOUT'],normalized='TIMEOUT',error_name='ETIMEDOUT')
        result=self.altered(change);self.assertEqual(result['verdict'],'FAIL');self.assertIn('unexpected_operation_result',result['reasons'])
    def test_signal_send_failure_cannot_establish_stimulus(self):
        def change(records):next(r for r in records if r.get('event')=='signal_sent')['data'].update(rc=-1,error=1)
        result=self.altered(change);self.assertEqual(result['verdict'],'ERROR');self.assertIn('precondition_not_established',result['reasons'])
    def test_simultaneous_kernel_timeout_invalidates_signal_case(self):
        def change(records):
            at=next(i for i,r in enumerate(records) if r.get('event')=='operation_armed');t=copy.deepcopy(records[at])
            t['event']='deadline';t['data']={'operation':'timed','deadline_ns':str(int(t['ns'])+500000000),'timeout_ms':500};records.insert(at,t)
        self.assertEqual(self.altered(change)['verdict'],'ERROR')

if __name__=='__main__':unittest.main()
