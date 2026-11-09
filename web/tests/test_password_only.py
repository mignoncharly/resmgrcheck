"""Current release policy: real password authentication, retained dormant MFA."""
import tempfile,time
from pathlib import Path
from django.test import TestCase,Client,override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from allauth.mfa.models import Authenticator
from control.models import AuditEvent
from .helpers import user,tenant,signed_client,PASSWORD

class PasswordOnlyTests(TestCase):
    def test_password_login_with_and_without_stored_authenticators_and_privileged_access(self):
        for has_mfa in [False,True]:
            account,org,project=tenant('Password owner '+str(has_mfa),'password-'+str(has_mfa)+'@example.test',mfa=has_mfa)
            original=list(Authenticator.objects.filter(user=account).values())
            client=Client();response=client.post('/administrator/login/',{'login':account.username,'password':PASSWORD})
            self.assertEqual(response.status_code,302);self.assertEqual(response.url,'/app/')
            self.assertEqual(client.get('/app/').status_code,200)
            self.assertEqual(client.get('/administrator/organizations/'+str(org.pk)+'/codes/').status_code,200)
            security=client.get('/administrator/settings/');self.assertContains(security,'MFA is deferred');self.assertNotContains(security,'/administrator/2fa/')
            self.assertEqual(client.get('/administrator/2fa/').status_code,404)
            self.assertEqual(list(Authenticator.objects.filter(user=account).values()),original)
            self.assertEqual([r['method'] for r in client.session['account_authentication_methods']],['password'])
            self.assertTrue(AuditEvent.objects.filter(actor=account,action='account.login').exists())
    def test_idle_and_absolute_expiration_flush_administrator_session(self):
        account=user('expires-admin@example.test')
        for key,age in [('rmc_admin_last_seen',1801),('rmc_admin_started_at',43201)]:
            client=signed_client(account);session=client.session;session[key]=time.time()-age;session.save()
            self.assertEqual(client.get('/app/').status_code,302);self.assertNotIn('_auth_user_id',client.session)
        self.assertEqual(AuditEvent.objects.filter(actor=account,action='administrator.session_expired').count(),2)
    def test_activity_does_not_extend_absolute_lifetime_and_missing_legacy_clock_expires(self):
        account=user('clock-admin@example.test');client=signed_client(account)
        original=client.session['rmc_admin_started_at'];self.assertEqual(client.get('/app/').status_code,200)
        self.assertEqual(client.session['rmc_admin_started_at'],original)
        session=client.session;del session['rmc_admin_started_at'];session.save()
        self.assertEqual(client.get('/app/').status_code,302)
    def test_stale_privileged_authentication_uses_password_reauthentication(self):
        account,org,_=tenant('Password reauth','reauth-admin@example.test',mfa=False);client=signed_client(account)
        session=client.session;session['account_authentication_methods'][0]['at']=time.time()-1000;session.save()
        path='/administrator/organizations/'+str(org.pk)+'/codes/'
        response=client.get(path);self.assertIn('/administrator/reauthenticate/',response.url);self.assertNotIn('/2fa/',response.url)
        response=client.post('/administrator/reauthenticate/',{'password':PASSWORD});self.assertEqual(response.status_code,302)
        self.assertEqual(client.get(path).status_code,200)
    def test_local_password_recovery_preserves_authenticators_and_refuses_reset_while_deferred(self):
        account=user('recover-password-only@example.test',mfa=True);before=list(Authenticator.objects.filter(user=account).values())
        client=signed_client(account)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'password';path.write_text('A new secure password recovery phrase 617!');path.chmod(0o600)
            call_command('recover_administrator',username=account.username,password_file=str(path),verbosity=0)
            with self.assertRaises(CommandError):call_command('recover_administrator',username=account.username,password_file=str(path),reset_mfa=True,verbosity=0)
        self.assertEqual(list(Authenticator.objects.filter(user=account).values()),before)
        self.assertEqual(client.get('/app/').status_code,302)
    def test_disabled_nonadministrator_and_anonymous_cannot_use_privileged_routes(self):
        account=user('disabled-password-only@example.test');account.is_active=False;account.save()
        client=Client();client.post('/administrator/login/',{'login':account.username,'password':PASSWORD})
        self.assertNotIn('_auth_user_id',client.session)
        self.assertEqual(client.get('/administrator/settings/').status_code,302)
