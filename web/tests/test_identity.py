import hashlib,re,secrets,time
from datetime import timedelta
from django.test import TestCase,Client,override_settings
from django.core import mail
from django.db import DatabaseError,transaction
from django.urls import reverse
from django.utils import timezone
from allauth.account.models import EmailAddress,EmailConfirmationHMAC
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP,generate_totp_secret,hotp_value,format_hotp_value
from allauth.mfa.adapter import get_adapter
from control.models import User,Organization,Membership,Project,ProjectMembership,Invitation,AuditEvent,AccountDeletion
from control.security import consume_rate
from .helpers import PASSWORD,user,signed_client,tenant

class IdentityTests(TestCase):
    def setUp(self):
        self.owner,self.organization,self.project=tenant('Tenant A','owner-a@example.test')
        self.other,self.other_org,self.other_project=tenant('Tenant B','owner-b@example.test')
        self.client=signed_client(self.owner,mfa=True)
    def test_anonymous_and_unverified_cannot_access_projects(self):
        self.assertEqual(Client().get('/app/').status_code,302)
        pending=user('pending@example.test',verified=False)
        self.assertEqual(signed_client(pending).get('/app/').status_code,403)
    def test_owner_must_have_mfa_and_current_session_assurance(self):
        self.assertIn('/2fa/reauthenticate/',signed_client(self.owner).get('/app/').url)
        Authenticator.objects.filter(user=self.owner).delete()
        self.assertIn('/2fa/totp/activate/',self.client.get('/app/').url)
    def test_expired_mfa_assurance_rejected(self):
        session=self.client.session;session['account_authentication_methods'][0]['at']=time.time()-50000;session.save()
        self.assertIn('reauthenticate',self.client.get('/app/').url)
    def test_project_view_and_api_cross_tenant_denied(self):
        for url in [reverse('project',args=[self.other_project.pk]),reverse('project_api',args=[self.other_project.pk])]:
            response=self.client.get(url);self.assertEqual(response.status_code,404);self.assertNotContains(response,'Tenant B',status_code=404)
        self.assertEqual(self.client.get(reverse('project_api',args=[self.project.pk])).json()['name'],self.project.name)
    def test_viewer_requires_explicit_project_and_cannot_mutate(self):
        viewer=user('viewer@example.test');Membership.objects.create(user=viewer,organization=self.organization,role='viewer')
        client=signed_client(viewer)
        self.assertEqual(client.get(reverse('project',args=[self.project.pk])).status_code,404)
        ProjectMembership.objects.create(project=self.project,user=viewer,role='viewer')
        self.assertEqual(client.get(reverse('project',args=[self.project.pk])).status_code,200)
        self.assertEqual(client.get(reverse('team',args=[self.organization.pk])).status_code,404)
        self.assertEqual(client.post(reverse('project_create',args=[self.organization.pk]),{'name':'Unauthorized'}).status_code,404)
    def test_team_and_audit_cross_tenant_denied(self):
        for name in ['team','audit_log']:
            self.assertEqual(self.client.get(reverse(name,args=[self.other_org.pk])).status_code,404)
    def test_csrf_rejects_mutations(self):
        client=signed_client(self.owner,mfa=True,csrf=True)
        self.assertEqual(client.post(reverse('project_create',args=[self.organization.pk]),{'name':'No token'}).status_code,403)
        self.assertFalse(Project.objects.filter(name='No token').exists())
    def test_org_and_project_creation_are_real_and_audited(self):
        self.assertEqual(self.client.post(reverse('organization_create'),{'name':'Third organization'}).status_code,302)
        self.assertTrue(Membership.objects.filter(user=self.owner,organization__name='Third organization',role='owner').exists())
        self.assertEqual(self.client.post(reverse('project_create',args=[self.organization.pk]),{'name':'Actual new project','description':'Owned work'}).status_code,302)
        self.assertTrue(AuditEvent.objects.filter(actor=self.owner,action='project.created',organization=self.organization).exists())
    def test_last_owner_cannot_be_removed(self):
        response=self.client.post(reverse('member_update',args=[self.organization.pk,self.owner.pk]),{'role':'viewer','active':'on'})
        self.assertEqual(response.status_code,409)
        self.assertEqual(Membership.objects.get(user=self.owner,organization=self.organization).role,'owner')
    def test_administrator_cannot_promote_owner_or_admin(self):
        admin=user('admin@example.test',mfa=True);Membership.objects.create(user=admin,organization=self.organization,role='admin')
        target=user('member@example.test');Membership.objects.create(user=target,organization=self.organization,role='viewer')
        response=signed_client(admin,mfa=True).post(reverse('member_update',args=[self.organization.pk,target.pk]),{'role':'owner','active':'on'})
        self.assertEqual(response.status_code,404)
    def test_project_assignment_rejects_cross_tenant_user(self):
        response=self.client.post(reverse('project_member',args=[self.project.pk]),{'user_id':str(self.other.pk),'role':'developer'})
        self.assertEqual(response.status_code,404)
    def test_project_role_cannot_exceed_organization_role(self):
        viewer=user('limited@example.test');Membership.objects.create(user=viewer,organization=self.organization,role='viewer')
        response=self.client.post(reverse('project_member',args=[self.project.pk]),{'user_id':str(viewer.pk),'role':'developer'})
        self.assertEqual(response.status_code,400)
    def test_revocation_affects_only_authorized_org_and_is_immediate(self):
        outsider=user('two-orgs@example.test');Membership.objects.create(user=outsider,organization=self.organization,role='viewer')
        Membership.objects.create(user=outsider,organization=self.other_org,role='viewer')
        ProjectMembership.objects.create(project=self.project,user=outsider,role='viewer');ProjectMembership.objects.create(project=self.other_project,user=outsider,role='viewer')
        client=signed_client(outsider)
        self.client.post(reverse('member_update',args=[self.organization.pk,outsider.pk]),{'role':'viewer'})
        self.assertEqual(client.get(reverse('project',args=[self.project.pk])).status_code,404)
        self.assertEqual(client.get(reverse('project',args=[self.other_project.pk])).status_code,200)
    def test_audit_cannot_be_updated_or_deleted_in_postgres(self):
        event=AuditEvent.objects.create(actor=self.owner,organization=self.organization,action='test.fact')
        for action in ['update','delete']:
            with self.assertRaises(DatabaseError),transaction.atomic():
                row=AuditEvent.objects.filter(pk=event.pk)
                row.update(action='tampered') if action=='update' else row.delete()
    def test_encrypted_totp_and_required_owner_authenticator(self):
        adapter=get_adapter();plaintext=generate_totp_secret();ciphertext=adapter.encrypt(plaintext)
        self.assertNotIn(plaintext,ciphertext);self.assertEqual(adapter.decrypt(ciphertext),plaintext)
        self.assertFalse(adapter.can_delete_authenticator(Authenticator.objects.get(user=self.owner,type='totp')))
    def test_invitation_requires_matching_verified_email_and_is_single_use(self):
        target=user('invitee@example.test');token=secrets.token_urlsafe(32)
        invitation=Invitation.objects.create(organization=self.organization,email=target.email,role='viewer',token_hash=hashlib.sha256(token.encode()).hexdigest(),invited_by=self.owner,expires_at=timezone.now()+timedelta(hours=2))
        url=reverse('accept_invitation',args=[token])
        self.assertEqual(self.client.post(url).status_code,404)
        client=signed_client(target);self.assertEqual(client.get(url).status_code,200)
        self.assertFalse(Membership.objects.filter(user=target).exists())
        self.assertEqual(client.post(url).status_code,302)
        self.assertEqual(client.post(url).status_code,404)
    def test_expired_invitation_rejected(self):
        token=secrets.token_urlsafe(32)
        Invitation.objects.create(organization=self.organization,email=self.owner.email,role='viewer',token_hash=hashlib.sha256(token.encode()).hexdigest(),invited_by=self.other,expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.post(reverse('accept_invitation',args=[token])).status_code,404)
    def test_account_export_excludes_other_users_and_security_material(self):
        response=self.client.get(reverse('account_export'))
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,self.other.email)
        for value in ['password','totp','secret','session_key']:self.assertNotContains(response,value)
    def test_password_confirmed_session_revocation(self):
        second=signed_client(self.owner,mfa=True)
        self.assertEqual(self.client.post(reverse('logout_all'),{'password':'wrong'}).status_code,400)
        self.assertEqual(self.client.post(reverse('logout_all'),{'password':PASSWORD}).status_code,302)
        self.assertEqual(second.get('/app/').status_code,302)
    def test_account_deletion_protects_sole_owner(self):
        response=self.client.post(reverse('account_delete'),{'password':PASSWORD})
        self.assertEqual(response.status_code,409);self.owner.refresh_from_db();self.assertTrue(self.owner.is_active)
    def test_account_deletion_disables_access_and_schedules_retention(self):
        target=user('leaving@example.test');client=signed_client(target)
        response=client.post(reverse('account_delete'),{'password':PASSWORD})
        self.assertEqual(response.status_code,200);target.refresh_from_db();self.assertFalse(target.is_active)
        self.assertTrue(AccountDeletion.objects.filter(user=target,completed_at=None).exists())
    def test_shared_rate_limits_have_distinct_identities(self):
        self.assertTrue(consume_rate('test','a',1,60));self.assertFalse(consume_rate('test','a',1,60));self.assertTrue(consume_rate('test','b',1,60))
    def test_security_headers(self):
        response=self.client.get('/app/')
        self.assertIn("object-src 'none'",response['Content-Security-Policy'])
        self.assertEqual(response['Cache-Control'],'no-store')
        self.assertEqual(response['X-Frame-Options'],'DENY')

class AccountProtocolTests(TestCase):
    def test_signup_email_verification_requires_post_and_real_password(self):
        response=self.client.post(reverse('account_signup'),{'email':'new@example.test','password1':PASSWORD,'password2':PASSWORD})
        self.assertEqual(response.status_code,302)
        target=User.objects.get(email='new@example.test');address=EmailAddress.objects.get(user=target)
        self.assertFalse(address.verified);self.assertEqual(len(mail.outbox),1)
        key=EmailConfirmationHMAC(address).key;url=reverse('account_confirm_email',args=[key])
        self.client.get(url);address.refresh_from_db();self.assertFalse(address.verified)
        self.assertEqual(self.client.post(url).status_code,302);address.refresh_from_db();self.assertTrue(address.verified)
    def test_login_with_totp_requires_actual_second_factor(self):
        target=user('mfa@example.test');secret=generate_totp_secret();TOTP.activate(target,secret)
        response=self.client.post(reverse('account_login'),{'login':target.email,'password':PASSWORD})
        self.assertEqual(response.status_code,302);self.assertIn('2fa/authenticate',response.url)
        self.assertNotIn('_auth_user_id',self.client.session)
        response=self.client.post(reverse('mfa_authenticate'),{'code':'not-a-code'})
        self.assertEqual(response.status_code,200);self.assertNotIn('_auth_user_id',self.client.session)
        code=format_hotp_value(hotp_value(secret,int(time.time())//30))
        response=self.client.post(reverse('mfa_authenticate'),{'code':code})
        self.assertEqual(response.status_code,302);self.assertEqual(self.client.session['_auth_user_id'],str(target.pk))
        self.assertEqual(self.client.get('/app/').status_code,200)
    def test_password_reset_protocol_changes_registered_password(self):
        target=user('reset@example.test')
        response=self.client.post(reverse('account_reset_password'),{'email':target.email})
        self.assertEqual(response.status_code,302);self.assertEqual(len(mail.outbox),1)
        url=re.search(r'https?://[^\s]+/accounts/password/reset/key/[^\s]+',mail.outbox[0].body).group(0)
        response=self.client.get(url,follow=True)
        new_password='Entirely different reset phrase 51892!'
        response=self.client.post(response.request['PATH_INFO'],{'password1':new_password,'password2':new_password})
        self.assertEqual(response.status_code,302);target.refresh_from_db();self.assertTrue(target.check_password(new_password))
    def test_get_logout_does_not_mutate_session(self):
        target=user('logout@example.test');client=signed_client(target)
        client.get(reverse('account_logout'));self.assertIn('_auth_user_id',client.session)
    def test_login_does_not_allow_external_next_redirect(self):
        target=user('redirect@example.test')
        response=self.client.post(reverse('account_login')+'?next=https://invalid.example/',{'login':target.email,'password':PASSWORD})
        self.assertEqual(response.status_code,302);self.assertNotIn('invalid.example',response.url)
    def test_real_totp_enrollment_and_step_up_before_first_organization(self):
        target=user('enroll@example.test')
        self.client.post(reverse('account_login'),{'login':target.email,'password':PASSWORD})
        # allauth requires explicit recent password reauthentication before enrollment.
        response=self.client.post(reverse('account_reauthenticate'),{'password':PASSWORD})
        self.assertEqual(response.status_code,302)
        response=self.client.get(reverse('mfa_activate_totp'))
        self.assertEqual(response.status_code,200)
        secret=self.client.session['mfa.totp.secret']
        code=format_hotp_value(hotp_value(secret,int(time.time())//30))
        response=self.client.post(reverse('mfa_activate_totp'),{'code':code})
        self.assertEqual(response.status_code,302)
        auth=Authenticator.objects.get(user=target,type='totp')
        self.assertNotEqual(auth.data['secret'],secret)
        self.assertTrue(Authenticator.objects.filter(user=target,type='recovery_codes').exists())
        self.assertIn('reauthenticate',self.client.get(reverse('organization_create')).url)
        response=self.client.post(reverse('mfa_reauthenticate'),{'code':code})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.post(reverse('organization_create'),{'name':'First real organization'}).status_code,302)
    def test_invalid_email_confirmation_rejected(self):
        response=self.client.post(reverse('account_confirm_email',args=['invalid-key']))
        self.assertEqual(response.status_code,404)
        self.assertFalse(EmailAddress.objects.filter(verified=True).exists())
