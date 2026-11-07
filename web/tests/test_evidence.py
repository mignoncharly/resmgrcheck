"""Private evidence boundaries with genuine archived native bytes; no new QNX run."""
from datetime import timedelta
import hashlib,json,os,shutil,zipfile
from pathlib import Path
from django.conf import settings
from django.db import DatabaseError,transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from control.models import Artifact,Run,AuditEvent,AccountDeletion,Membership
from control.engine import run_path,PolicyError
from control.storage import seal,open_artifact,verify_inventory
from control.evidence import bundle_export,verify_local_links
from control.retention import purge_run,erase_account
from . import test_dashboard as dashboard_tests
from .helpers import tenant,signed_client,user

class EvidenceTests(TestCase):
    setUp=dashboard_tests.DashboardTests.setUp
    recorded=dashboard_tests.DashboardTests.recorded
    def aged(self):
        run=self.recorded('after');Run.objects.filter(pk=run.pk).update(finished_at=timezone.now()-timedelta(days=31));run.refresh_from_db();return run
    def test_offline_archive_hashes_and_every_report_link(self):
        run=self.recorded('broken')
        with bundle_export(run) as stream,zipfile.ZipFile(stream) as archive:
            names=archive.namelist();self.assertIn('START_HERE.txt',names)
            index=json.loads(archive.read('EXPORT.json'))
            self.assertEqual(index['native_run_id'],run.native_run_id)
            for name,entry in index['files'].items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),entry['sha256'])
            for name in names:
                if name.endswith('.html'):verify_local_links(name,archive.read(name),set(names))
    def test_history_and_original_partial_bytes_exported(self):
        source=settings.REPO_ROOT/'docs/evidence/phase7/executions/uncertain'
        original=self.recorded('recovered',source);path=run_path(original)
        relative='history/collection-000001/timeout/partial-events.jsonl'
        with bundle_export(original) as stream,zipfile.ZipFile(stream) as archive:
            self.assertEqual(archive.read('evidence/'+relative),(source/relative).read_bytes())
            self.assertEqual(archive.read('evidence/history/collection-000001/result.json'),(source/'history/collection-000001/result.json').read_bytes())
    def test_closed_inventory_rejects_added_history(self):
        original=self.recorded('broken');path=run_path(original)
        # A closed inventory must refuse adding a previously absent history.
        snapshot=path/'history/collection-000001';snapshot.mkdir(parents=True)
        (snapshot/'result.json').write_bytes(b'{"historical":"partial"}\n')
        with self.assertRaises(PolicyError):seal(original)
        self.assertTrue((snapshot/'result.json').exists())
    def test_artifact_rows_cannot_be_mutated_deleted_or_added_after_seal(self):
        run=self.recorded('after');artifact=Artifact.objects.filter(run=run).first()
        for operation in [lambda:Artifact.objects.filter(pk=artifact.pk).update(sha256='0'*64),
                          lambda:Artifact.objects.filter(pk=artifact.pk).delete(),
                          lambda:Artifact.objects.create(run=run,relative_path='new.json',sha256='0'*64,byte_count=0,content_type='text/plain')]:
            with self.assertRaises(DatabaseError),transaction.atomic():operation()
    def test_repeat_seal_is_idempotent_and_preserves_hashes(self):
        run=self.recorded('after');before=list(Artifact.objects.filter(run=run).values('id','sha256','relative_path'))
        seal(run);self.assertEqual(before,list(Artifact.objects.filter(run=run).values('id','sha256','relative_path')))
    def test_tamper_blocks_archive_and_status_verdict(self):
        run=self.recorded('after');path=run_path(run)/'cases/timeout/bundle/observations.jsonl';path.write_bytes(path.read_bytes()+b'\n')
        self.assertEqual(self.client.get(reverse('evidence_download',args=[run.pk])).status_code,409)
        result=self.client.get(reverse('run_status',args=[run.pk])).json()
        self.assertIsNone(result['summary']);self.assertFalse(result['cleanup_verified']);self.assertEqual(result['evidence_integrity'],'failed')
    def test_cross_tenant_export_and_retention_are_denied(self):
        run=self.recorded('after');other,_,_=tenant('Other evidence','other-evidence@example.test');client=signed_client(other,mfa=True)
        self.assertEqual(client.get(reverse('evidence_download',args=[run.pk])).status_code,404)
        self.assertEqual(client.post(reverse('retention_hold',args=[run.pk]),{'hold':'1'}).status_code,404)
        self.assertEqual(client.get(reverse('retention',args=[self.org.pk])).status_code,404)
    def test_download_has_safe_literal_attachment_and_audit(self):
        run=self.recorded('after');response=self.client.get(reverse('evidence_download',args=[run.pk]))
        self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Type'],'application/zip')
        self.assertEqual(response['Content-Disposition'],'attachment; filename="resmgrcheck-'+str(run.pk)+'.zip"')
        self.assertTrue(b''.join(response.streaming_content).startswith(b'PK'))
        self.assertTrue(AuditEvent.objects.filter(action='evidence.exported',object_id=str(run.pk),organization=self.org).exists())
    def test_traversal_backslash_absolute_and_control_names_denied(self):
        run=self.recorded('after');artifact=Artifact.objects.filter(run=run).first()
        for name in ['../other','/etc/passwd','cases\\timeout\\bundle','./../request.json']:
            artifact.relative_path=name
            with self.assertRaises((OSError,PolicyError)):open_artifact(artifact)
    def test_symlink_leaf_parent_and_hardlink_are_denied(self):
        run=self.recorded('after');artifact=Artifact.objects.get(run=run,relative_path='cases/timeout/bundle/plan.json')
        path=run_path(run)/artifact.relative_path;copy=path.with_name('saved-plan');path.rename(copy);path.symlink_to(copy)
        with self.assertRaises((OSError,PolicyError)):open_artifact(artifact)
        path.unlink();os.link(copy,path)
        with self.assertRaises(PolicyError):open_artifact(artifact)
        path.unlink();copy.rename(path)
        parent=path.parent;renamed=parent.with_name('saved-bundle');parent.rename(renamed);parent.symlink_to(renamed,target_is_directory=True)
        with self.assertRaises((OSError,PolicyError)):open_artifact(artifact)
    def test_unknown_report_external_or_missing_link_is_rejected(self):
        for body in [b'<a href="https://example.test/">outside</a>',b'<a href="../unknown.json">escape</a>']:
            with self.assertRaises(PolicyError):verify_local_links('report.html',body,{'report.html'})
    def test_retention_dry_run_then_exact_removal_keeps_metadata(self):
        run=self.aged();count=Artifact.objects.filter(run=run).count();path=run_path(run)
        dry=purge_run(run.pk);self.assertTrue(dry['dry_run']);self.assertTrue((path/'request.json').exists())
        result=purge_run(run.pk,apply=True);self.assertFalse(result['dry_run']);self.assertEqual(list(path.iterdir()),[])
        run.refresh_from_db();self.assertIsNotNone(run.purged_at);self.assertEqual(Artifact.objects.filter(run=run).count(),count)
        self.assertEqual(self.client.get(reverse('report_file',args=[run.pk,'report.html'])).status_code,404)
        self.assertContains(self.client.get(reverse('run_detail',args=[run.pk])),'Evidence expired')
    def test_hold_and_not_yet_due_retention_are_withheld(self):
        run=self.recorded('after')
        with self.assertRaises(PolicyError):purge_run(run.pk,apply=True)
        Run.objects.filter(pk=run.pk).update(finished_at=timezone.now()-timedelta(days=31),retention_hold=True)
        with self.assertRaises(PolicyError):purge_run(run.pk,apply=True)
    def test_unknown_file_and_symlink_block_retention_before_any_removal(self):
        run=self.aged();path=run_path(run);unknown=path/'unknown.txt';unknown.write_text('preserve')
        with self.assertRaises(PolicyError):purge_run(run.pk,apply=True)
        self.assertTrue((path/'request.json').exists());run.refresh_from_db();self.assertIsNone(run.purged_at)
        unknown.unlink();(path/'unknown-directory').symlink_to(path/'cases',target_is_directory=True)
        with self.assertRaises(PolicyError):purge_run(run.pk,apply=True)
        self.assertTrue((path/'request.json').exists())
    def test_active_replay_dependency_blocks_retention(self):
        run=self.aged()
        Run.objects.create(project=self.project,target=self.target,build=run.build,actor=self.owner,actor_auth_hash='0'*64,mfa_at=timezone.now(),native_run_id='pending-replay',operation='replay',original=run,idempotency_key='active-replay-key',intent_sha256='1'*64)
        with self.assertRaises(PolicyError):purge_run(run.pk,apply=True)
    def test_retention_policy_field_bounds_and_hold_audit(self):
        run=self.recorded('after');url=reverse('retention',args=[self.org.pk])
        for days in [0,6,3651]:self.assertEqual(self.client.post(url,{'retention_days':days}).status_code,400)
        self.assertEqual(self.client.post(url,{'retention_days':60}).status_code,302)
        self.assertEqual(self.client.post(reverse('retention_hold',args=[run.pk]),{'hold':'1'}).status_code,302)
        run.refresh_from_db();self.assertTrue(run.retention_hold)
    def test_due_account_erasure_preserves_pseudonymous_audit(self):
        person=user('erase-private@example.test',mfa=True);person.is_active=False;person.first_name='Private';person.save()
        record=AccountDeletion.objects.create(user=person,due_at=timezone.now()-timedelta(days=1))
        self.assertTrue(erase_account(record.pk)['dry_run']);person.refresh_from_db();self.assertEqual(person.first_name,'Private')
        erase_account(record.pk,apply=True);person.refresh_from_db()
        self.assertTrue(person.email.endswith('@deleted.invalid'));self.assertFalse(person.has_usable_password());self.assertEqual(person.first_name,'')
        self.assertFalse(EmailAddress.objects.filter(user=person).exists());self.assertFalse(Authenticator.objects.filter(user=person).exists())
        self.assertTrue(AuditEvent.objects.filter(actor=person,action='account.personal_data_erased').exists())
    def test_account_erasure_is_not_early_and_active_work_blocks_it(self):
        person=user('erase-not-due@example.test');person.is_active=False;person.save()
        record=AccountDeletion.objects.create(user=person,due_at=timezone.now()+timedelta(days=30))
        with self.assertRaises(PolicyError):erase_account(record.pk,apply=True)
