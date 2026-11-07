"""Presentation of genuine archived QNX bytes; no new native execution claim."""
import json,shutil,tempfile,hashlib
from pathlib import Path
from django.conf import settings
from django.test import TestCase,override_settings
from django.urls import reverse
from control.models import Target,BuildRelease,Run,Artifact
from control.engine import run_path
from control.storage import seal
from .helpers import tenant,signed_client

class DashboardTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.override=override_settings(MEDIA_ROOT=Path(self.temp.name));self.override.enable();self.addCleanup(self.override.disable)
        self.owner,self.org,self.project=tenant('Report owner','report-owner@example.test');self.client=signed_client(self.owner,mfa=True)
        self.target=Target.objects.create(project=self.project,name='Archived evidence test target',approved=True)
    def recorded(self,label,source=None):
        source=source or settings.REPO_ROOT/'docs/evidence/phase10/executions'/('p10demo2-'+label)
        request=json.loads((source/'request.json').read_text())
        build=BuildRelease.objects.create(target=self.target,label='Recorded '+label,manifest=request['deployment'],approved=True)
        run=Run.objects.create(project=self.project,target=self.target,build=build,actor=self.owner,actor_auth_hash='0'*64,mfa_at=self.owner.date_joined,
            native_run_id=request['run_id'],operation='run',profile='job' if label=='job' else 'sensor',suite='profile',fixture_mode=request['mode'],
            idempotency_key='archived-recorded-'+label,intent_sha256='1'*64,state='completed')
        path=run_path(run);path.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,path)
        summary,cleanup=seal(run);run.summary=summary;run.target_cleanup_verified=cleanup;run.save(update_fields=['summary','target_cleanup_verified'])
        return run
    def test_public_demo_is_recorded_and_never_enqueues(self):
        initial=Run.objects.count()
        for selection,verdict in [('before','FAIL'),('after','PASS'),('job','PASS'),('partial','ERROR')]:
            response=self.client.get(reverse('demo_case',args=[selection]))
            self.assertEqual(response.status_code,200);self.assertContains(response,'RECORDED EVIDENCE PLAYBACK');self.assertContains(response,verdict)
        self.assertEqual(Run.objects.count(),initial)
    def test_actual_failed_obligations_and_source_references_display(self):
        run=self.recorded('broken');response=self.client.get(reverse('run_detail',args=[run.pk]))
        self.assertEqual(response.status_code,200)
        for text in ['cancellation_not_completed','pending_state_not_released','NOT_RUN','#event-timeout-122','58db59fec146ed83']:
            self.assertContains(response,text)
    def test_all_twenty_recorded_cycles_and_six_cases_are_preserved(self):
        run=self.recorded('lifecycle',settings.REPO_ROOT/'docs/evidence/phase7/executions/sensor-fixed')
        response=self.client.get(reverse('run_detail',args=[run.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['cases']),6)
        repeat=next(case for case in response.context['cases'] if case['name']=='repeat')
        self.assertEqual(len(repeat['result']['cycles']),20)
        for number in range(1,21):self.assertContains(response,'Inspect cycle '+str(number)+'<')
    def test_source_corrected_comparison_retains_native_label(self):
        before=self.recorded('broken');after=self.recorded('after')
        response=self.client.get(reverse('compare'),{'before':str(before.pk),'after':str(after.pk)})
        self.assertEqual(response.status_code,200);self.assertEqual(response.context['comparison']['label'],'fixed')
        self.assertContains(response,'39b99d7');self.assertContains(response,'d9d2a1a')
    def test_tampered_required_evidence_withholds_pass(self):
        run=self.recorded('after');raw=run_path(run)/'cases/timeout/bundle/observations.jsonl'
        raw.write_bytes(raw.read_bytes()+b'\n')
        response=self.client.get(reverse('run_detail',args=[run.pk]))
        self.assertEqual(response.status_code,409);self.assertContains(response,'Required evidence failed integrity',status_code=409)
        self.assertNotContains(response,'all_obligations_satisfied',status_code=409)
    def test_original_offline_html_is_sandboxed_and_owned(self):
        run=self.recorded('broken');response=self.client.get(reverse('report_file',args=[run.pk,'report.html']))
        self.assertEqual(response.status_code,200)
        self.assertIn("default-src 'none'",response['Content-Security-Policy']);self.assertNotIn('allow-scripts',response['Content-Security-Policy'])
        self.assertIn(b'ResMgrCheck',b''.join(response.streaming_content))
        other,_,_=tenant('Other owner','no-report@example.test')
        self.assertEqual(signed_client(other,mfa=True).get(reverse('report_file',args=[run.pk,'report.html'])).status_code,404)
    def test_public_demo_file_allowlist_prevents_path_escape(self):
        self.assertEqual(self.client.get('/demo/before/evidence/not-a-member/').status_code,404)
        self.assertEqual(self.client.get('/demo/unknown/evidence/plan.json/').status_code,404)
    def test_unknown_comparison_identifier_is_field_specific(self):
        response=self.client.get(reverse('compare'),{'before':'not-a-uuid','after':'also-invalid'})
        self.assertContains(response,'before/after: expected valid',status_code=400)
    def test_empty_workspace_has_no_fabricated_activity(self):
        response=self.client.get('/app/')
        self.assertContains(response,'No execution requests yet');self.assertContains(response,'No registered targets',count=0)
        self.assertEqual(response.context['stats']['requests'],0)
