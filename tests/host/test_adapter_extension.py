"""Adapter ABI/profile and historical evidence compatibility. No host-native claims."""
import copy
from pathlib import Path
import unittest
from resmgrcheck.contracts import Profile,Invalid,load,canonical
from resmgrcheck.deployment import Deployment,engine_info,native_builds
from resmgrcheck.transport import Unsupported
from resmgrcheck.workflow import suite_profiles,inspect_execution

ROOT=Path(__file__).resolve().parents[2]

class AdapterExtensionTests(unittest.TestCase):
    def test_mailbox_contract_preserves_message_custody_independently_of_waiters(self):
        profile=Profile.parse(load(ROOT/'profiles/mailbox.json'))
        self.assertEqual(profile.data['expectations']['state_after'],{'message_exists':1,'message_ready':0,'acknowledgements':0})
        expanded=suite_profiles(profile,'lifecycle')
        self.assertEqual(len(expanded),6);self.assertEqual(expanded[3].data['suite']['cycles'],20)
        self.assertEqual(expanded[4].data['expectations']['next_health'],{'channel':1,'value':8})
        self.assertEqual(expanded[4].data['expectations']['state_after']['acknowledgements'],0)

    def test_version_parameters_and_missing_predicates_are_rejected(self):
        for change in [lambda p:p['adapter'].update(abi=2),lambda p:p['operation']['parameters'].update(channel=2),
                       lambda p:p['expectations']['state_after'].pop('acknowledgements')]:
            profile=load(ROOT/'profiles/mailbox.json');change(profile)
            with self.assertRaises(Invalid):Profile.parse(profile)

    def test_original_two_adapter_deployment_and_genuine_saved_results_still_validate(self):
        original=load(ROOT/'tests/data/deployment-v1.json');parsed=Deployment.parse(original)
        self.assertEqual(parsed.data,original);self.assertEqual(set(parsed.data['candidates']),{'sensor-v1','job-v1'})
        request,result,_=inspect_execution(ROOT/'docs/evidence/phase10/executions/p10demo2-normal')
        self.assertEqual(result['cases'][0]['verdict'],'PASS')

    def test_build_missing_an_adapter_stays_unsupported_and_cannot_imply_capability(self):
        original=load(ROOT/'tests/data/deployment-v1.json')
        with self.assertRaises(Unsupported):native_builds(original,'mailbox-v1')
        value={'kind':'engine-info','schema_version':1,'adapter_abi':1,'adapters':[
            {'id':'sensor-v1','fixture':'sensor-v1-fixture','capabilities':['state','health']},
            {'id':'job-v1','fixture':'job-v1-fixture','capabilities':['state','health']}]}
        self.assertNotIn('mailbox-v1',engine_info(canonical(value)))

    def test_unknown_adapter_files_and_incomplete_deployment_are_rejected(self):
        for change in [lambda d:d['candidates'].pop('job-v1'),lambda d:d['files'].update({'unknown-plugin':{'sha256':'a'*64,'bytes':1}}),
                       lambda d:d['candidates'].update({'arbitrary-v1':{}})]:
            original=load(ROOT/'tests/data/deployment-v1.json');change(original)
            with self.assertRaises(Invalid):Deployment.parse(original)
