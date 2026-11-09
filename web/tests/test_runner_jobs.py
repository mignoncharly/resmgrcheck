"""Job authorization/reconnect/upload/ingestion. Recorded native bytes stay labeled."""
import base64,copy,hashlib,io,json,os,shutil,tarfile,tempfile,time,uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase,TransactionTestCase,override_settings
from django.db import DatabaseError,transaction,connection
from django.utils import timezone
from customer_runner import protocol as wire
from customer_runner.archive import pack,unpack,publish
from customer_runner.client import create
from customer_runner import work
from control import runners,runner_jobs,runner_ingest
from control.engine import run_path
from control.jobs import enqueue,QueueError,auth_fingerprint
from control.models import BuildRelease,Run,RunnerJob,RunnerChunk,CustomerRunner,Membership,Artifact
from control.worker import claim as local_claim
from resmgrcheck.build_identity import source_hash
from . import test_runners as baseline

@override_settings(RUNNER_ENABLED=True,RUNNER_SIGNING_KEY='c'*64)
class RunnerJobsTests(TestCase):
    enrollment=baseline.RunnerTests.enrollment
    enroll=baseline.RunnerTests.enroll
    post=baseline.RunnerTests.post
    beat=baseline.RunnerTests.beat
    def setUp(self):
        baseline.RunnerTests.setUp(self)
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
        self.overrides=override_settings(MEDIA_ROOT=self.root/'evidence',PRIVATE_ROOT=self.root/'private');self.overrides.enable();self.addCleanup(self.overrides.disable)
        self.source=settings.REPO_ROOT/'docs/evidence/phase10/executions/p10demo2-normal'
        self.record=json.loads((self.source/'request.json').read_text())
        self.info['target_identity']=self.record['target_identity'];self.info['engine_sha256']=source_hash(settings.REPO_ROOT)
        self.enroll();runners.approve(self.user,self.target,self.runner.inventory_sha256)
        self.post('exchange',self.beat());self.target.refresh_from_db();self.runner=CustomerRunner.objects.select_related('target').get(pk=self.target.pk)
        self.build=BuildRelease.objects.create(target=self.target,label='Recorded native build fixture',manifest=self.record['deployment'],approved=True)
        self.request=SimpleNamespace(user=self.user,session=self.browser.session)

    def queued(self,key='customer-job-idempotency-key'):
        return enqueue(self.request,self.project,self.target,self.build,profile='sensor',suite='profile',mode='fixed',key=key)[0]

    def offered(self):
        result=runner_jobs.poll(self.runner,{'operation':'poll','inventory':self.info});return RunnerJob.objects.get(pk=result['job']['run_id']),result

    def begin(self,job):
        return runner_jobs.begin(self.runner,{'operation':'begin','run_id':str(job.pk),'ticket':str(job.ticket),'intent_sha256':job.run.intent_sha256})

    def upload(self,job,raw):
        for index,start in enumerate(range(0,len(raw),wire.CHUNK_SIZE)):
            runner_jobs.chunk(self.runner,{'operation':'chunk','run_id':str(job.pk),'ticket':str(job.ticket),
                'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'index':index,'data':base64.b64encode(raw[start:start+wire.CHUNK_SIZE]).decode()})
        return runner_jobs.finish(self.runner,{'operation':'finish','run_id':str(job.pk),'ticket':str(job.ticket)})

    def recorded_job(self):
        # Import the exact original native ID. Never relabel saved bytes as a new run.
        run=Run.objects.create(project=self.project,target=self.target,build=self.build,actor=self.user,
            actor_auth_hash=auth_fingerprint(self.user),mfa_at=timezone.now(),native_run_id=self.record['run_id'],operation='run',
            profile='sensor',suite='profile',fixture_mode='fixed',idempotency_key='recorded-runner-ingest-fixture',intent_sha256='1'*64,state='queued')
        job,_=self.offered();self.assertTrue(self.begin(job)['launch_allowed'])
        archive=self.root/'recorded.tar';pack(self.source,archive);return run,job,archive.read_bytes()

    def test_deduplication_single_launch_and_exact_id_after_disconnect(self):
        run=self.queued();self.assertEqual(run.pk,self.queued().pk);job,first=self.offered()
        self.assertIsNone(local_claim())
        again=runner_jobs.poll(self.runner,{'operation':'poll','inventory':self.info});self.assertEqual(first['job'],again['job'])
        permit=self.begin(job);self.assertTrue(permit['launch_allowed']);self.assertEqual(permit['native_run_id'],run.native_run_id)
        self.assertFalse(self.begin(job)['launch_allowed'])
        uncertain=runner_jobs.uncertain(self.runner,{'operation':'uncertain','run_id':str(run.pk),'ticket':str(job.ticket)})
        self.assertEqual(uncertain['recover_native_run_id'],run.native_run_id);self.assertFalse(uncertain['cleanup_verified'])
        again=runner_jobs.poll(self.runner,{'operation':'poll','inventory':self.info});self.assertEqual(again['job']['native_run_id'],run.native_run_id)
        self.assertFalse(self.begin(job)['launch_allowed'])

    def test_revoked_user_cancel_and_expired_offer_prevent_first_grant(self):
        run=self.queued();job,_=self.offered();Membership.objects.filter(user=self.user).update(active=False)
        result=self.begin(job);self.assertFalse(result['launch_allowed']);run.refresh_from_db();self.assertEqual(run.state,'rejected')

    def test_cancelled_offer_prevents_launch(self):
        run=self.queued();job,_=self.offered();Run.objects.filter(pk=run.pk).update(cancel_requested=True)
        self.assertFalse(self.begin(job)['launch_allowed'])

    def test_target_queue_daily_and_offline_limits_are_enforced(self):
        self.queued();self.queued('second-customer-job-key')
        with self.assertRaisesRegex(QueueError,'target_queue_full'):self.queued('third-customer-job-key')
        CustomerRunner.objects.filter(pk=self.target.pk).update(last_seen=timezone.now()-timedelta(seconds=91))
        with self.assertRaises(QueueError):self.queued('offline-customer-job-key')

    def test_daily_limit_counts_completed_requests_without_refunding(self):
        CustomerRunner.objects.filter(pk=self.target.pk).update(daily_limit=1)
        run=self.queued();Run.objects.filter(pk=run.pk).update(state='rejected')
        with self.assertRaisesRegex(QueueError,'target_daily_quota'):self.queued('second-daily-customer-job')

    def test_expired_queue_authority_cannot_gain_a_delayed_launch(self):
        run=self.queued();future=timezone.now()+timedelta(minutes=16)
        with patch('control.runner_jobs.timezone.now',return_value=future):
            result=runner_jobs.poll(self.runner,{'operation':'poll','inventory':self.info})
        self.assertNotIn('job',result);run.refresh_from_db();self.assertEqual(run.state,'rejected')

    def test_job_provenance_cannot_be_deleted_to_obtain_a_second_launch_grant(self):
        self.queued();job,_=self.offered();self.begin(job)
        with self.assertRaises(DatabaseError),transaction.atomic():RunnerJob.objects.filter(pk=job.pk).delete()
        self.assertFalse(self.begin(job)['launch_allowed'])

    def test_customer_external_lifecycle_and_unapproved_build_are_rejected(self):
        self.build.approved=False;self.build.save(update_fields=['approved'])
        with self.assertRaisesRegex(QueueError,'build_not_approved'):self.queued()
        self.build.approved=True;self.build.save(update_fields=['approved'])
        changed=copy.deepcopy(self.info);changed['attachment']='external-attach'
        with patch('control.runner_jobs.CustomerRunner.objects.select_related') as query:
            self.runner.inventory=changed;query.return_value.get.return_value=self.runner
            with self.assertRaises(wire.ProtocolError):runner_jobs.capable(self.target,self.build,'sensor','lifecycle','fixed')

    def test_foreign_job_ticket_or_signature_cannot_submit_or_begin(self):
        self.queued();job,_=self.offered()
        with self.assertRaises(wire.ProtocolError):runner_jobs.begin(self.runner,{'operation':'begin','run_id':str(job.pk),'ticket':str(uuid.uuid4()),'intent_sha256':job.run.intent_sha256})
        with self.assertRaises(DatabaseError),transaction.atomic():RunnerJob.objects.filter(pk=job.pk).update(intent={})

    def test_upload_is_idempotent_bounded_and_cannot_change_chunk_or_archive(self):
        self.queued();job,_=self.offered();self.begin(job);raw=b'a'*100
        body={'operation':'chunk','run_id':str(job.pk),'ticket':str(job.ticket),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':100,'index':0,'data':base64.b64encode(raw).decode()}
        self.assertEqual(runner_jobs.chunk(self.runner,body),runner_jobs.chunk(self.runner,body))
        changed=dict(body,data=base64.b64encode(b'b'*100).decode())
        with self.assertRaises(wire.ProtocolError):runner_jobs.chunk(self.runner,changed)
        with self.assertRaises(DatabaseError),transaction.atomic():RunnerChunk.objects.filter(job=job).update(data=b'replace')
        with self.assertRaises(DatabaseError),transaction.atomic():RunnerChunk.objects.filter(job=job).delete()
        with self.assertRaises(wire.ProtocolError):runner_jobs.chunk(self.runner,dict(body,bytes=wire.MAX_ARCHIVE+1))

    def test_incomplete_upload_cannot_request_ingestion(self):
        self.queued();job,_=self.offered();self.begin(job)
        with self.assertRaises(wire.ProtocolError):runner_jobs.finish(self.runner,{'operation':'finish','run_id':str(job.pk),'ticket':str(job.ticket)})
        self.assertIsNone(runner_ingest.claim())

    def test_recorded_native_bytes_are_revalidated_sealed_and_tenant_scoped(self):
        run,job,raw=self.recorded_job();self.assertEqual(self.upload(job,raw)['job_state'],'received')
        self.assertFalse(run_path(run).exists());claimed=runner_ingest.claim();self.assertTrue(runner_ingest.execute(*claimed))
        run.refresh_from_db();self.assertEqual(run.state,'completed');self.assertTrue(run.target_cleanup_verified)
        self.assertEqual(run.native_run_id,self.record['run_id']);self.assertTrue(Artifact.objects.filter(run=run,relative_path='web-evidence-v2.json').exists())
        self.assertEqual(RunnerChunk.objects.filter(job=job).count(),0)
        self.assertEqual(self.browser.get('/app/runs/'+str(run.pk)+'/').status_code,200)
        from .helpers import tenant,signed_client
        other,_,_=tenant('Foreign result','foreign-runner-result@example.test')
        self.assertEqual(signed_client(other,mfa=True).get('/app/runs/'+str(run.pk)+'/').status_code,404)

    def test_unknown_output_is_preserved_and_never_adopted(self):
        run,job,raw=self.recorded_job();output=run_path(run);output.mkdir(parents=True);(output/'unknown').write_text('preserve')
        self.upload(job,raw);self.assertFalse(runner_ingest.execute(*runner_ingest.claim()))
        self.assertEqual((output/'unknown').read_text(),'preserve');run.refresh_from_db();self.assertEqual(run.state,'blocked');self.assertFalse(run.target_cleanup_verified)

    def test_invalid_evidence_quarantines_without_any_pass_or_cleanup_claim(self):
        self.queued();job,_=self.offered();self.begin(job);self.upload(job,b'invalid authenticated customer upload')
        self.assertFalse(runner_ingest.execute(*runner_ingest.claim()));job.run.refresh_from_db()
        self.assertFalse(job.run.target_cleanup_verified);self.assertEqual(job.run.state,'blocked')

    def test_archive_rejects_links_traversal_unknown_members_and_destination_replacement(self):
        for name,kind in [('../escape',tarfile.REGTYPE),('request.json',tarfile.SYMTYPE),('ssh-key',tarfile.REGTYPE)]:
            with self.subTest(name=name):
                data=io.BytesIO()
                with tarfile.open(fileobj=data,mode='w:') as tar:
                    member=tarfile.TarInfo(name);member.type=kind;member.linkname='/etc/passwd';tar.addfile(member)
                path=self.root/('bad-'+uuid.uuid4().hex+'.tar');path.write_bytes(data.getvalue())
                with self.assertRaises(wire.ProtocolError):unpack(path,self.root/uuid.uuid4().hex)
        source=self.root/'new';source.mkdir();destination=self.root/'occupied';destination.mkdir()
        with self.assertRaises(OSError):publish(source,destination)
        self.assertTrue(source.exists());self.assertTrue(destination.exists())

    def test_agent_persists_launch_intent_before_grant_and_never_relaunches_on_retry(self):
        run=self.queued();job,offer=self.offered();configuration={'target_id':str(self.target.pk),'project_id':str(self.project.pk),'organization_id':str(self.org.pk),
            'engine_root':str(settings.REPO_ROOT),'attachment':'managed-fixture','allowed_modes':['corrected'],'manifests':{self.build.manifest['deployment_id']:str(self.root/'manifest')},'alias':'local','target_config':'/not-read'}
        fake=SimpleNamespace(exchange=lambda body:offer if body['operation']=='poll' else (_ for _ in ()).throw(wire.ProtocolError('lost reply')))
        with patch.object(work,'validate',return_value=(Path('profile'),'manifest')),patch.object(work,'storage',return_value={}),patch.object(work,'command') as command:
            with self.assertRaises(wire.ProtocolError):work.run_once(fake,configuration,self.root,self.info)
            self.assertTrue((self.root/('job-'+str(run.pk))/'launch-intent').exists())
            command.assert_not_called()
            # The second attempt collects the same ID; it never asks begin again.
            calls=[]
            def record(body):calls.append(body['operation']);return offer if body['operation']=='poll' else {}
            fake.exchange=record
            command.side_effect=wire.ProtocolError('no existing target record')
            with self.assertRaises(wire.ProtocolError):work.run_once(fake,configuration,self.root,self.info)
            self.assertEqual(command.call_args[0][1][0],'collect');self.assertIn(run.native_run_id,command.call_args[0][1]);self.assertNotIn('begin',calls)

    def test_actual_runtime_grants_separate_machine_upload_and_private_sealing(self):
        import re
        from psycopg import sql
        names=['resmgr_web','resmgr_exec','resmgr_ai','resmgr_backup']
        roles={name:'rmctest_'+name+'_'+uuid.uuid4().hex[:8] for name in names}
        with connection.cursor() as cursor:
            for role in roles.values():cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role)))
            text=(settings.REPO_ROOT/'web/ops/production/database-grants.sql').read_text()
            text='\n'.join(line for line in text.splitlines() if not line.startswith('\\'))
            self.assertEqual(connection.settings_dict['NAME'],'test_resmgrcheck_web')
            text=text.replace('DATABASE resmgrcheck_web','DATABASE test_resmgrcheck_web')
            for original,role in roles.items():text=re.sub(r'\b'+original+r'\b',role,text)
            cursor.execute(text)
            expectations={
                'resmgr_web':[('control_runnerchunk','INSERT',True),('control_runnerchunk','UPDATE',False),('control_runnerchunk','DELETE',False),('control_runnerjob','INSERT',True),('control_runnerjob','DELETE',False),('control_artifact','INSERT',False)],
                'resmgr_exec':[('control_runnerchunk','SELECT',True),('control_runnerchunk','DELETE',True),('control_runnerjob','UPDATE',True),('control_runnerjob','INSERT',False),('control_customerrunner','UPDATE',False),('control_artifact','INSERT',True)],
                'resmgr_ai':[('control_runnerjob','UPDATE',False),('control_runnerchunk','INSERT',False)],
                'resmgr_backup':[('control_runnerjob','SELECT',True),('control_runnerchunk','SELECT',True),('control_runnerchunk','DELETE',False)]}
            for original,checks in expectations.items():
                cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(roles[original])))
                for table,privilege,expected in checks:
                    cursor.execute('SELECT has_table_privilege(current_user,%s,%s)',[table,privilege]);self.assertEqual(cursor.fetchone()[0],expected,(original,table,privilege))
                cursor.execute('RESET ROLE')

class RunnerMigrationBackupTests(TransactionTestCase):
    def test_additive_migration_roundtrip_preserves_legacy_rows_and_restores_legacy_archive(self):
        from django.db.migrations.executor import MigrationExecutor
        from control import backup
        from control.models import AuditEvent
        from .helpers import tenant
        self.assertEqual(connection.settings_dict['NAME'],'test_resmgrcheck_web')
        user,org,project=tenant('Migration preservation','runner-migration@example.test')
        event=AuditEvent.objects.create(actor=user,organization=org,action='fixture.pre_runner_preservation')
        newer=('control','0019_runnerjob_runnerchunk');older=('control','0017_session_and_scope_integrity')
        # Only the disposable test DB, with no runner rows. Production rollback
        # keeps additive tables/records and changes code only after quiescence.
        self.assertEqual(CustomerRunner.objects.count(),0)
        try:
            MigrationExecutor(connection).migrate([older])
            self.assertTrue(AuditEvent.objects.filter(pk=event.pk,action='fixture.pre_runner_preservation').exists())
            with tempfile.TemporaryDirectory() as temporary,override_settings(PRIVATE_ROOT=Path(temporary)):
                root=Path(temporary);key=root/'backup-key';create(key,os.urandom(32));archive=root/'legacy.rmc'
                saved=backup.snapshot(archive,key);restored=backup.restore_drill(archive,key)
                self.assertEqual(saved['encrypted_sha256'],restored['encrypted_sha256']);self.assertTrue(restored['passed'])
                with connection.cursor() as cursor:self.assertEqual(set(backup.identity(cursor)['counts']),set(backup.TABLES))
        finally:MigrationExecutor(connection).migrate([newer])
        self.assertTrue(AuditEvent.objects.filter(pk=event.pk,action='fixture.pre_runner_preservation').exists())
        self.assertEqual(CustomerRunner.objects.count(),0)
