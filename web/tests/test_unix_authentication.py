"""Real CSRF/password/MFA with Gunicorn's empty Unix-socket REMOTE_ADDR."""
import re,time
from django.test import Client,TestCase,override_settings,RequestFactory
from django.core.exceptions import PermissionDenied
from allauth.account.adapter import get_adapter
from allauth.mfa.models import Authenticator
from allauth.mfa.utils import decrypt
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from .helpers import user,PASSWORD

@override_settings(ENVIRONMENT='production',SESSION_COOKIE_SECURE=True,CSRF_COOKIE_SECURE=True,
    SECURE_SSL_REDIRECT=True,SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),
    ALLAUTH_TRUSTED_CLIENT_IP_HEADER='X-Real-IP')
class UnixAuthenticationTests(TestCase):
    host='qnx-resmgrcheck.gestionatech.de'
    def setUp(self):
        self.account=user('unix-auth@example.test',mfa=True)
        self.client=Client(enforce_csrf_checks=True,REMOTE_ADDR='',HTTP_X_REAL_IP='198.51.100.20',
            HTTP_HOST=self.host,HTTP_X_FORWARDED_PROTO='https',HTTP_ORIGIN='https://'+self.host)
    def post(self,path,data):
        page=self.client.get(path);self.assertEqual(page.status_code,200)
        token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.content.decode()).group(1)
        return self.client.post(path,{**data,'csrfmiddlewaretoken':token})
    def test_old_unconfigured_adapter_reproduces_production_403_before_password_check(self):
        with override_settings(ALLAUTH_TRUSTED_CLIENT_IP_HEADER=None):
            response=self.post('/administrator/login/',{'login':self.account.username,'password':PASSWORD})
        self.assertEqual(response.status_code,403);self.assertNotIn('_auth_user_id',self.client.session)
    def test_correct_proxy_identity_keeps_password_MFA_and_CSRF_requirements(self):
        response=self.post('/administrator/login/',{'login':self.account.username,'password':'Wrong password probe'})
        self.assertEqual(response.status_code,200);self.assertNotIn('_auth_user_id',self.client.session)
        response=self.post('/administrator/login/',{'login':self.account.username,'password':PASSWORD})
        self.assertIn('/administrator/2fa/authenticate/',response.url);self.assertNotIn('_auth_user_id',self.client.session)
        self.assertEqual(self.client.get('/app/').status_code,302)
        secret=decrypt(Authenticator.objects.get(user=self.account,type='totp').data['secret'])
        code=format_hotp_value(hotp_value(secret,int(time.time())//30))
        response=self.post('/administrator/2fa/authenticate/',{'code':code})
        self.assertEqual(response.status_code,302);self.assertEqual(self.client.session['_auth_user_id'],str(self.account.pk))
    def test_missing_or_invalid_header_fails_closed_and_forwarded_chain_cannot_substitute(self):
        for value in ['', 'untrusted.invalid','198.51.100.20, 198.51.100.21']:
            request=RequestFactory().post('/',REMOTE_ADDR='',HTTP_X_REAL_IP=value,HTTP_X_FORWARDED_FOR='192.0.2.2')
            with self.assertRaises(PermissionDenied):get_adapter().get_client_ip(request)
        request=RequestFactory().post('/',REMOTE_ADDR='',HTTP_X_REAL_IP='2001:db8::20',HTTP_X_FORWARDED_FOR='192.0.2.2')
        self.assertEqual(get_adapter().get_client_ip(request),'2001:db8::20')
    def test_valid_identity_does_not_allow_foreign_origin_or_missing_CSRF_token(self):
        self.client.get('/administrator/login/')
        data={'login':self.account.username,'password':PASSWORD}
        self.assertEqual(self.client.post('/administrator/login/',data).status_code,403)
        self.client.defaults['HTTP_ORIGIN']='https://untrusted.invalid'
        self.assertEqual(self.post('/administrator/login/',data).status_code,403)
