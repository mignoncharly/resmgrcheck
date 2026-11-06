"""Host-only negative contract checks; these are not QNX execution evidence."""
import copy
import unittest
from pathlib import Path
from resmgrcheck.contracts import Profile, Plan, Invalid, loads, canonical, digest

ROOT=Path(__file__).resolve().parents[2]

class Contracts(unittest.TestCase):
    def setUp(self): self.profile=loads((ROOT/'profiles/job.json').read_bytes())
    def test_reviewed_profiles(self):
        for p in (ROOT/'profiles').glob('*.json'): Profile.parse(loads(p.read_bytes()))
    def reject(self, mutate):
        d=copy.deepcopy(self.profile); mutate(d)
        with self.assertRaises(Invalid): Profile.parse(d)
    def test_versions_types_and_unknown_fields(self):
        for value in (0,2,True,'1',1.0):
            self.reject(lambda d: d.update(schema_version=value))
        self.reject(lambda d:d.update(command='sh'))
        self.reject(lambda d:d['operation'].update(command='sh'))
        self.reject(lambda d:d['timing'].update(operation_ms=True))
        self.reject(lambda d:d['timing'].update(operation_ms=0))
        self.reject(lambda d:d['timing'].update(operation_ms=999999))
    def test_unsafe_paths_and_identifiers(self):
        for path in ('/etc/passwd','/dev/resmgrcheck-../../x','/dev/resmgrcheck-x;id','/dev/resmgrcheck-x/y','/dev/resmgrcheck-x\x00'):
            self.reject(lambda d:d['service'].update(device=path))
        self.reject(lambda d:d.update(id='../../x'))
    def test_parameters_and_facts_are_registered(self):
        self.reject(lambda d:d['operation']['parameters'].update(job_id=2))
        self.reject(lambda d:d['operation']['parameters'].update(code='42'))
        self.reject(lambda d:d['expectations']['health'].update(value=True))
        self.reject(lambda d:d['expectations']['health'].update(shell=1))
        self.reject(lambda d:d['expectations'].update(state_after={}))
    def test_required_observers_and_relaxed_defect_expectation(self):
        self.reject(lambda d:d['capabilities']['required'].remove('pending'))
        self.reject(lambda d:d['capabilities']['required'].append('unknown'))
        self.reject(lambda d:d['capabilities']['optional'].append('pending'))
        self.reject(lambda d:d['expectations'].update(pending_after=1))
        self.reject(lambda d:d['expectations'].update(cancel_error='EOK'))
        self.reject(lambda d:d.update(fixture_mode='ignore-unblock'))
    def test_json_ambiguities_and_bounds(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1.0}',b'{"x":01}',b'{"x":"\\u0000"}',b'{} trailing',b'\xff',b'{"x":"\x00"}'):
            with self.subTest(raw=raw), self.assertRaises(Invalid): loads(raw)
        with self.assertRaises(Invalid): loads(b'['*20+b'0'+b']'*20)
        with self.assertRaises(Invalid): loads(b' '*1048577)
    def test_plain_valid_json_boolean_is_not_integer(self):
        self.assertIs(loads(b'{"x":true}')['x'], True)
        self.reject(lambda d:d['suite'].update(cycles=False))
    def test_bad_suite_and_abi(self):
        self.reject(lambda d:d['suite'].update(required=['timeout','timeout']))
        self.reject(lambda d:d['suite'].update(reset='arbitrary-command'))
        self.reject(lambda d:d['adapter'].update(abi=2))
        self.reject(lambda d:d['adapter'].update(id='auto-detect'))


class DependencyPin(unittest.TestCase):
    def test_vendored_files_match_reviewed_revision(self):
        import hashlib
        metadata=loads((ROOT/'third_party/cjson/REVISION.json').read_bytes())
        self.assertEqual(metadata['revision'],'c859b25da02955fef659d658b8f324b5cde87be3')
        for name,value in metadata['sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'third_party/cjson'/name).read_bytes()).hexdigest(),value)

if __name__=='__main__': unittest.main()
