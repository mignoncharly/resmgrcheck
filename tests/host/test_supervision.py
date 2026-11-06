"""Recorded actual-QNX vectors and explicitly synthetic evidence mutations."""
import copy
import json
from pathlib import Path
import unittest
from resmgrcheck.contracts import canonical,load,loads
from resmgrcheck.evaluator import evaluate,evaluate_persistent
from resmgrcheck.outcomes import infrastructure_error

ROOT=Path(__file__).resolve().parents[2]/'docs/evidence/phase4'

class Supervision(unittest.TestCase):
    def vector(self,tag):
        return load(ROOT/(tag+'-plan.json')),(ROOT/(tag+'-events.jsonl')).read_bytes(),load(ROOT/(tag+'-status.json'))
    def test_native_matrix_exact_outcomes(self):
        index=json.loads((ROOT/'index.json').read_text())
        self.assertEqual(len(index['cases']),22)
        for case in index['cases']:
            plan,raw,status=self.vector(case['case']);result=evaluate_persistent(plan,raw,status).data
            self.assertEqual(result['verdict'],case['verdict'],case['case'])
            self.assertEqual(result['reasons'],case['reasons'],case['case'])
            if result['verdict']=='PASS':self.assertEqual(result['completion'],'complete')
    def test_service_failures_survive_cleanup_error(self):
        result=evaluate_persistent(*self.vector('cleanup')).data
        assertions={a['id']:a['verdict'] for a in result['assertions']}
        self.assertEqual(assertions['cancellation_not_completed'],'FAIL')
        self.assertEqual(assertions['pending_state_cleanup'],'FAIL')
        self.assertEqual(assertions['cleanup_failed'],'ERROR')
    def test_service_failure_survives_later_malformed_or_truncated_evidence(self):
        plan,raw,_=self.vector('late')
        records=raw.splitlines(keepends=True)
        cut=next(i for i,line in enumerate(records) if b'"event":"invalid_frame"' in line)
        for suffix in (b'{bad}\n',b'{"kind":'):
            result=evaluate(plan,b''.join(records[:cut])+suffix).data
            self.assertEqual(result['verdict'],'ERROR')
            self.assertIn('cancellation_not_completed',result['reasons'])
            self.assertTrue(any(a['id']=='cancellation_not_completed' and a['verdict']=='FAIL' for a in result['assertions']))
    def test_unknown_ownership_never_signalled_and_dependent_not_run(self):
        _,raw,status=self.vector('ownership');records=[loads(s) for s in raw.splitlines()]
        unknown={r['data']['child_pid'] for r in records if r.get('event')=='problem' and r['data']['reason']=='ownership_unknown'}
        self.assertTrue(unknown)
        self.assertFalse(any(r.get('event')=='signal_sent' and r['data']['child_pid'] in unknown for r in records))
        self.assertFalse(status['cleanup_ok'])
        for tag in ('dependent','owned_dep'):
            plan,raw,status=self.vector(tag)
            self.assertEqual(evaluate_persistent(plan,raw,status).data['verdict'],'NOT_RUN')
            self.assertFalse(any(loads(s).get('event')=='spawned' for s in raw.splitlines()))
    def test_primary_evidence_loss_cannot_pass(self):
        for tag in ('sink','quota'):
            plan,_,status=self.vector(tag)
            primary=(ROOT/(tag+'-primary.jsonl')).read_bytes()
            self.assertEqual(evaluate_persistent(plan,primary,status).data['verdict'],'ERROR')
    def test_synthetic_incomplete_final_or_status_control_cannot_pass(self):
        plan,raw,status=self.vector('normal');records=[loads(s) for s in raw.splitlines()]
        records[-1]['data']['flow_complete']=0
        self.assertEqual(evaluate(plan,b''.join(canonical(d)+b'\n' for d in records)).data['verdict'],'ERROR')
        status['lab_control']='other'
        self.assertEqual(evaluate_persistent(plan,raw,status).data['verdict'],'ERROR')
    def test_synthetic_restarted_instance_cannot_satisfy_health(self):
        plan,raw,_=self.vector('normal');records=[loads(s) for s in raw.splitlines()]
        ready=copy.deepcopy(next(r for r in records if r.get('event')=='ready'))
        at=next(i for i,r in enumerate(records) if r.get('event')=='result' and r['data']['operation']=='health')
        # A second readiness publication, even at the same path, invalidates identity.
        ready['ns']=records[at]['ns'];records.insert(at,ready)
        seq=0
        for r in records:
            if r.get('producer')=='fixture':seq+=1;r['seq']=seq
        result=evaluate(plan,b''.join(canonical(d)+b'\n' for d in records)).data
        self.assertEqual(result['verdict'],'ERROR');self.assertIn('service_interference',result['reasons'])
    def test_target_wide_failure_never_claims_cleanup(self):
        plan,_,_=self.vector('normal')
        result=infrastructure_error(plan,'target_unreachable',b'partial').data
        self.assertEqual(result['verdict'],'ERROR')
        self.assertEqual(result['completion'],'incomplete')
        self.assertEqual(next(a for a in result['assertions'] if a['id']=='remote_cleanup')['verdict'],'NOT_RUN')

if __name__=='__main__':unittest.main()
