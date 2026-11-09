"""Actual disposable DB principal lifecycle; no protected production config access."""
import contextlib,io,json,sys,tempfile,uuid
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from .helpers import tenant
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import acceptance_operator as acceptance
from https_checks import CheckFailed

class ProductionAcceptanceIdentityTests(TestCase):
    def test_failed_browser_still_publishes_safe_cleanup_receipt(self):
        from control.models import User
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary);(source/'.local/browser-test/bin').mkdir(parents=True);(source/'.local/browser-test/bin/python').touch()
            (source/'.local/web/evidence').mkdir(parents=True);state=source/'protected';state.mkdir(mode=0o700)
            with patch.object(acceptance,'load_application'),patch.object(acceptance.deployment,'SOURCE',source),patch.object(acceptance,'native_plan',return_value={'status':'blocked','reason':'fixture'}),patch.object(acceptance.deployment,'command',side_effect=[b'inactive',CheckFailed('fixture_browser_failure')]),self.assertRaisesRegex(CheckFailed,'fixture_browser_failure'):
                acceptance.run('5'*40,'6'*40,state)
            receipt=json.loads(next((source/'.local/web/evidence').glob('production-*/operator-cleanup.json')).read_text())
            self.assertTrue(receipt['temporary_account_disabled']);self.assertFalse(receipt['existing_users_changed'])
            self.assertEqual(User.objects.filter(username__startswith='accept-',is_active=True).count(),0)
            self.assertEqual(json.loads(next(state.glob('*.cleanup.json')).read_text()),receipt)
            self.assertEqual(set(receipt),{'temporary_account_disabled','temporary_codes_revoked','existing_users_changed','audit_runs_evidence_preserved','own_native_work_still_active'})
    def test_bootstrap_and_cleanup_preserve_existing_users_and_revoke_only_own_test_data(self):
        from control.models import User,AccessCode,AccessSession,Organization,Membership
        from control.access import create_code
        existing,org,project=tenant('Preserved real identity','preserved-identity@example.test')
        original=User.objects.values().get(pk=existing.pk)
        identifier=uuid.uuid4();credentials=acceptance.bootstrap(identifier,{'status':'blocked','reason':'no production native in fixture'})
        account=User.objects.get(pk=credentials['account_id']);self.assertTrue(account.check_password(credentials['password']))
        self.assertFalse(account.is_superuser);self.assertFalse(Membership.objects.filter(user=existing).exclude(organization=org).exists())
        from django.test import Client
        from django.utils import timezone
        from datetime import timedelta
        scoped=Organization.objects.get(pk=credentials['organization_id'])
        from control.models import Project
        selected=Project.objects.get(pk=credentials['project_id'])
        code,raw=create_code(account,scoped,'Temporary acceptance code',[{'project':selected,'targets':[]}])
        client=Client();self.assertEqual(client.post('/access/',{'code':raw}).status_code,302)
        result=acceptance.close(credentials)
        self.assertTrue(result['temporary_account_disabled']);self.assertFalse(User.objects.get(pk=account.pk).is_active)
        self.assertTrue(AccessCode.objects.get(pk=code.pk).revoked_at);self.assertTrue(AccessSession.objects.get().revoked_at)
        self.assertEqual(client.get('/app/').status_code,302);self.assertEqual(User.objects.values().get(pk=existing.pk),original)
        self.assertNotIn(credentials['password'],json.dumps(result));self.assertNotIn(credentials['totp_secret'],json.dumps(result))
    def test_cleanup_cannot_adopt_existing_administrator_by_name_or_id(self):
        existing,_,_=tenant('Unrelated administrator','no-cleanup@example.test')
        with self.assertRaises(CheckFailed):acceptance.close({'account_id':str(existing.pk),'username':existing.username,'acceptance_id':str(uuid.uuid4())})
        existing.refresh_from_db();self.assertTrue(existing.is_active)
    def test_bootstrap_cross_tenant_scope_is_not_granted(self):
        from control.models import User,Project
        from control.security import visible_projects
        credentials=acceptance.bootstrap(uuid.uuid4(),{'status':'blocked','reason':'fixture'})
        account=User.objects.get(pk=credentials['account_id'])
        self.assertTrue(visible_projects(account).filter(pk=credentials['project_id']).exists())
        self.assertFalse(visible_projects(account).filter(pk=credentials['foreign_project_id']).exists())
