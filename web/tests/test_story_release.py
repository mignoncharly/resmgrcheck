"""Compatible application round trip; temporary pointer, modeled root/services."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
from unittest.mock import patch
from . import test_security_release as baseline
import deploy_evidence_story as story


class StoryReleaseTests(baseline.SecurityReleaseTests):
    def setUp(self):
        super().setUp()
        scoped = patch.object(baseline, 'deploy', story)
        scoped.start(); self.addCleanup(scoped.stop)

    def test_round_trip_requires_old_and_new_browser_acceptance_and_preserves_files(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary); old = root/'old'; new = root/'new'
            old.mkdir(); new.mkdir(); (old/'keep').write_bytes(b'old'); (new/'keep').write_bytes(b'new')
            calls = []
            for owner, name in [(story.auth,'web'),(story.ops,'command'),(story.auth.release,'switch_current'),
                                (story.auth,'private_ready'),(story.ops,'units_and_runtime'),
                                (story.ops,'replace_owned'),(story,'health')]:
                stack.enter_context(patch.object(owner,name))
            restore = stack.enter_context(patch.object(story,'restore'))
            helper = stack.enter_context(patch.object(story,'helper',side_effect=lambda *a:calls.append(a)))
            journal = {'executor_before':'active'}
            story.rollback_drill(old,new,journal,root/'state.json','a'*40)
            restore.assert_called_once()
            self.assertIn(('--acceptance-rollback',story.ACTIVE,'a'*40),calls)
            self.assertIn(('--acceptance-final',story.CANDIDATE,'a'*40),calls)
            self.assertLess(calls.index(('--acceptance-rollback',story.ACTIVE,'a'*40)),calls.index(('--acceptance-final',story.CANDIDATE,'a'*40)))
            self.assertTrue(journal['rollback_verified'])
            self.assertEqual((old/'keep').read_bytes(),b'old')
            self.assertEqual((new/'keep').read_bytes(),b'new')

    def test_failed_rollback_browser_never_sets_success_or_switches_forward(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root=Path(temporary); journal={'executor_before':'active'}
            for owner,name in [(story.auth,'web'),(story.ops,'command'),(story,'restore')]:
                stack.enter_context(patch.object(owner,name))
            switch=stack.enter_context(patch.object(story.auth.release,'switch_current'))
            def helper(flag,*args):
                if flag=='--acceptance-rollback':raise story.CheckFailed('rollback_browser_failed')
            stack.enter_context(patch.object(story,'helper',side_effect=helper))
            with self.assertRaisesRegex(story.CheckFailed,'rollback_browser_failed'):
                story.rollback_drill(root/'old',root/'new',journal,root/'state.json','a'*40)
            self.assertNotIn('rollback_verified',journal)
            switch.assert_not_called()
