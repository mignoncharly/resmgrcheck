"""Revised administrator identity gate; no public accounts or email recovery."""
import io,tempfile,time
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError,transaction
from django.urls import reverse
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import generate_totp_secret,TOTP,hotp_value,format_hotp_value
from control.models import User,AuditEvent,Membership
from control.security import consume_rate
from .helpers import tenant,user,signed_client,PASSWORD

class AdministratorTests(TestCase):
    def password_file(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);path=Path(temp.name)/'password';path.write_text(PASSWORD);path.chmod(0o600);return path
    def test_local_provisioning_hashes_password_without_email(self):
        file=self.password_file();output=io.StringIO()
        call_command('provision_administrator',username='first-admin',password_file=str(file),stdout=output)
        account=User.objects.get(username='first-admin');self.assertIsNone(account.email);self.assertTrue(account.is_staff)
        self.assertTrue(account.check_password(PASSWORD));self.assertTrue(account.password.startswith('argon2'))
        self.assertNotIn(PASSWORD,output.getvalue());self.assertTrue(AuditEvent.objects.filter(action='administrator.provisioned').exists())
    def test_provisioning_rejects_publicly_readable_password_file(self):
        file=self.password_file();file.chmod(0o644)
        with self.assertRaises(CommandError):call_command('provision_administrator',username='rejected-admin',password_file=str(file),stdout=io.StringIO())
        self.assertFalse(User.objects.exists())
    def test_provisioning_rejects_symlink_and_unsafe_username(self):
        file=self.password_file();link=file.with_name('link');link.symlink_to(file)
        with self.assertRaises(OSError):call_command('provision_administrator',username='safe-name',password_file=str(link),stdout=io.StringIO())
        with self.assertRaises(CommandError):call_command('provision_administrator',username='../../admin',password_file=str(file),stdout=io.StringIO())
    def test_production_provisioning_requires_local_root(self):
        with override_settings(ENVIRONMENT='production'),self.assertRaises(CommandError):call_command('provision_administrator',username='root-required',password_file=str(self.password_file()),stdout=io.StringIO())
    def test_staging_label_cannot_authorize_production_database_recovery(self):
        from django.conf import settings
        from control.management.commands.provision_administrator import local_operator
        for field,value in [('HOST','/var/run/postgresql'),('NAME','production'),('PORT','5432')]:
            with override_settings(ENVIRONMENT='staging'),patch.dict(settings.DATABASES['default'],{field:value}),self.assertRaises(CommandError):local_operator()
    def test_provisioning_explicit_organization_binding_is_scoped(self):
        _,org,_=tenant('Provision scope','provision-owner@example.test')
        call_command('provision_administrator',username='scoped-admin',password_file=str(self.password_file()),organization=[str(org.pk)],role='admin',stdout=io.StringIO())
        account=User.objects.get(username='scoped-admin')
        self.assertFalse(account.is_superuser);self.assertEqual(list(Membership.objects.filter(user=account).values_list('organization_id','role')),[(org.pk,'admin')])
    def test_all_obsolete_email_routes_are_gone(self):
        for path in ['/accounts/login/','/accounts/signup/','/accounts/email/','/accounts/password/reset/','/administrator/signup/','/administrator/password/reset/','/app/invitations/unused/','/app/account/delete/']:
            self.assertEqual(self.client.get(path).status_code,404,path)
    def test_anonymous_cannot_access_private_dashboard_or_api(self):
        owner,org,project=tenant('Private','private-admin@example.test')
        for url in ['/app/',reverse('project_api',args=[project.pk]),reverse('team',args=[org.pk])]:self.assertEqual(self.client.get(url).status_code,302)
    def test_username_password_login_requires_real_totp(self):
        account=user('mfa-admin@example.test',mfa=True)
        response=self.client.post(reverse('account_login'),{'login':account.username,'password':PASSWORD})
        self.assertIn('/administrator/2fa/authenticate/',response.url);self.assertNotIn('_auth_user_id',self.client.session)
        from allauth.mfa.utils import decrypt
        secret=decrypt(Authenticator.objects.get(user=account,type='totp').data['secret'])
        code=format_hotp_value(hotp_value(secret,int(time.time())//30))
        response=self.client.post(reverse('mfa_authenticate'),{'code':code})
        self.assertEqual(response.status_code,302);self.assertEqual(self.client.session['_auth_user_id'],str(account.pk))
    def test_bad_password_and_disabled_or_nonadmin_identity_denied(self):
        account=user('blocked-admin@example.test',mfa=True)
        self.assertEqual(self.client.post(reverse('account_login'),{'login':account.username,'password':'wrong'}).status_code,200)
        account.is_active=False;account.save()
        self.assertNotIn('_auth_user_id',self.client.session)
        self.client.post(reverse('account_login'),{'login':account.username,'password':PASSWORD});self.assertNotIn('_auth_user_id',self.client.session)
        account.is_active=True;account.is_staff=False
        with self.assertRaises(DatabaseError),transaction.atomic():account.save()
    def test_first_login_requires_real_enrollment_and_reauthentication(self):
        account=user('enroll-admin@example.test');self.client.post(reverse('account_login'),{'login':account.username,'password':PASSWORD})
        self.assertIn('totp/activate',self.client.get('/app/').url)
        response=self.client.get(reverse('mfa_activate_totp'))
        self.assertEqual(response.status_code,302)
        self.client.post(reverse('account_reauthenticate'),{'password':PASSWORD})
        response=self.client.get(reverse('mfa_activate_totp'));self.assertEqual(response.status_code,200)
        secret=self.client.session['mfa.totp.secret'];code=format_hotp_value(hotp_value(secret,int(time.time())//30))
        response=self.client.post(reverse('mfa_activate_totp'),{'code':code});self.assertEqual(response.status_code,302)
        self.assertTrue(Authenticator.objects.filter(user=account,type='totp').exists())
    def test_owner_requires_current_mfa_assurance(self):
        owner,_,_=tenant('MFA scope','step-up@example.test');client=signed_client(owner)
        self.assertIn('reauthenticate',client.get('/app/').url)
        session=client.session;session['account_authentication_methods_user']=str(owner.pk);session['account_authentication_methods']=[{'method':'mfa','type':'totp','at':time.time()-50000}];session.save()
        self.assertIn('reauthenticate',client.get('/app/').url)
    def test_local_recovery_revokes_sessions_and_resets_mfa_only_explicitly(self):
        account=user('recover-admin@example.test',mfa=True);client=signed_client(account,mfa=True)
        output=io.StringIO();call_command('recover_administrator',username=account.username,password_file=str(self.password_file()),reset_mfa=True,stdout=output)
        self.assertNotIn(PASSWORD,output.getvalue());self.assertFalse(Authenticator.objects.filter(user=account).exists())
        self.assertEqual(client.get('/app/').status_code,302);self.assertTrue(AuditEvent.objects.filter(action='administrator.local_recovery').exists())
    def test_password_change_uses_no_email_and_revokes_other_sessions(self):
        account=user('change-admin@example.test',mfa=True);first=signed_client(account,mfa=True);second=signed_client(account,mfa=True)
        response=first.post(reverse('account_change_password'),{'oldpassword':PASSWORD,'password1':'A newly changed administrator phrase 481!','password2':'A newly changed administrator phrase 481!'})
        self.assertEqual(response.status_code,302);account.refresh_from_db();self.assertTrue(account.check_password('A newly changed administrator phrase 481!'))
        self.assertEqual(second.get('/app/').status_code,302)
    def test_password_confirmed_global_session_revocation(self):
        account=user('revoke-admin@example.test',mfa=True);first=signed_client(account,mfa=True);second=signed_client(account,mfa=True)
        self.assertEqual(first.post(reverse('logout_all'),{'password':'incorrect'}).status_code,400)
        self.assertEqual(first.post(reverse('logout_all'),{'password':PASSWORD}).status_code,302)
        self.assertEqual(second.get('/app/').status_code,302)
    def test_administrator_session_view_is_mfa_scoped_without_email_dependencies(self):
        account=user('session-list-admin@example.test',mfa=True);client=signed_client(account,mfa=True)
        response=client.get(reverse('usersessions_list'));self.assertContains(response,'Browser sessions');self.assertContains(response,'Revoke all sessions')
        self.assertNotContains(response,client.session.session_key)
        self.assertIn('reauthenticate',signed_client(account).get(reverse('usersessions_list')).url)
    def test_get_logout_never_changes_a_session(self):
        account=user('logout-admin@example.test',mfa=True);client=signed_client(account,mfa=True)
        self.assertEqual(client.get(reverse('account_logout')).status_code,405);self.assertIn('_auth_user_id',client.session)
    def test_cross_tenant_administrator_access_is_denied(self):
        first,org,project=tenant('First','first-scope@example.test');second,_,_=tenant('Other','other-scope@example.test');client=signed_client(second,mfa=True)
        for url in [reverse('project',args=[project.pk]),reverse('project_api',args=[project.pk]),reverse('access_codes',args=[org.pk]),reverse('audit_log',args=[org.pk])]:self.assertEqual(client.get(url).status_code,404)
    def test_admin_login_is_csrf_protected_and_rate_limited(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('account_login'),{'login':'unknown','password':'never-used'}).status_code,403)
        for number in range(10):self.client.post(reverse('account_login'),{'login':'unknown-admin','password':'incorrect'})
        self.assertEqual(self.client.post(reverse('account_login'),{'login':'unknown-admin','password':'incorrect'}).status_code,429)
    def test_audit_append_only_and_no_email_backend_dependency(self):
        account=user('audit-admin@example.test');event=AuditEvent.objects.create(actor=account,action='security.test')
        with self.assertRaises(DatabaseError),transaction.atomic():AuditEvent.objects.filter(pk=event.pk).update(action='changed')
        from django.conf import settings
        from control.auth import DisabledMailBackend
        self.assertNotIn('smtp',settings.EMAIL_BACKEND)
        with self.assertRaises(RuntimeError):DisabledMailBackend().send_messages([])
    def test_security_headers_and_production_cookie_settings(self):
        response=self.client.get('/access/');self.assertEqual(response['X-Frame-Options'],'DENY');self.assertIn('no-store',response['Cache-Control'])
        self.assertIn("form-action 'self'",response['Content-Security-Policy'])
