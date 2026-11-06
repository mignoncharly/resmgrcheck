"""Host-only mutations of recorded QNX evidence. Mutations are synthetic."""
import copy
import json
from pathlib import Path
import unittest
from resmgrcheck.contracts import load, loads, canonical, Invalid, Plan, EvaluatedResult, ReplayInput
from resmgrcheck.evaluator import evaluate

ROOT=Path(__file__).resolve().parents[2]/'docs/evidence/phase3'

class Evaluation(unittest.TestCase):
    def setUp(self):
        self.plan=load(ROOT/'job-corrected-plan.json')
        self.raw=(ROOT/'job-corrected-events.jsonl').read_bytes()
        self.records=[loads(s) for s in self.raw.splitlines()]
    def verdict(self, mutate):
        values=copy.deepcopy(self.records); mutate(values)
        return evaluate(self.plan,b''.join(canonical(d)+b'\n' for d in values)).data['verdict']
    def test_recorded_matrix(self):
        for tag, verdict in [('sensor-corrected','PASS'),('job-corrected','PASS'),('sensor-defect','FAIL'),('job-defect','FAIL'),('unsupported','UNSUPPORTED')]:
            p=load(ROOT/(tag+'-plan.json')); raw=(ROOT/(tag+'-events.jsonl')).read_bytes()
            result=evaluate(p,raw).data
            self.assertEqual(result['verdict'],verdict)
            EvaluatedResult.parse(result)
    def test_truncation_and_duplicate_keys(self):
        self.assertEqual(evaluate(self.plan,self.raw[:-1]).data['verdict'],'ERROR')
        self.assertEqual(evaluate(self.plan,self.raw.split(b'\n')[0]+b'\n').data['verdict'],'ERROR')
        self.assertEqual(evaluate(self.plan,self.raw.replace(b'"seq":1,',b'"seq":1,"seq":1,',1)).data['verdict'],'ERROR')
    def test_sequence_identity_types_unknown_fields(self):
        mutations=[lambda r:r[1].update(seq=99),lambda r:r[1].update(run_id='other'),
                   lambda r:r[1].update(ns=1), lambda r:r[1].update(unknown=1),
                   lambda r:r[1]['data'].update(timeout_ms=True),lambda r:r[1].update(producer='fixture')]
        for mutation in mutations: self.assertEqual(self.verdict(mutation),'ERROR')
    def test_missing_required_capability_cannot_pass(self):
        self.assertNotEqual(self.verdict(lambda r:r[0]['capabilities'].remove('pending')),'PASS')
    def test_late_pending_is_error(self):
        def change(r):
            deadline=next(x for x in r if x.get('event')=='deadline')
            for x in r:
                if x.get('event')=='pending' and x['data']['client_pid']==deadline['pid']:
                    x['ns']=str(int(deadline['data']['deadline_ns'])+1)
        self.assertEqual(self.verdict(change),'ERROR')
    def test_retained_state_is_failure(self):
        def change(r):
            next(x for x in r if x.get('event')=='control_result' and x['data']['operation']=='state')['data']['pending']=1
        self.assertEqual(self.verdict(change),'FAIL')
    def test_deleted_service_state_is_failure(self):
        def change(r):
            next(x for x in r if x.get('event')=='control_result' and x['data']['operation']=='state')['data']['facts']['job_exists']=0
        self.assertEqual(self.verdict(change),'FAIL')
    def test_devctl_errno_confusion_is_error(self):
        def change(r):
            x=next(x for x in r if x.get('event')=='result' and x['data']['operation']=='negative')
            x['data']['api_error']=x['data']['raw_errno']
        self.assertEqual(self.verdict(change),'ERROR')
    def test_wrong_health_and_cleanup_cannot_pass(self):
        def health(r): next(x for x in r if x.get('event')=='result' and x['data']['operation']=='health')['data']['facts']['value']=1
        self.assertEqual(self.verdict(health),'FAIL')
        def cleanup(r): next(x for x in r if x.get('event')=='cleanup')['data']['all_reaped']=0
        self.assertEqual(self.verdict(cleanup),'ERROR')
    def test_missing_worker_final_cannot_pass(self):
        def change(r):
            x=next(x for x in r if x.get('event')=='worker_final'); r.remove(x)
        self.assertEqual(self.verdict(change),'ERROR')
    def test_replay_and_hash_validation(self):
        replay={'kind':'replay-input','schema_version':1,'original_plan':self.plan,
                'original_event_sha256':'0'*64,'selected_builds':self.plan['builds']}
        ReplayInput.parse(replay)
        replay['original_plan']=copy.deepcopy(self.plan);replay['original_plan']['profile_sha256']='0'*64
        with self.assertRaises(Invalid): ReplayInput.parse(replay)
    def test_generic_cores_do_not_branch_on_service_names(self):
        project=ROOT.parents[2]
        for name in ('native/runner.c','native/worker.c','native/common/plan.c','native/common/result.c','native/common/persistence.c','resmgrcheck/evaluator.py'):
            text=(project/name).read_text().lower()
            self.assertNotIn('sensor',text);self.assertNotIn('job',text)

if __name__=='__main__': unittest.main()
