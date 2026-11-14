"""Host evaluation regression over recorded QNX bytes; edited cases are synthetic."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('qfuse_check', ROOT / 'integrations/qfuse/check.py')
check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)


class QFuseIntegration(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / 'tests/data/qfuse-events.jsonl').read_bytes()
        self.rows = [json.loads(line) for line in self.raw.splitlines()]

    def edited(self): return b'\n'.join(json.dumps(r).encode() for r in self.rows)

    def test_real_held_callback_and_cumulative_counter_are_allowed(self):
        value = check.evaluate(self.raw, 0)
        self.assertEqual(value['verdict'], 'PASS')
        self.assertFalse(value['abi1_adapter'])
        self.assertTrue(value['cleanup_verified'])

    def test_native_exit_and_missing_cleanup_are_errors(self):
        self.assertEqual(check.evaluate(self.raw, 124)['verdict'], 'ERROR')
        self.rows.pop()
        self.assertEqual(check.evaluate(self.edited(), 0)['verdict'], 'ERROR')

    def test_incomplete_identity_or_wrong_error_identity_cannot_pass(self):
        self.rows[2]['expected_error'] = 0
        self.assertEqual(check.evaluate(self.edited(), 0)['verdict'], 'ERROR')

    def test_return_code_alone_does_not_establish_healthy_external_service(self):
        self.rows[4]['raw_return'] = -1
        value = check.evaluate(self.edited(), 0)
        self.assertEqual(value['verdict'], 'FAIL')
        self.assertEqual(value['assertions']['cancel_return'], 'PASS')
        self.assertEqual(value['assertions']['independent_path_health'], 'FAIL')

    def test_active_callback_remaining_after_release_is_failure(self):
        self.rows[5]['active_operations'] = 1
        value = check.evaluate(self.edited(), 0)
        self.assertEqual(value['verdict'], 'FAIL')
        self.assertEqual(value['assertions']['callback_drained_after_release'], 'FAIL')

    def test_reordered_observations_are_error(self):
        self.rows[1], self.rows[2] = self.rows[2], self.rows[1]
        self.assertEqual(check.evaluate(self.edited(), 0)['verdict'], 'ERROR')
