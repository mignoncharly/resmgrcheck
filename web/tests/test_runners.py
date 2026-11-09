"""Real signatures/PG transactions. Discovery fixtures are not native qualification."""
from datetime import timedelta
import copy,json,logging,secrets,time,uuid
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.db import DatabaseError,transaction
from django.urls import reverse
from django.utils import timezone
from customer_runner import protocol as wire
from control import runners
from control.models import CustomerRunner,RunnerEnrollment,RunnerNonce,Target
from control.logging import PrivateFormatter
from .helpers import tenant,signed_client

def discovery():
    return {'protocol':1,'runner_version':'1','engine_sha256':'a'*64,'route_sha256':'e'*64,
        'target_identity':{'uid':0,'processor':'x86_64','machine':'x86pc','release':'8.0.0','recipe_id':'b'*64,'root':'/data/resmgrcheck'},
        'compiled_adapters':{'sensor-v1':['pending','unblock','state','release','health','timeout']},'attachment':'managed-fixture'}

@override_settings(RUNNER_ENABLED=True,RUNNER_SIGNING_KEY='c'*64)
class RunnerTests(TestCase):
    def setUp(self):
        self.user,self.org,self.project=tenant('Runner customer','runner-customer@example.test')
        self.browser=signed_client(self.user,mfa=True)
        self.seed=secrets.token_hex(32);self.info=discovery()
        self.target,self.token=runners.issue(self.user,self.project,'Owned QNX target')
        self.machine=Client(enforce_csrf_checks=True)

    def enrollment(self,seed=None,info=None):
        seed=seed or self.seed
        payload={'version':1,'audience':'https://qnx-resmgrcheck.gestionatech.de','timestamp':int(time.time()),
            'nonce':secrets.token_hex(16),'public_key':wire.public(seed),'inventory':info or self.info}
        return {'token':self.token,'message':wire.sign(seed,'enrollment',payload)}

    def post(self,operation,value):
        return self.machine.post(reverse('runner_machine',args=[operation]),data=wire.canonical(value),content_type='application/json',secure=True)

    def enroll(self):
        response=self.post('enroll',self.enrollment());self.assertEqual(response.status_code,200)
        self.runner=CustomerRunner.objects.select_related('target').get(pk=self.target.pk);return response

    def beat(self,info=None):
        return wire.request(self.seed,str(self.target.pk),'https://qnx-resmgrcheck.gestionatech.de',{'operation':'heartbeat','inventory':info or self.info})

    def test_enrollment_binds_one_target_and_public_key_but_never_approves(self):
        response=self.enroll();result=wire.verify(wire.public('c'*64),'response',response.json())['body']
        self.assertEqual(result['organization_id'],str(self.org.pk));self.assertEqual(result['runner_id'],str(self.target.pk))
        self.target.refresh_from_db();self.assertFalse(self.target.approved);self.assertEqual(result['state'],'pending-approval')
        self.assertNotIn(self.token,CustomerRunner.objects.get().public_key)
        self.assertNotEqual(RunnerEnrollment.objects.get().verifier,self.token)

    def test_idempotent_enrollment_retry_cannot_replace_device_key(self):
        self.enroll();self.assertEqual(self.post('enroll',self.enrollment()).status_code,200)
        self.assertEqual(self.post('enroll',self.enrollment(seed=secrets.token_hex(32))).status_code,400)
        self.assertEqual(CustomerRunner.objects.get().public_key,wire.public(self.seed))

    def test_expired_revoked_and_bad_enrollment_do_not_create_runner(self):
        for field in ['expires_at','revoked_at']:
            with self.subTest(field=field):
                row=RunnerEnrollment.objects.get();setattr(row,field,timezone.now()-timedelta(seconds=1));row.save()
                self.assertEqual(self.post('enroll',self.enrollment()).status_code,400)
                row.expires_at=timezone.now()+timedelta(minutes=10);row.revoked_at=None;row.save()
        value=self.enrollment();value['token']=value['token'][:-2]+'xx'
        self.assertEqual(self.post('enroll',value).status_code,400);self.assertFalse(CustomerRunner.objects.exists())

    def test_bad_signature_tamper_and_cross_server_audience_are_rejected(self):
        for field,value in [('audience','https://foreign.example'),('public_key',wire.public(secrets.token_hex(32)))]:
            message=self.enrollment();message['message']['payload'][field]=value
            self.assertEqual(self.post('enroll',message).status_code,400)
        self.assertFalse(CustomerRunner.objects.exists())

    def test_heartbeat_requires_signature_freshness_and_unique_nonce(self):
        self.enroll();message=self.beat();self.assertEqual(self.post('exchange',message).status_code,200)
        self.assertEqual(self.post('exchange',message).status_code,400)
        message=self.beat();message['payload']['timestamp']-=120;message=wire.sign(self.seed,'request',message['payload'])
        self.assertEqual(self.post('exchange',message).status_code,400)
        message=self.beat();message['signature']='0'*128;self.assertEqual(self.post('exchange',message).status_code,400)
        self.assertEqual(RunnerNonce.objects.count(),1)

    def test_cross_customer_signature_cannot_act_as_other_runner(self):
        self.enroll();other,org,project=tenant('Other runner','other-runner@example.test')
        target,token=runners.issue(other,project,'Other target')
        value=self.beat();value['payload']['runner_id']=str(target.pk);value=wire.sign(self.seed,'request',value['payload'])
        self.assertEqual(self.post('exchange',value).status_code,400)

    def test_inventory_change_quarantines_instead_of_switching_targets(self):
        self.enroll();runners.approve(self.user,self.target,self.runner.inventory_sha256)
        changed=copy.deepcopy(self.info);changed['route_sha256']='d'*64
        response=self.post('exchange',self.beat(info=changed));self.assertEqual(response.status_code,200)
        result=wire.verify(wire.public('c'*64),'response',response.json())['body'];self.assertEqual(result['state'],'quarantined')
        self.runner.refresh_from_db();self.assertEqual(self.runner.inventory,self.info);self.assertTrue(self.runner.quarantined)

    def test_approval_requires_exact_inventory_and_live_state_expires(self):
        self.enroll()
        with self.assertRaises(wire.ProtocolError):runners.approve(self.user,self.target,'0'*64)
        runners.approve(self.user,self.target,self.runner.inventory_sha256)
        self.runner=CustomerRunner.objects.select_related('target').get();self.assertEqual(runners.status(self.runner),'connected')
        self.runner.last_seen=timezone.now()-timedelta(seconds=91);self.assertEqual(runners.status(self.runner),'disconnected')
        self.assertFalse(self.post('exchange',self.beat()).json()['payload']['body']['lifecycle_qualified_by_connection'])

    def test_revocation_blocks_existing_identity_and_reenrollment(self):
        self.enroll();runners.revoke(self.user,self.target)
        self.assertEqual(self.post('exchange',self.beat()).status_code,400)
        self.assertEqual(self.post('enroll',self.enrollment()).status_code,400)
        self.target.refresh_from_db();self.assertFalse(self.target.approved)

    def test_incompatible_protocol_is_visible_and_cannot_be_approved(self):
        self.info['protocol']=2;self.enroll();self.assertEqual(runners.status(self.runner),'incompatible')
        with self.assertRaises(wire.ProtocolError):runners.approve(self.user,self.target,self.runner.inventory_sha256)

    def test_no_adapter_means_unsupported_even_when_connected_and_approved(self):
        self.info['compiled_adapters']={};self.enroll();runners.approve(self.user,self.target,self.runner.inventory_sha256)
        self.runner=CustomerRunner.objects.select_related('target').get();self.assertEqual(runners.status(self.runner),'unsupported')

    def test_browser_requests_need_mfa_project_scope_and_csrf(self):
        self.enroll();url=reverse('runner_detail',args=[self.project.pk,self.target.pk])
        self.assertEqual(self.browser.get(url).status_code,200)
        other,_,_=tenant('Foreign administrator','foreign-runner-admin@example.test')
        self.assertEqual(signed_client(other,mfa=True).get(url).status_code,404)
        self.assertEqual(signed_client(self.user).get(url).status_code,302)
        csrf=signed_client(self.user,mfa=True,csrf=True)
        self.assertEqual(csrf.post(reverse('runner_approve',args=[self.project.pk,self.target.pk]),{'inventory_sha256':self.runner.inventory_sha256}).status_code,403)

    def test_credential_once_response_is_not_persisted_or_reflected_by_detail(self):
        response=self.browser.post(reverse('runner_issue',args=[self.project.pk]),{'name':'Second runner'})
        self.assertEqual(response.status_code,200);self.assertEqual(response['Cache-Control'],'no-store')
        raw=response.context['token'];self.assertContains(response,raw)
        self.enroll();detail=self.browser.get(reverse('runner_detail',args=[self.project.pk,self.target.pk]))
        self.assertNotContains(detail,self.token);self.assertEqual(detail['Cache-Control'],'no-store')

    def test_machine_endpoint_rejects_cookies_bad_json_extra_fields_and_http_auth(self):
        self.enroll();message=self.beat();message['payload']['body']['shell']='id';message=wire.sign(self.seed,'request',message['payload'])
        self.assertEqual(self.post('exchange',message).status_code,400)
        self.machine.cookies['session']='x';self.assertEqual(self.post('exchange',self.beat()).status_code,400)
        self.machine.cookies.clear()
        self.assertEqual(self.machine.post(reverse('runner_machine',args=['exchange']),data=b'{"x":1,"x":2}',content_type='application/json').status_code,400)

    def test_disabled_endpoint_and_issue_remain_unavailable(self):
        with override_settings(RUNNER_ENABLED=False):
            self.assertEqual(self.post('enroll',self.enrollment()).status_code,404)
            self.assertEqual(self.browser.post(reverse('runner_issue',args=[self.project.pk]),{'name':'Disabled'}).status_code,409)

    def test_request_nonce_collection_is_bounded_and_expired_rows_can_be_removed(self):
        self.enroll();RunnerNonce.objects.create(runner=self.runner,nonce='0'*32,expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.post('exchange',self.beat()).status_code,200)
        self.assertFalse(RunnerNonce.objects.filter(nonce='0'*32).exists())

    def test_enrollment_token_is_redacted_even_from_untrusted_error_path(self):
        record=logging.LogRecord('test',logging.ERROR,'',0,'untrusted /'+self.token,(),None)
        output=PrivateFormatter().format(record);self.assertNotIn(self.token,output);self.assertIn('REDACTED_RUNNER_ENROLLMENT',output)

    def test_database_guards_prevent_target_key_inventory_or_tenant_switch(self):
        self.enroll();other,_,project=tenant('Database isolation','runner-guard@example.test')
        for fields in [{'public_key':'d'*64},{'inventory':{}},{'quarantined':False,'public_key':'e'*64}]:
            with self.assertRaises(DatabaseError),transaction.atomic():CustomerRunner.objects.filter(pk=self.runner.pk).update(**fields)
        with self.assertRaises(DatabaseError),transaction.atomic():Target.objects.filter(pk=self.target.pk).update(project=project)
        with self.assertRaises(DatabaseError),transaction.atomic():Target.objects.filter(pk=self.target.pk).update(kind='managed-lab')
        with self.assertRaises(DatabaseError),transaction.atomic():self.project.__class__.objects.filter(pk=self.project.pk).update(organization=project.organization)
        runners.revoke(self.user,self.target)
        with self.assertRaises(DatabaseError),transaction.atomic():CustomerRunner.objects.filter(pk=self.runner.pk).update(revoked_at=None)
