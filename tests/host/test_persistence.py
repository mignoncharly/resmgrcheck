"""Host-only status mutations based on retained real QNX persistence evidence."""
import copy
from pathlib import Path
import unittest
from resmgrcheck.contracts import load, Invalid, RunStatus, RunStarted
from resmgrcheck.evaluator import evaluate_persistent

ROOT=Path(__file__).resolve().parents[2]/'docs/evidence/phase4-persistence'

class Persistence(unittest.TestCase):
    def setUp(self):
        self.plan=load(ROOT/'normal-plan.json')
        self.status=load(ROOT/'normal-status.json')
        self.raw=(ROOT/'normal-events.jsonl').read_bytes()
    def test_reconnected_native_outcomes(self):
        for name,expected in [('normal','PASS'),('disconnect','FAIL')]:
            p=load(ROOT/(name+'-plan.json'));s=load(ROOT/(name+'-status.json'))
            RunStatus.parse(s);RunStarted.parse(load(ROOT/(name+'-start.json')))
            r=evaluate_persistent(p,(ROOT/(name+'-events.jsonl')).read_bytes(),s).data
            self.assertEqual(r['verdict'],expected)
            self.assertTrue(any(a['id']=='target_completion_status' and a['verdict']=='PASS' for a in r['assertions']))
    def test_stale_owner_run_or_build_cannot_pass(self):
        for key,value in [('supervisor_pid','1'),('run_id','another'),('source_tree_sha256','0'*64),('profile_sha256','0'*64)]:
            s=copy.deepcopy(self.status);s[key]=value
            self.assertEqual(evaluate_persistent(self.plan,self.raw,s).data['verdict'],'ERROR')
    def test_running_status_cannot_validate_complete_events(self):
        s=copy.deepcopy(self.status);s.update(state='running',exit_code=-1,cleanup_ok=False)
        r=evaluate_persistent(self.plan,self.raw,s).data
        self.assertEqual(r['verdict'],'ERROR');self.assertEqual(r['completion'],'incomplete')
    def test_cleanup_failure_cannot_pass(self):
        s=copy.deepcopy(self.status);s.update(state='incomplete',exit_code=2,cleanup_ok=False,unresolved=[{'pid':'123','role':'worker'}])
        self.assertEqual(evaluate_persistent(self.plan,self.raw,s).data['verdict'],'ERROR')
    def test_status_validation_rejects_ambiguous_data(self):
        for mutation in [lambda s:s.update(cleanup_ok=1),lambda s:s.update(exit_code=True),lambda s:s.update(schema_version=2),lambda s:s.update(command='kill')]:
            s=copy.deepcopy(self.status);mutation(s)
            with self.assertRaises(Invalid):RunStatus.parse(s)
    def test_disconnected_run_keeps_service_failures_visible(self):
        p=load(ROOT/'disconnect-plan.json');s=load(ROOT/'disconnect-status.json')
        s.update(state='incomplete',exit_code=2,cleanup_ok=False)
        r=evaluate_persistent(p,(ROOT/'disconnect-events.jsonl').read_bytes(),s).data
        self.assertEqual(r['verdict'],'ERROR')
        self.assertTrue(any(a['id']=='cancellation_not_completed' and a['verdict']=='FAIL' for a in r['assertions']))

if __name__=='__main__':unittest.main()
