import json,tempfile,time,uuid
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,RequestFactory,override_settings
from django.db import DatabaseError,transaction
from django.urls import reverse
from django.utils import timezone
from control.models import Target,BuildRelease,Run,ExecutorSlot,Membership,Artifact
from control.jobs import enqueue,QueueError
from control.worker import claim,reauthorize,execute_claim
from control.engine import fixed_argv,Binding,PolicyError,command,EngineUncertain
from .helpers import tenant,signed_client

class SchedulingTests(TestCase):
    def setUp(self):
        self.user,self.org,self.project=tenant('Queue owner','queue@example.test',mfa=False)
        self.client=signed_client(self.user)
        self.target=Target.objects.create(project=self.project,name='Private fixture lab',kind='managed-lab',approved=True,state='available',inventory={'compiled_adapters':{'sensor-v1':['pending','unblock','state','release','health','timeout'],'job-v1':['pending','unblock','state','release','health','timeout','error-probe']}})
        self.build=BuildRelease.objects.create(target=self.target,label='Known original',approved=True,
            manifest=json.loads((Path(__file__).resolve().parents[2]/'tests/data/deployment-v1.json').read_text()))
    def request(self):
        request=RequestFactory().post('/');request.user=self.user;request.session=self.client.session;return request
    def queued(self,key='idempotent-request-1234',**extra):
        return enqueue(self.request(),self.project,self.target,self.build,profile='sensor',suite='profile',mode='fixed',key=key,**extra)[0]
    def test_deduplication_is_intent_bound(self):
        first=self.queued();second=self.queued();self.assertEqual(first.pk,second.pk);self.assertEqual(Run.objects.count(),1)
        with self.assertRaises(QueueError):enqueue(self.request(),self.project,self.target,self.build,profile='job',suite='profile',mode='fixed',key=first.idempotency_key)
    def test_project_target_cannot_cross_tenant(self):
        _,_,other=tenant('Different owner','different@example.test')
        with self.assertRaises(QueueError):enqueue(self.request(),self.project,Target.objects.create(project=other,name='Other',approved=True),self.build,profile='sensor',suite='profile',mode='fixed',key='another-valid-request')
    def test_worker_reauthorizes_revoked_membership(self):
        run=self.queued();Membership.objects.filter(user=self.user,organization=self.org).update(active=False)
        with self.assertRaises(PolicyError):reauthorize(run)
    def test_worker_rejects_password_or_session_revocation(self):
        run=self.queued();self.user.session_version+=1;self.user.save();run.refresh_from_db()
        with self.assertRaises(PolicyError):reauthorize(run)
    def test_global_slot_prevents_concurrent_dispatch(self):
        self.queued();self.queued(key='second-valid-request')
        first=claim();self.assertIsNotNone(first);self.assertIsNone(claim())
    def test_expired_lease_recovers_same_identity(self):
        run=self.queued();first=claim();ExecutorSlot.objects.filter(name='private-qnx').update(expires_at=timezone.now()-timedelta(seconds=1))
        recovered=claim();self.assertEqual(first[0],recovered[0]);self.assertTrue(recovered[2]);self.assertEqual(Run.objects.get(pk=run.pk).native_run_id,run.native_run_id)
    def test_postgres_rejects_run_intent_mutation(self):
        run=self.queued()
        with self.assertRaises(DatabaseError),transaction.atomic():Run.objects.filter(pk=run.pk).update(fixture_mode='ignore-unblock')
    def test_postgres_rejects_target_tenant_substitution(self):
        run=self.queued();_,_,other=tenant('Third owner','third@example.test');other_target=Target.objects.create(project=other,name='Other')
        with self.assertRaises(DatabaseError),transaction.atomic():Run.objects.filter(pk=run.pk).update(target=other_target)
    def test_capacity_limits_do_not_drop_requested_coverage(self):
        for i in range(5):self.queued(key='capacity-key-valid-'+str(i))
        with self.assertRaisesRegex(QueueError,'project_queue_full'):self.queued(key='capacity-overflow-key')
    def test_recovery_can_collect_under_service_authority_after_actor_revocation(self):
        run=self.queued();Membership.objects.filter(user=self.user).update(active=False)
        reauthorize(run,recovery=True)
    def test_new_run_requires_preview_confirmation_and_is_idempotent(self):
        data={'target':str(self.target.pk),'build':str(self.build.pk),'profile':'sensor','suite':'profile','fixture_mode':'fixed','idempotency_key':'preview-confirmed-key'}
        url=reverse('new_run',args=[self.project.pk]);response=self.client.post(url,data)
        self.assertEqual(response.status_code,200);self.assertEqual(Run.objects.count(),0)
        token=response.context['form'].data['confirmation']
        data.update(confirmed='on',confirmation=token)
        self.assertEqual(self.client.post(url,data).status_code,302);self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(Run.objects.count(),1)
    def test_confirmation_cannot_be_reused_after_parameter_tamper(self):
        data={'target':str(self.target.pk),'build':str(self.build.pk),'profile':'sensor','suite':'profile','fixture_mode':'fixed','idempotency_key':'tamper-confirmation-key'}
        url=reverse('new_run',args=[self.project.pk]);response=self.client.post(url,data)
        data.update(confirmed='on',confirmation=response.context['form'].data['confirmation'],profile='job')
        self.assertEqual(self.client.post(url,data).status_code,400);self.assertEqual(Run.objects.count(),0)
    def test_status_and_cancel_do_not_cross_tenants(self):
        run=self.queued();other,_,_=tenant('Other','other-status@example.test');client=signed_client(other,mfa=True)
        self.assertEqual(client.get(reverse('run_status',args=[run.pk])).status_code,404)
        self.assertEqual(client.post(reverse('cancel',args=[run.pk])).status_code,404)
        self.assertFalse(Run.objects.get(pk=run.pk).cancel_requested)
    def test_unknown_capabilities_and_arbitrary_profile_are_rejected(self):
        self.target.inventory={};self.target.save()
        data={'target':str(self.target.pk),'build':str(self.build.pk),'profile':'sensor','suite':'profile','fixture_mode':'fixed','idempotency_key':'unknown-capabilities-key'}
        response=self.client.post(reverse('new_run',args=[self.project.pk]),data)
        self.assertContains(response,'UNKNOWN',status_code=400)
        data['profile']='sensor; whoami';self.assertEqual(self.client.post(reverse('new_run',args=[self.project.pk]),data).status_code,400)
    def test_customer_request_does_not_accept_arbitrary_host_or_approval(self):
        response=self.client.post(reverse('target_request',args=[self.project.pk]),{'name':'My customer target','approved':'on','binding':'evil','hostname':'127.0.0.1;id','kind':'managed-lab'})
        self.assertEqual(response.status_code,302)
        target=Target.objects.get(name='My customer target');self.assertFalse(target.approved);self.assertEqual(target.kind,'customer-request');self.assertEqual(target.binding,'')
    def test_external_lifecycle_is_unsupported_before_any_dispatch(self):
        self.target.kind='external-health';self.target.save()
        with self.assertRaisesRegex(QueueError,'required_capability_unsupported'):self.queued()
    def test_control_selection_cannot_claim_an_unexercised_obligation(self):
        data={'target':str(self.target.pk),'build':str(self.build.pk),'profile':'sensor','suite':'profile','fixture_mode':'drop-job','idempotency_key':'unsupported-control-key'}
        response=self.client.post(reverse('new_run',args=[self.project.pk]),data)
        self.assertContains(response,'UNSUPPORTED',status_code=400)
        data['fixture_mode']='retain-third'
        self.assertContains(self.client.post(reverse('new_run',args=[self.project.pk]),data),'third reconnect',status_code=400)
        self.assertEqual(Run.objects.count(),0)

class HostProcessBoundTests(TestCase):
    def binding(self):return Binding(Path('/tmp'),Path('/tmp/not-used'),'lab',{},'org','project')
    def test_bounded_real_owned_host_child_exit(self):
        code,raw,facts=command(['/usr/bin/python3','-c','print("host-only probe")'],self.binding(),lambda:None,timeout=3)
        self.assertEqual(code,0);self.assertIn(b'host-only',raw);self.assertTrue(facts['local_child_exit_observed'])
    def test_stuck_owned_host_child_is_reaped_without_remote_cleanup_claim(self):
        with self.assertRaises(EngineUncertain):command(['/usr/bin/python3','-c','import time;time.sleep(30)'],self.binding(),lambda:None,timeout=.1)
    def test_output_bound(self):
        with self.assertRaises(EngineUncertain):command(['/usr/bin/python3','-c','print("x"*300000)'],self.binding(),lambda:None,timeout=3)
    def test_start_callback_failure_also_reaps_owned_child(self):
        import os
        observed=[]
        def fail(pid):observed.append(pid);raise RuntimeError('host-only callback failure')
        with self.assertRaises(RuntimeError):command(['/usr/bin/python3','-c','import time;time.sleep(30)'],self.binding(),lambda:None,timeout=3,on_started=fail)
        with self.assertRaises(ProcessLookupError):os.kill(observed[0],0)
