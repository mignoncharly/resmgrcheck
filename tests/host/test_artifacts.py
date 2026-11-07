"""Host artifact tests over actual QNX vectors; all mutations are synthetic."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from resmgrcheck.artifacts import atomic_write, create_bundle, inspect_bundle
from resmgrcheck.contracts import Invalid, Plan, canonical, digest, load
from resmgrcheck.exports import compare, execution_exit, junit
from resmgrcheck.replay import CandidateManifest, candidate_manifest

ROOT = Path(__file__).resolve().parents[2] / 'docs/evidence/phase5-clean-lifecycle'


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)

    def tearDown(self):
        for entry in self.path.rglob('*'):
            if entry.is_dir(): entry.chmod(0o755)
            elif entry.is_file(): entry.chmod(0o644)
        self.temporary.cleanup()

    def bundle(self, tag, name=None):
        return create_bundle(self.path / (name or tag), (ROOT / (tag + '-plan.json')).read_bytes(),
                             (ROOT / (tag + '-events.jsonl')).read_bytes(),
                             (ROOT / (tag + '-status.json')).read_bytes())

    def test_failed_run_is_immutable_inspectable_artifact(self):
        bundle = self.bundle('job-timeout-ignore-unblock')
        self.assertEqual(inspect_bundle(bundle.path).result.data['verdict'], 'FAIL')
        self.assertFalse((bundle.path / 'partial.json').exists())
        self.assertEqual((bundle.path / 'observations.jsonl').read_bytes(), (ROOT / 'job-timeout-ignore-unblock-events.jsonl').read_bytes())
        with self.assertRaises(FileExistsError): self.bundle('job-timeout-ignore-unblock')

    def test_incomplete_input_keeps_raw_partial_artifact(self):
        tag = 'job-timeout-corrected'
        with self.assertRaises(Invalid):
            create_bundle(self.path / 'partial', (ROOT / (tag + '-plan.json')).read_bytes(), b'{bad}\n', (ROOT / (tag + '-status.json')).read_bytes())
        self.assertEqual((self.path / 'partial/observations.jsonl').read_bytes(), b'{bad}\n')
        self.assertTrue((self.path / 'partial/partial.json').exists())
        self.assertFalse((self.path / 'partial/bundle.json').exists())
        with self.assertRaises(Invalid): inspect_bundle(self.path / 'partial')

    def test_truncated_required_event_stream_stays_error(self):
        tag = 'job-timeout-corrected'
        raw = (ROOT / (tag + '-events.jsonl')).read_bytes()[:-1]
        bundle = create_bundle(self.path / 'truncated', (ROOT / (tag + '-plan.json')).read_bytes(), raw, (ROOT / (tag + '-status.json')).read_bytes())
        self.assertEqual(bundle.result.data['verdict'], 'ERROR')
        self.assertNotEqual(execution_exit([bundle.result]), 0)

    def test_tampering_and_unknown_members_rejected(self):
        for name in ('result.json', 'observations.jsonl', 'replay.json'):
            bundle = self.bundle('job-timeout-corrected', name + '-bundle')
            member = bundle.path / name; member.chmod(0o644)
            member.write_bytes(member.read_bytes()[:-1])
            with self.assertRaises(Invalid): inspect_bundle(bundle.path)
        bundle = self.bundle('sensor-timeout-corrected')
        bundle.path.chmod(0o755); (bundle.path / 'surprise').write_text('x')
        with self.assertRaises(Invalid): inspect_bundle(bundle.path)

    def test_duplicate_keys_and_missing_final_marker_rejected(self):
        bundle = self.bundle('job-timeout-corrected')
        marker = bundle.path / 'bundle.json'; marker.chmod(0o644)
        marker.write_bytes(marker.read_bytes().replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'))
        with self.assertRaises(Invalid): inspect_bundle(bundle.path)
        bundle.path.chmod(0o755); marker.unlink()
        with self.assertRaises(Invalid): inspect_bundle(bundle.path)

    def test_symlink_member_rejected(self):
        bundle = self.bundle('job-timeout-corrected'); bundle.path.chmod(0o755)
        member = bundle.path / 'profile.json'; saved = member.read_bytes(); member.unlink()
        external = self.path / 'external.json'; external.write_bytes(saved); member.symlink_to(external)
        with self.assertRaises(Invalid): inspect_bundle(bundle.path)

    def test_atomic_replace_keeps_previous_file_on_publish_failure(self):
        target = self.path / 'report'; target.write_bytes(b'previous')
        with patch('resmgrcheck.artifacts.os.replace', side_effect=OSError('synthetic publication failure')):
            with self.assertRaises(OSError): atomic_write(target, b'new')
        self.assertEqual(target.read_bytes(), b'previous')
        self.assertEqual([p.name for p in self.path.iterdir()], ['report'])

    def test_assertion_expected_observed_and_event_references(self):
        bundle = self.bundle('job-repeat-corrected')
        rows = [json.loads(line) for line in bundle.raw.splitlines()]
        groups = [bundle.result.data['assertions']] + [c['assertions'] for c in bundle.result.data['cycles']]
        for group in groups:
            for assertion in group:
                self.assertEqual(set(assertion), {'id', 'verdict', 'reason', 'expected', 'observed', 'event_refs'})
                self.assertEqual(assertion['observed']['events'], [rows[i] for i in assertion['event_refs']])
        state = next(a for a in bundle.result.data['cycles'][0]['assertions'] if a['id'] == 'state_facts')
        self.assertEqual(state['expected'], {'job_exists': 1, 'job_ready': 0})

    def test_mixed_junit_is_parsed_and_raw_bytes_do_not_change(self):
        tags = ('sensor-timeout-corrected', 'sensor-timeout-ignore-unblock', 'job-departure-ignore-unblock',
                'sensor-unsupported-capability-corrected', 'job-repeat-retain-third')
        bundles = [self.bundle(tag) for tag in tags]
        before = {str(b.path): {p.name: p.read_bytes() for p in b.path.iterdir()} for b in bundles}
        raw = junit(bundles); root = ET.fromstring(raw)
        self.assertGreater(int(root.get('failures')), 0)
        self.assertGreater(int(root.get('errors')), 0)
        self.assertGreater(int(root.get('skipped')), 0)
        self.assertEqual(len(root.findall("testsuite/testcase[@name='repeat.cycle20']/skipped")), 1)
        self.assertEqual(junit(bundles), raw)
        for bundle in bundles:
            self.assertEqual(before[str(bundle.path)], {p.name: p.read_bytes() for p in bundle.path.iterdir()})

    def test_all_unsupported_required_suite_has_synthetic_error(self):
        root = ET.fromstring(junit([self.bundle('sensor-unsupported-capability-corrected')]))
        self.assertEqual(int(root.get('skipped')), 1)
        self.assertEqual(int(root.get('errors')), 1)
        self.assertEqual(root.find('testsuite/testcase/error').get('type'), 'incomplete_required_coverage')

    def test_exit_precedence_keeps_required_coverage_unavailable_above_fail(self):
        passed = {'verdict': 'PASS', 'completion': 'complete'}
        failed = {'verdict': 'FAIL', 'completion': 'complete'}
        error = {'verdict': 'ERROR', 'completion': 'incomplete'}
        unsupported = {'verdict': 'UNSUPPORTED', 'completion': 'complete'}
        withheld = {'verdict': 'NOT_RUN', 'completion': 'aborted'}
        for results, code in [([], 3), ([passed], 0), ([failed], 1), ([failed, unsupported], 3),
                               ([failed, withheld], 3), ([error, unsupported, failed], 2)]:
            self.assertEqual(execution_exit(results), code)
            self.assertEqual(execution_exit(results, interrupted=True), 130)

    def test_comparison_labels_contract_changes_and_incompleteness(self):
        fixed = self.bundle('job-timeout-corrected')
        failed = self.bundle('job-timeout-ignore-unblock')
        # Synthetic comparison inputs isolate result transitions without claiming
        # that flipping a runtime mode establishes changed-build reproduction.
        same = replace(fixed, plan=failed.plan)
        self.assertEqual(compare(failed, same)['label'], 'fixed')
        self.assertEqual(compare(failed, failed)['label'], 'still-failing')
        self.assertEqual(compare(same, failed)['label'], 'newly-failing')
        self.assertEqual(compare(failed, fixed)['label'], 'incomparable')
        data = copy.deepcopy(same.result.data); data.update(verdict='ERROR', completion='incomplete')
        self.assertEqual(compare(failed, replace(same, result=replace(same.result, data=data)))['label'], 'incomplete')

    def test_candidate_has_immutable_identity_and_narrow_paths_versions_architecture(self):
        plan = load(ROOT / 'job-timeout-corrected-plan.json')
        manifest = candidate_manifest(plan['builds'], plan['profile']['adapter'], '/data/resmgrcheck/selected')
        for key, value in [('architecture', 'aarch64'), ('directory', '/tmp/unsafe'), ('schema_version', 2)]:
            data = copy.deepcopy(manifest.data); data[key] = value
            with self.assertRaises(Invalid): CandidateManifest.parse(data)
        data = copy.deepcopy(manifest.data); data['executables']['fixture'] += ';id'
        with self.assertRaises(Invalid): CandidateManifest.parse(data)
        data = copy.deepcopy(manifest.data); data['builds']['binaries']['fixture'] = '0' * 64
        with self.assertRaises(Invalid): CandidateManifest.parse(data)

    def test_changed_expectation_cannot_relabel_saved_native_evidence(self):
        from resmgrcheck.evaluator import evaluate
        tag = 'job-timeout-corrected'
        plan = load(ROOT / (tag + '-plan.json'))
        plan['profile']['expectations']['health']['value'] += 1
        plan['profile_sha256'] = digest(plan['profile'])
        self.assertEqual(evaluate(Plan.parse(plan), (ROOT / (tag + '-events.jsonl')).read_bytes()).data['verdict'], 'ERROR')


class ActualReplayGate(unittest.TestCase):
    """Recorded real QNX replay gate; no synthetic service executions."""
    root = ROOT.parent / 'phase6'

    def test_actual_same_and_changed_builds_keep_identical_contract(self):
        index = load(self.root / 'index.json')
        self.assertEqual(len(index['replays']), 4)
        self.assertEqual(index['candidate_source']['source_revision'], 'c26365e91f8f0810a531726937c6b2c4bd923837')
        for service in ('sensor', 'job'):
            original = inspect_bundle(self.root / (service + '-original'))
            path = self.root / 'attempts' / original.manifest.data['bundle_id']
            for number, verdict, label in [(2, 'FAIL', 'still-failing'), (3, 'PASS', 'fixed')]:
                bundle = inspect_bundle(path / ('attempt' + str(number)) / 'bundle')
                self.assertEqual(bundle.result.data['verdict'], verdict)
                self.assertEqual(compare(original, bundle)['label'], label)
                self.assertEqual(original.plan.data['profile'], bundle.plan.data['profile'])
                self.assertEqual(bundle.plan.data['fixture_mode'], 'ignore-unblock')
                self.assertEqual(original.plan.data['builds']['binaries']['fixture'] != bundle.plan.data['builds']['binaries']['fixture'], number == 3)

    def test_actual_wrong_hash_never_requested_launch(self):
        for service in ('sensor', 'job'):
            original = inspect_bundle(self.root / (service + '-original'))
            path = self.root / 'attempts' / original.manifest.data['bundle_id'] / 'attempt4'
            attempt = load(path / 'attempt.json')
            self.assertFalse(attempt['launch_requested']); self.assertFalse(attempt['acknowledged'])
            self.assertEqual(attempt['execution_exit'], 2)
            checks = load(path / 'hash-checks.json')
            self.assertNotEqual(checks[-1]['observed'], checks[-1]['expected'])
            self.assertFalse((path / 'bundle').exists())

    def test_actual_mixed_junit_preserves_required_coverage_error(self):
        root = ET.fromstring((self.root / 'mixed.xml').read_bytes())
        self.assertEqual({k: int(root.get(k)) for k in ('tests', 'failures', 'errors', 'skipped')},
                         {'tests': 32, 'failures': 6, 'errors': 4, 'skipped': 18})
        self.assertEqual(len(root.findall("testsuite/testcase[@name='required-coverage']/error")), 3)


if __name__ == '__main__': unittest.main()
