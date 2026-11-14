"""Run existing immutable-release guards against the separately pinned nav driver."""
from unittest.mock import patch
from . import test_security_release as previous
import deploy_navigation as navigation

class NavigationReleaseTests(previous.SecurityReleaseTests):
    def setUp(self):
        super().setUp()
        # Reuse the same scope/alias/backup/failure-restoration cases without
        # changing the historical security-page driver or its protected journal.
        scoped=patch.object(previous,'deploy',navigation);scoped.start();self.addCleanup(scoped.stop)

    def test_release_and_journal_are_separate_from_completed_security_deployment(self):
        import deploy_security_page as security
        self.assertEqual(navigation.ACTIVE,security.CANDIDATE)
        self.assertNotEqual(navigation.STATE,security.STATE)
        self.assertIn('web/control/templatetags/navigation.py',navigation.APP_FILES)
        self.assertNotIn('web/control/security.py',navigation.APP_FILES)
        self.assertNotIn('web/control/worker.py',navigation.APP_FILES)
