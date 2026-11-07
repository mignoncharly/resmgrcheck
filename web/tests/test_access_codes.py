"""Real PostgreSQL-backed code/session policy, isolation and concurrency checks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta,date
import hashlib,json,secrets,sys,time
from pathlib import Path
from unittest.mock import patch
from django.db import transaction,DatabaseError,connections,close_old_connections
from django.test import TestCase,TransactionTestCase,Client,RequestFactory
from django.urls import reverse
from django.utils import timezone
from control.models import AccessCode,AccessGrant,AccessSession,User,Run,Target,AuditEvent,AIProviderState,AIAnalysis,AIUsage
from control.access import create_code,revoke_code,verifier
from control.security import job_principal,principal_fields,start_authority
from control.jobs import enqueue
from control.worker import reauthorize,claim,execute_claim
from control.engine import PolicyError,command,Binding
from control.ai_evidence import evidence_pack
from control.ai_jobs import enqueue_analysis
from control.ai_provider import Provider
from control.ai_worker import claim as claim_ai,execute as execute_ai
from . import test_dashboard as dashboard_tests
from .helpers import tenant,signed_client

class AccessTests(TestCase):
    setUp=dashboard_tests.DashboardTests.setUp
    recorded=dashboard_tests.DashboardTests.recorded
    def issue(self,*,live=False,ai=False,download=True,all_evidence=True,evidence=(),targets=None,**limits):
        self.target.kind='managed-lab';self.target.save(update_fields=['kind'])
        return create_code(self.owner,self.org,'Scoped engineering access',[{'project':self.project,'targets':targets if targets is not None else [self.target],
            'evidence':list(evidence),'all_evidence':all_evidence,'can_run':live,'can_ai':ai,'can_download':download}],allow_live=live,allow_ai=ai,**limits)
    def code_client(self,raw,csrf=False):
        client=Client(enforce_csrf_checks=csrf);response=client.post(reverse('developer_access'),{'code':raw})
        self.assertEqual(response.status_code,302);return client
    def principal_request(self,client):
        identifier=client.session['rmc_access_session'];session=AccessSession.objects.select_related('code__organization').get(pk=identifier)
        request=RequestFactory().post('/');request.user=job_principal(type('Job',(),{'access_session_id':session.pk,'access_session':session})());request.session=client.session
        return request
    def test_secure_generation_stores_only_keyed_verifier_and_no_user_account(self):
        users=User.objects.count();code,raw=self.issue();self.assertEqual(len(code.verifier),64);self.assertNotEqual(code.verifier,raw)
        self.assertEqual(code.verifier,verifier(raw));self.assertGreaterEqual(len(raw),80)
        client=self.code_client(raw);self.assertEqual(User.objects.count(),users)
        self.assertNotIn(raw,json.dumps(dict(client.session)));self.assertNotIn(raw,json.dumps(list(AuditEvent.objects.values('action','details')),default=str))
    def test_administrator_dashboard_shows_raw_code_only_on_creation(self):
        self.target.kind='managed-lab';self.target.save()
        response=self.client.post(reverse('access_codes',args=[self.org.pk]),{'description':'Read current report','projects':[str(self.project.pk)],'targets':[str(self.target.pk)],'max_sessions':1,'all_evidence':'on'})
        self.assertEqual(response.status_code,200);raw=response.context['created_code'];self.assertTrue(raw)
        code=response.context['created'];self.assertEqual(code.verifier,verifier(raw))
        self.assertNotContains(self.client.get(reverse('code_detail',args=[code.pk])),raw)
        self.assertNotContains(self.client.get(reverse('access_codes',args=[self.org.pk])),raw)
        self.assertEqual(response['Cache-Control'],'no-store')
    def test_valid_redemption_persists_browser_session_without_retransmitting_code(self):
        code,raw=self.issue();client=self.code_client(raw);identifier=client.session['rmc_access_session']
        for _ in range(3):self.assertEqual(client.get(reverse('project_api',args=[self.project.pk])).status_code,200)
        self.assertEqual(client.session['rmc_access_session'],identifier);code.refresh_from_db();self.assertEqual(code.redemptions,1);self.assertIsNotNone(code.last_access)
    def test_invalid_malformed_and_unknown_codes_denied_without_echo(self):
        _,raw=self.issue()
        for value in ['not-an-issued-code-r4x',raw[:-1]+('a' if raw[-1]!='a' else 'b'),'rmc_'+secrets.token_hex(16)+'_'+secrets.token_urlsafe(32)]:
            response=Client().post('/access/',{'code':value});self.assertEqual(response.status_code,400);self.assertNotContains(response,value,status_code=400)
        self.assertFalse(AccessSession.objects.exists())
    def test_expired_code_and_revoked_code_denied(self):
        code,raw=self.issue();AccessCode.objects.filter(pk=code.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(Client().post('/access/',{'code':raw}).status_code,400)
        AccessCode.objects.filter(pk=code.pk).update(expires_at=None);revoke_code(self.owner,code.pk)
        self.assertEqual(Client().post('/access/',{'code':raw}).status_code,400)
    def test_maximum_redemptions_and_active_sessions_enforced(self):
        code,raw=self.issue(max_redemptions=1,max_sessions=1);first=self.code_client(raw)
        self.assertEqual(Client().post('/access/',{'code':raw}).status_code,400)
        first.post(reverse('account_logout'));self.assertEqual(Client().post('/access/',{'code':raw}).status_code,400)
        code.refresh_from_db();self.assertEqual(code.redemptions,1)
    def test_logout_releases_capacity_when_lifetime_redemptions_remain(self):
        _,raw=self.issue(max_sessions=1);first=self.code_client(raw);first.post(reverse('account_logout'))
        second=self.code_client(raw);self.assertEqual(second.get('/app/').status_code,200)
    def test_code_revocation_immediately_denies_all_active_sessions(self):
        code,raw=self.issue(max_sessions=2);first=self.code_client(raw);second=self.code_client(raw)
        self.client.post(reverse('code_revoke',args=[code.pk]))
        for client in [first,second]:self.assertEqual(client.get(reverse('project_api',args=[self.project.pk])).status_code,302)
        self.assertEqual(AccessSession.objects.filter(code=code,revoked_at=None).count(),0)
    def test_single_session_revocation_does_not_revoke_other_session(self):
        _,raw=self.issue(max_sessions=2);first=self.code_client(raw);second=self.code_client(raw)
        self.client.post(reverse('access_session_revoke',args=[first.session['rmc_access_session']]))
        self.assertEqual(first.get('/app/').status_code,302);self.assertEqual(second.get('/app/').status_code,200)
    def test_idle_absolute_and_code_expiry_invalidate_existing_session(self):
        for field in ['idle','absolute','code']:
            code,raw=self.issue();client=self.code_client(raw);sid=client.session['rmc_access_session']
            if field=='idle':AccessSession.objects.filter(pk=sid).update(last_access=timezone.now()-timedelta(minutes=31))
            elif field=='absolute':AccessSession.objects.filter(pk=sid).update(expires_at=timezone.now()-timedelta(seconds=1))
            else:AccessCode.objects.filter(pk=code.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
            self.assertEqual(client.get('/app/').status_code,302)
    def test_session_binding_rejects_an_access_session_id_in_another_browser(self):
        _,raw=self.issue();first=self.code_client(raw);second=Client();session=second.session;session['rmc_access_session']=first.session['rmc_access_session'];session.save()
        self.assertEqual(second.get('/app/').status_code,302)
    def test_codes_are_not_bearer_or_query_api_credentials(self):
        _,raw=self.issue();client=Client()
        self.assertEqual(client.get(reverse('project_api',args=[self.project.pk]),HTTP_AUTHORIZATION='Bearer '+raw).status_code,302)
        self.assertEqual(client.get('/app/?code='+raw).status_code,302)
    def test_code_redemption_requires_csrf_and_invalid_attempts_are_bounded(self):
        _,raw=self.issue();self.assertEqual(Client(enforce_csrf_checks=True).post('/access/',{'code':raw}).status_code,403)
        client=Client()
        for _ in range(10):client.post('/access/',{'code':'wrong'})
        self.assertEqual(client.post('/access/',{'code':'wrong'}).status_code,429)
    def test_project_and_target_scope_are_enforced_in_lists_and_direct_urls(self):
        _,_,other=tenant('Different project','other-code@example.test');foreign=Target.objects.create(project=other,name='Foreign target',approved=True)
        second=Target.objects.create(project=self.project,name='Unselected target',approved=True)
        _,raw=self.issue();client=self.code_client(raw)
        self.assertEqual(client.get(reverse('project_api',args=[other.pk])).status_code,404)
        self.assertNotContains(client.get('/app/targets/'),'Foreign target');self.assertNotContains(client.get('/app/targets/'),'Unselected target')
        self.assertEqual(client.post(reverse('inventory',args=[self.project.pk,second.pk])).status_code,404)
    def test_selected_evidence_only_and_download_permission(self):
        selected=self.recorded('broken');unselected=self.recorded('after')
        _,raw=self.issue(all_evidence=False,evidence=[selected]);client=self.code_client(raw)
        self.assertEqual(client.get(reverse('run_detail',args=[selected.pk])).status_code,200)
        self.assertEqual(client.get(reverse('run_detail',args=[unselected.pk])).status_code,404)
        _,other=self.issue(download=False);restricted=self.code_client(other)
        self.assertEqual(restricted.get(reverse('evidence_download',args=[selected.pk])).status_code,404)
        self.assertEqual(restricted.get(reverse('report_file',args=[selected.pk,'report.html'])).status_code,404)
    def test_cross_project_evidence_and_comparison_denied(self):
        selected=self.recorded('broken');_,_,other=tenant('Secret project','secret-project@example.test')
        Run.objects.filter(pk=selected.pk) # Intent cannot be moved; use a separate project's recorded fixture.
        from control.models import BuildRelease
        foreign_target=Target.objects.create(project=other,name='Foreign service')
        foreign=Run.objects.create(project=other,target=foreign_target,actor=other.created_by,actor_auth_hash='0'*64,mfa_at=timezone.now(),native_run_id='foreign-access-test',operation='run',idempotency_key='foreign-key-unique',intent_sha256='1'*64)
        _,raw=self.issue();client=self.code_client(raw)
        self.assertEqual(client.get(reverse('run_detail',args=[foreign.pk])).status_code,404)
        self.assertEqual(client.get(reverse('evidence_download',args=[foreign.pk])).status_code,404)
        self.assertEqual(client.get(reverse('compare'),{'before':str(selected.pk),'after':str(foreign.pk)}).status_code,404)
    def test_code_cannot_administer_codes_members_targets_or_retention(self):
        code,raw=self.issue(live=True,ai=True);client=self.code_client(raw)
        for path in [reverse('access_codes',args=[self.org.pk]),reverse('code_detail',args=[code.pk]),reverse('administrator_settings'),reverse('team',args=[self.org.pk]),reverse('retention',args=[self.org.pk]),reverse('ai_settings',args=[self.project.pk])]:self.assertEqual(client.get(path).status_code,404,path)
        self.assertEqual(client.post(reverse('target_request',args=[self.project.pk]),{'name':'Escalation'}).status_code,404)
    def test_readonly_code_cannot_run_or_request_ai(self):
        run=self.recorded('after');_,raw=self.issue();client=self.code_client(raw)
        self.assertEqual(client.post(reverse('new_run',args=[self.project.pk]),{}).status_code,404)
        self.assertEqual(client.get(reverse('ai_request',args=[run.pk])).status_code,404)
        self.assertEqual(client.get('/demo/').status_code,200)
    def test_permission_edit_revokes_sessions_without_exposing_original_code(self):
        code,raw=self.issue(live=True);client=self.code_client(raw)
        response=self.client.post(reverse('code_detail',args=[code.pk]),{'description':'Reduced policy','projects':[str(self.project.pk)],'targets':[str(self.target.pk)],'max_sessions':1,'all_evidence':'on'})
        self.assertEqual(response.status_code,302);self.assertEqual(client.get('/app/').status_code,302)
        code.refresh_from_db();self.assertFalse(code.allow_live);self.assertEqual(code.verifier,verifier(raw))
        fresh=self.code_client(raw);self.assertEqual(fresh.post(reverse('new_run',args=[self.project.pk]),{}).status_code,404)
    def test_pending_qnx_work_is_rejected_after_code_revocation_without_any_child(self):
        archived=self.recorded('after');code,raw=self.issue(live=True);client=self.code_client(raw);request=self.principal_request(client)
        run,_=enqueue(request,self.project,self.target,archived.build,profile='sensor',suite='profile',mode='fixed',key='code-pending-work-key')
        self.assertIsNone(run.actor_id);self.assertEqual(run.access_session_id,request.user.pk)
        revoke_code(self.owner,code.pk);run.refresh_from_db()
        with self.assertRaises(PolicyError):reauthorize(run)
        with patch('control.worker.registry') as binding,patch('control.worker.command') as launch:
            execute_claim(*claim());binding.assert_not_called();launch.assert_not_called()
        run.refresh_from_db();self.assertEqual(run.state,'rejected');self.assertIsNone(run.started_at)
    def test_child_start_guard_denies_revocation_even_after_prior_authorization(self):
        archived=self.recorded('after');code,raw=self.issue(live=True);request=self.principal_request(self.code_client(raw))
        run,_=enqueue(request,self.project,self.target,archived.build,profile='sensor',suite='profile',mode='fixed',key='guarded-native-key')
        reauthorize(run);revoke_code(self.owner,code.pk)
        binding=Binding(Path('/tmp'),Path('/tmp/unused'),'lab',{},'org','project')
        with patch('subprocess.Popen') as child,self.assertRaises(PolicyError):command([sys.executable,'-c','pass'],binding,lambda:None,start_guard=start_authority(run))
        child.assert_not_called()
    def test_service_owned_recovery_can_collect_exact_run_after_code_revocation(self):
        archived=self.recorded('after');code,raw=self.issue(live=True);request=self.principal_request(self.code_client(raw))
        run,_=enqueue(request,self.project,self.target,archived.build,profile='sensor',suite='profile',mode='fixed',key='code-recovery-key')
        revoke_code(self.owner,code.pk);reauthorize(run,recovery=True)
    def test_ai_under_code_session_preserves_consent_budgets_and_revocation(self):
        run=self.recorded('broken');code,raw=self.issue(ai=True);request=self.principal_request(self.code_client(raw))
        provider=Provider('openai','host-only-test-model','not-a-real-provider-key',1000000,4000000,500000,100000,date.today().isoformat())
        AIProviderState.objects.create(name='default',available=True,policy=provider.public(),refreshed_at=timezone.now())
        self.project.ai_enabled=True;self.project.ai_daily_budget_microusd=200000;self.project.save()
        payload,citations=evidence_pack(request.user,run,'timeout','explain')
        first,_=enqueue_analysis(request,run,'explain',payload,citations,'code-ai-reservation-key');second,created=enqueue_analysis(request,run,'explain',payload,citations,'code-ai-reservation-key')
        self.assertEqual(first.pk,second.pk);self.assertFalse(created);self.assertIsNone(first.actor_id);self.assertEqual(AIUsage.objects.get(scope='global').requests,1)
        revoke_code(self.owner,code.pk)
        with patch('control.ai_worker.configuration',return_value=provider),patch('control.ai_worker.bounded_invoke') as invoke:execute_ai(*claim_ai());invoke.assert_not_called()
        first.refresh_from_db();self.assertEqual(first.state,'error');self.assertEqual(first.accounted_microusd,first.reserved_microusd)
    def test_code_ai_view_requires_exact_signed_consent_before_reserving(self):
        run=self.recorded('broken');code,raw=self.issue(ai=True);client=self.code_client(raw)
        provider=Provider('openai','host-only-test-model','not-a-real-provider-key',1000000,4000000,500000,100000,date.today().isoformat())
        AIProviderState.objects.create(name='default',available=True,policy=provider.public(),refreshed_at=timezone.now())
        self.project.ai_enabled=True;self.project.ai_daily_budget_microusd=200000;self.project.save()
        url=reverse('ai_request',args=[run.pk]);data={'task':'explain','case':'timeout','key':'signed-code-consent-key'}
        preview=client.post(url,data);self.assertEqual(preview.status_code,200);self.assertFalse(AIAnalysis.objects.exists())
        data['confirmation']=preview.context['form'].data['confirmation']
        self.assertEqual(client.post(url,data).status_code,400);self.assertFalse(AIUsage.objects.exists())
        data['consent']='on';response=client.post(url,data);self.assertEqual(response.status_code,302)
        self.assertEqual(client.post(url,data).url,response.url);self.assertEqual(AIAnalysis.objects.count(),1)
        request=self.principal_request(client);job=AIAnalysis.objects.get()
        self.assertEqual(job.access_session_id,request.user.pk);self.assertEqual(AIUsage.objects.get(scope='global').requests,1)
    def test_database_guards_reject_code_tenant_and_job_identity_substitution(self):
        archived=self.recorded('after');code,raw=self.issue(live=True);request=self.principal_request(self.code_client(raw))
        run,_=enqueue(request,self.project,self.target,archived.build,profile='sensor',suite='profile',mode='fixed',key='identity-db-code-key')
        with self.assertRaises(DatabaseError),transaction.atomic():Run.objects.filter(pk=run.pk).update(access_session=None)
        _,_,other=tenant('Other grant','other-grant@example.test')
        with self.assertRaises(DatabaseError),transaction.atomic():AccessGrant.objects.create(code=code,project=other)

class ConcurrentRedemptionTests(TransactionTestCase):
    def test_concurrent_redemptions_respect_active_session_limit(self):
        owner,org,project=tenant('Concurrency','concurrent-admin@example.test');target=Target.objects.create(project=project,name='Owned scope')
        code,raw=create_code(owner,org,'One active session',[{'project':project,'targets':[target]}],max_sessions=1)
        def redeem_one(number):
            close_old_connections()
            try:return Client().post('/access/',{'code':raw},REMOTE_ADDR='192.0.2.'+str(number+1)).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(redeem_one,range(4)))
        self.assertEqual(statuses.count(302),1);self.assertEqual(statuses.count(400),3);code.refresh_from_db();self.assertEqual(code.redemptions,1)
        self.assertEqual(AccessSession.objects.filter(code=code,revoked_at=None).count(),1)
    def test_concurrent_redemptions_respect_lifetime_limit(self):
        owner,org,project=tenant('Lifetime','lifetime-admin@example.test');target=Target.objects.create(project=project,name='Owned scope')
        code,raw=create_code(owner,org,'One lifetime redemption',[{'project':project,'targets':[target]}],max_sessions=4,max_redemptions=1)
        def redeem_one(number):
            close_old_connections()
            try:return Client().post('/access/',{'code':raw},REMOTE_ADDR='198.51.100.'+str(number+1)).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(redeem_one,range(4)))
        self.assertEqual(statuses.count(302),1);code.refresh_from_db();self.assertEqual(code.redemptions,1)
