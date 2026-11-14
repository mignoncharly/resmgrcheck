"""Explanations retain actual saved failure, withheld-health and cleanup distinctions."""
from pathlib import Path
import copy
import unittest
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.story import assertion_story

ROOT = Path(__file__).resolve().parents[2]


class StoryTests(unittest.TestCase):
    def recorded(self, label):
        return inspect_bundle(ROOT / 'docs/evidence/phase10/executions' /
                              ('p10demo2-' + label) / 'cases/timeout/bundle').result.data

    def test_real_failure_does_not_borrow_success_from_cleanup(self):
        result = self.recorded('broken'); original = copy.deepcopy(result)
        steps = {row['label']: row for row in assertion_story(result)}
        self.assertEqual(steps['Client operation']['verdict'], 'FAIL')
        self.assertEqual(steps['Pending state']['verdict'], 'FAIL')
        self.assertEqual(steps['Next client']['verdict'], 'NOT_RUN')
        self.assertEqual(steps['Test cleanup']['verdict'], 'PASS')
        self.assertIn('withheld', steps['Next client']['description'])
        self.assertEqual(result, original)

    def test_corrected_and_job_stories_link_only_saved_assertion_references(self):
        for label in ('after', 'job'):
            result = self.recorded(label)
            steps = assertion_story(result)
            self.assertTrue(all(row['verdict'] == 'PASS' for row in steps))
            allowed = {ref for item in result['assertions'] for ref in item['event_refs']}
            self.assertTrue(all(set(row['event_refs']) <= allowed for row in steps))

    def test_missing_unsupported_error_and_withheld_never_receive_success_prose(self):
        for verdict in ('ERROR', 'UNSUPPORTED', 'NOT_RUN'):
            result = {'assertions': [{'id': 'fresh_client_health', 'verdict': verdict, 'event_refs': []}]}
            steps = {row['label']: row for row in assertion_story(result)}
            self.assertEqual(steps['Next client']['verdict'], verdict)
            self.assertNotIn('satisfied', steps['Next client']['description'])
            self.assertEqual(steps['Pending state']['verdict'], 'UNRECORDED')
