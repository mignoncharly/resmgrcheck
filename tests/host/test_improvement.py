"""Archived QNX observations and host-only search safety; mocks are not native evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.contracts import Invalid, load
from resmgrcheck.return_check import return_check
from resmgrcheck.reduction import reduce_cycles, failure_signature
from resmgrcheck.transport import Target
from resmgrcheck.workflow import inspect_execution
from resmgrcheck.evaluator import evaluate_persistent, evaluate

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence/phase7/executions/release'


class Improvement(unittest.TestCase):
    def test_real_failure_on_last_requested_cycle_is_not_infrastructure_error(self):
        source = ROOT / 'docs/evidence/impact-innovation/trials/final-cycle-error'
        original = load(source / 'result.json')
        result = evaluate_persistent(load(source / 'plan.json'), (source / 'observations.jsonl').read_bytes(), load(source / 'status.json')).data
        self.assertEqual(original['verdict'], 'ERROR')  # Preserved pre-correction evaluation.
        self.assertEqual([c['verdict'] for c in result['cycles']], ['PASS', 'PASS', 'FAIL'])
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(next(a['verdict'] for a in result['assertions'] if a['id'] == 'repeat_coverage'), 'NOT_RUN')
        self.assertEqual(next(a['verdict'] for a in result['assertions'] if a['id'] == 'evidence_completeness'), 'PASS')

    def test_missing_last_cycle_state_still_is_uncertainty(self):
        source = ROOT / 'docs/evidence/impact-innovation/trials/final-cycle-error'
        import json
        from resmgrcheck.contracts import canonical
        rows = [json.loads(line) for line in (source / 'observations.jsonl').read_bytes().splitlines()]
        rows = [r for r in rows if not (r.get('event') == 'control_result' and r['cycle'] == 3 and r['data']['operation'] == 'state')]
        sequences = {}
        for row in rows[1:]:
            key = (row['producer'], row['pid']); sequences[key] = sequences.get(key, 0) + 1; row['seq'] = sequences[key]
        result = evaluate(load(source / 'plan.json'), b''.join(canonical(r) + b'\n' for r in rows)).data
        self.assertEqual(result['verdict'], 'ERROR')
        self.assertEqual(result['cycles'][-1]['verdict'], 'ERROR')

    def test_real_timeout_return_does_not_establish_waiter_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            for service in ('sensor', 'job'):
                source = EVIDENCE / (service + '-timeout-retain-waiter') / 'cases/timeout/bundle'
                before = {p.name: p.read_bytes() for p in source.iterdir()}
                result = return_check(source, Path(directory) / (service + '.json'))
                self.assertEqual(result['limited_predicate'], 'SATISFIED')
                self.assertEqual(result['canonical_verdict'], 'FAIL')
                self.assertIn('pending_state_not_released', result['canonical_reasons'])
                self.assertEqual(result['missed_obligations'][0]['observed']['events'][0]['data']['pending'], 1)
                self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})

    def test_return_check_preserves_existing_output_and_requires_cancel_case(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'occupied'; path.write_bytes(b'preserve')
            with self.assertRaises(Invalid):
                return_check(EVIDENCE / 'sensor-timeout-retain-waiter/cases/timeout/bundle', path)
            self.assertEqual(path.read_bytes(), b'preserve')

    def test_reduction_rejects_wrong_target_and_occupied_output_before_launch(self):
        source = EVIDENCE / 'sensor-repeat-retain-third'
        request, _, _ = inspect_execution(source)
        target = Target(request.data['target'], dict(request.data['target_identity']))
        with tempfile.TemporaryDirectory() as directory, patch('resmgrcheck.reduction.execute') as launch:
            path = Path(directory) / 'occupied'; path.mkdir()
            with self.assertRaises(FileExistsError): reduce_cycles(source, target, path)
            altered = copy.deepcopy(target.data); altered['recipe_id'] = '0' * 64
            with self.assertRaises(Invalid): reduce_cycles(source, Target(target.name, altered), Path(directory) / 'new')
            launch.assert_not_called()

    def test_uncertain_launch_stops_and_retains_recovery_identity(self):
        source = EVIDENCE / 'sensor-repeat-retain-third'
        request, _, _ = inspect_execution(source)
        target = Target(request.data['target'], dict(request.data['target_identity']))
        with tempfile.TemporaryDirectory() as directory, patch('resmgrcheck.reduction.execute', side_effect=Invalid('uncertain')) as launch:
            path = Path(directory) / 'search'
            with self.assertRaises(Invalid): reduce_cycles(source, target, path, progress=lambda _: None)
            launch.assert_called_once()
            result = load(path / 'reduction.json')
            self.assertEqual(result['state'], 'blocked_error')
            self.assertEqual(result['attempts'][0]['state'], 'launch_intent')
            self.assertTrue(result['attempts'][0]['run_id'])
            self.assertFalse(result['minimal_within_cycle_count_domain'])

    def test_original_repeat_failure_signature_ignores_withheld_cycles(self):
        bundle = inspect_bundle(EVIDENCE / 'sensor-repeat-retain-third/cases/repeat/bundle')
        self.assertEqual(failure_signature(bundle.result.data), ['pending_state_not_released'])
