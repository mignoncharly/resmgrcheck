"""Settings presentation and real session/CSRF boundaries; isolated test DB only."""
import re
from django.test import TestCase,Client,override_settings
from allauth.usersessions.models import UserSession
from control.models import AuditEvent
from .helpers import user,signed_client,PASSWORD

@override_settings(ADMIN_MFA_REQUIRED=False)
class SecuritySettingsTests(TestCase):
    def setUp(self):
        self.account=user('security-preview@example.test')
        self.client=signed_client(self.account)

    def test_current_session_is_matched_by_key_and_private_keys_never_render(self):
        key=self.client.session.session_key
        UserSession.objects.update_or_create(session_key=key,defaults={'user':self.account,'ip':'127.0.0.1','user_agent':'fixture'})
        UserSession.objects.create(user=self.account,session_key='other-private-session-key',ip='127.0.0.1')
        other=user('other-security@example.test')
        UserSession.objects.create(user=other,session_key='foreign-private-session-key',ip='127.0.0.1')
        response=self.client.get('/administrator/settings/')
        self.assertEqual(response.status_code,200);self.assertFalse(response.context['is_account_page'])
        self.assertEqual(len(response.context['sessions']),2)
        self.assertEqual(sum(s.current for s in response.context['sessions']),1)
        self.assertContains(response,'Current session');self.assertContains(response,'Security and recovery')
        for secret in [key,'other-private-session-key','foreign-private-session-key','127.0.0.1']:
            self.assertNotContains(response,secret)

    def test_invalid_confirmation_retains_access_and_returns_accessible_form(self):
        for data in [{},{'password':'wrong-password'}]:
            response=self.client.post('/administrator/logout-all/',data)
            self.assertEqual(response.status_code,400);self.assertContains(response,'role="alert"',status_code=400)
            self.assertContains(response,'aria-invalid="true"',status_code=400)
            self.assertNotContains(response,'value="wrong-password"',status_code=400)
            self.assertEqual(self.client.get('/administrator/settings/').status_code,200)
        self.assertFalse(AuditEvent.objects.filter(action='administrator.sessions_revoked').exists())

    def test_csrf_required_for_all_security_posts_and_current_logout_preserves_other_browser(self):
        protected=Client(enforce_csrf_checks=True);protected.cookies=self.client.cookies
        for path,data in [('/administrator/logout-all/',{'password':PASSWORD}),('/sign-out/',{}),('/administrator/password/change/',{})]:
            self.assertEqual(protected.post(path,data).status_code,403,path)
        second=signed_client(self.account)
        self.assertEqual(self.client.post('/sign-out/').status_code,302)
        self.assertEqual(self.client.get('/administrator/settings/').status_code,302)
        self.assertEqual(second.get('/administrator/settings/').status_code,200)

    def test_anonymous_settings_and_mutations_require_authentication(self):
        anonymous=Client()
        self.assertEqual(anonymous.get('/administrator/settings/').status_code,302)
        self.assertEqual(anonymous.post('/administrator/logout-all/',{'password':PASSWORD}).status_code,302)

    def test_password_change_and_global_revocation_preserve_canonical_controls(self):
        other=signed_client(self.account)
        new_password='Changed administrator phrase 841! Secure'
        response=self.client.post('/administrator/password/change/',{'oldpassword':PASSWORD,'password1':new_password,'password2':new_password})
        self.assertEqual(response.status_code,302)
        self.account.refresh_from_db();self.assertTrue(self.account.check_password(new_password))
        self.assertEqual(other.get('/administrator/settings/').status_code,302)
        first=signed_client(self.account,csrf=True);second=signed_client(self.account)
        page=first.get('/administrator/settings/')
        self.assertEqual(page.status_code,200)
        token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.content.decode()).group(1)
        response=first.post('/administrator/logout-all/',{'password':new_password,'csrfmiddlewaretoken':token})
        self.assertEqual(response.status_code,302)
        self.assertEqual(first.get('/administrator/settings/').status_code,302)
        self.assertEqual(second.get('/administrator/settings/').status_code,302)
        self.assertTrue(AuditEvent.objects.filter(action='administrator.sessions_revoked',actor=self.account).exists())
