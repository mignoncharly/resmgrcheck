"""Retained real QNX evidence; disposable PostgreSQL/files; no new native execution."""
import copy,json,os,pwd,shutil,sys,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from django.test import TestCase,override_settings
from django.utils import timezone
from control.models import User,Organization,Project,Target,BuildRelease,Run,AccessCode,AccessGrant,AccessSession,AuditEvent,ExecutorSlot
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import recover_executor_collection as recovery
import executor_plan as plan
import provision_executor as provision
from resmgrcheck.contracts import load,canonical,digest,Invalid
from resmgrcheck.transport import Target as NativeTarget
from resmgrcheck import workflow,deployment

SOURCE=Path(__file__).resolve().parents[2]
ARCHIVE=SOURCE/'docs/evidence/phase10/executions/p10demo2-broken'
DRIVER='a'*40

class ControllerSelectionTests(unittest.TestCase):
    def test_missing_selection_reproduces_bootstrap_failure_then_exact_manifest_avoids_it(self):
        request=workflow.Request.parse(load(ARCHIVE/'request.json'))
        target=NativeTarget('lab',plan.target_config()['targets']['lab']);transport=Mock();transport.target=target
        transport.command.side_effect=[canonical({'kind':'owned-session','schema_version':1,'id':request.data['run_id'],
            'binding':digest(request.data),'uid':0}),canonical(request.data)]
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary)/'state';state.mkdir(mode=0o700)
            with patch.object(deployment,'STATE',state),patch.object(recovery,'STATE_ROOT',state),\
                patch.object(workflow,'bootstrap',side_effect=Invalid('targetctl unavailable: source qnxsdp-env.sh and run make qnx')) as bootstrap:
                with self.assertRaisesRegex(Invalid,'targetctl unavailable'):workflow.remote_request(target,request.data['run_id'],transport)
                bootstrap.assert_called_once()
                self.assertTrue(recovery.install_selection(request.data['deployment']))
                before=recovery.selected_path().read_bytes();stamp=recovery.selected_path().stat().st_mtime_ns
                self.assertFalse(recovery.install_selection(request.data['deployment']))
                actual=workflow.remote_request(target,request.data['run_id'],transport)
                self.assertEqual(actual.data,request.data);self.assertEqual(bootstrap.call_count,1)
                self.assertEqual(recovery.selected_path().read_bytes(),before);self.assertEqual(recovery.selected_path().stat().st_mtime_ns,stamp)
                calls=[call.args for call in transport.command.call_args_list]
                self.assertEqual(len(calls),2);self.assertTrue(all(call[1]=='read-session' for call in calls))

    def test_selection_never_replaces_unknown_files_or_follows_links(self):
        manifest=load(SOURCE/plan.MANIFESTS['before'][0])
        for kind in ['contents','symlink','directory','mode']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temporary:
                state=Path(temporary)/'state';state.mkdir(mode=0o700)
                with patch.object(recovery,'STATE_ROOT',state):
                    parent=state/'lab';parent.mkdir(mode=0o700);path=parent/'deployment.json'
                    if kind=='contents':path.write_text('{}');path.chmod(0o600)
                    elif kind=='symlink':path.symlink_to(SOURCE/plan.MANIFESTS['before'][0])
                    elif kind=='directory':path.mkdir()
                    else:path.write_bytes(canonical(manifest));path.chmod(0o644)
                    before=path.lstat()
                    with self.assertRaises((ValueError,OSError)):recovery.install_selection(manifest)
                    self.assertEqual(path.lstat().st_ino,before.st_ino)

    def test_interrupted_selection_publication_keeps_payload_out_of_final_path(self):
        manifest=load(SOURCE/plan.MANIFESTS['before'][0])
        with tempfile.TemporaryDirectory() as temporary,patch.object(recovery,'STATE_ROOT',Path(temporary)):
            Path(temporary).chmod(0o700)
            with patch('customer_runner.archive.publish',side_effect=InterruptedError),self.assertRaises(InterruptedError):recovery.install_selection(manifest)
            self.assertFalse(recovery.selected_path().exists());self.assertEqual(len(list(recovery.selected_path().parent.glob('.select-*'))),1)
            recovery.install_selection(manifest);self.assertEqual(json.loads(recovery.selected_path().read_bytes()),manifest)

    def test_frozen_unit_override_retains_runtime_check_and_tightens_umask(self):
        value=recovery.dropin(Path('/opt/resmgrcheck/operator-tools')/DRIVER).decode()
        self.assertNotIn('ExecStartPre=',value);self.assertNotIn('User=',value);self.assertNotIn('LoadCredential=',value)
        self.assertIn('UMask=0077',value);self.assertIn(' --worker',value)
        self.assertNotIn('bash',value);self.assertNotIn('sudo',value)

    def test_interrupted_recollection_initialization_is_not_published_and_can_resume(self):
        request=workflow.Request.parse(load(ARCHIVE/'request.json'))
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'recovered';old=os.umask(0o077)
            try:
                with patch('customer_runner.archive.publish',side_effect=InterruptedError),self.assertRaises(InterruptedError):recovery.reserve_recollection(path,request)
                self.assertFalse(path.exists());retained=list(Path(temporary).glob('.recover-init-*'));self.assertEqual(len(retained),1)
                recovery.reserve_recollection(path,request);before=(path/'state.json').read_bytes();stamp=(path/'state.json').stat().st_mtime_ns
                recovery.reserve_recollection(path,request);self.assertEqual((path/'state.json').read_bytes(),before)
                self.assertEqual((path/'state.json').stat().st_mtime_ns,stamp);self.assertTrue(retained[0].exists())
                (path/'unexpected-link').symlink_to('/etc/passwd')
                with self.assertRaisesRegex(ValueError,'recovery_resource_type_or_owner'):recovery.reserve_recollection(path,request)
            finally:os.umask(old)

class RecollectionEvidenceTests(unittest.TestCase):
    def fixture(self,root):
        original=root/'original';original.mkdir();(original/'cases/timeout').mkdir(parents=True)
        for name in ['request.json','cases/timeout/status.json']:
            (original/name).write_bytes((ARCHIVE/name).read_bytes())
        raw=(ARCHIVE/'cases/timeout/bundle/observations.jsonl').read_bytes();partial=raw[:raw.index(b'\n')+1]
        (original/'cases/timeout/partial-events.jsonl').write_bytes(partial);(original/'cases/timeout/partial-events.jsonl').chmod(0o640)
        result=root/'recollected';shutil.copytree(ARCHIVE,result)
        run=SimpleNamespace(build=SimpleNamespace(manifest=load(SOURCE/plan.MANIFESTS['before'][0])))
        return original,result,run

    def test_real_recorded_FAIL_cleanup_and_partial_prefix_are_verified_without_changing_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            original,result,run=self.fixture(Path(temporary));snapshot={str(p.relative_to(original)):p.read_bytes() for p in original.rglob('*') if p.is_file()}
            with patch.object(recovery,'NATIVE','p10demo2-broken'),patch('control.engine.run_path',return_value=original),\
                patch.object(recovery.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid())):
                proof=recovery.verify_recollection(run,result)
            self.assertEqual(proof['canonical_verdict'],'FAIL');self.assertTrue(proof['cleanup_verified']);self.assertTrue(proof['same_supervisor'])
            self.assertEqual({str(p.relative_to(original)):p.read_bytes() for p in original.rglob('*') if p.is_file()},snapshot)

    def test_incomplete_changed_identity_modified_events_or_supervisor_never_prove_cleanup(self):
        for kind in ['incomplete','events','supervisor','request']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temporary:
                original,result,run=self.fixture(Path(temporary))
                if kind=='incomplete':(result/'cases/timeout/bundle/bundle.json').unlink()
                elif kind=='events':(result/'cases/timeout/bundle/observations.jsonl').write_bytes(b'tampered')
                elif kind=='supervisor':
                    path=original/'cases/timeout/status.json';value=load(path);value['supervisor_pid']=str(int(value['supervisor_pid'])+1);path.write_bytes(canonical(value))
                else:
                    path=original/'request.json';value=load(path);value['mode']='corrected';path.write_bytes(canonical(value))
                with patch.object(recovery,'NATIVE','p10demo2-broken'),patch('control.engine.run_path',return_value=original),\
                    patch.object(recovery.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid())),self.assertRaises((ValueError,OSError)):
                    recovery.verify_recollection(run,result)

class ExecutorContextRecoveryTests(unittest.TestCase):
    def test_interrupted_stop_attempt_restores_canonical_executor_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            drop=Path(temporary);calls=[]
            def command(argv,**kwargs):
                calls.append(argv)
                if argv[:2]==['systemctl','stop']:raise provision.ops.CheckFailed('command_failed_systemctl')
                return b''
            with patch.object(provision,'DROP_DIR',drop),patch.object(provision.ops,'command',side_effect=command),self.assertRaises(provision.ops.CheckFailed):
                recovery.run_in_executor(drop/'tool',DRIVER)
            self.assertEqual(calls,[['systemctl','stop','resmgrcheck-executor.service'],['systemctl','start','resmgrcheck-executor.service']])
            self.assertEqual(list(drop.iterdir()),[])
    def test_success_and_failure_restore_only_the_own_override_and_service(self):
        for fails in [False,True]:
            with self.subTest(fails=fails),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);drop=root/'unit.d';drop.mkdir();private=root/'private';private.mkdir();state=root/'state';state.mkdir()
                tool=root/'tools'/DRIVER;calls=[];starts=0
                proof={'passed':True,'driver_revision':DRIVER,'application':plan.APPLICATION,'web_run_id':recovery.RUN,
                    'kind':'actual-systemd-same-ID-recollection','canonical_verdict':'FAIL','same_supervisor':True,'cleanup_verified':True,
                    'original_ERROR_retained':True,'evidence_directory':str(private/('recovered-'+recovery.RUN+'-'+DRIVER))}
                path=private/('recovered-'+DRIVER+'.json');path.write_bytes(canonical(proof));path.chmod(0o600)
                def command(argv,**kwargs):
                    nonlocal starts
                    calls.append(argv)
                    if argv[:2]==['systemctl','start']:
                        starts+=1
                        if fails and starts==1:raise provision.ops.CheckFailed('command_failed_systemctl')
                    return b''
                with patch.object(provision,'DROP_DIR',drop),patch.object(plan,'STATE',state),patch.object(recovery,'PRIVATE',private),\
                    patch.object(recovery.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid())),patch.object(provision.ops,'command',side_effect=command):
                    if fails:
                        with self.assertRaises(provision.ops.CheckFailed):recovery.run_in_executor(tool,DRIVER)
                    else:self.assertEqual(recovery.run_in_executor(tool,DRIVER),proof)
                self.assertFalse((drop/'91-resmgrcheck-collection-recovery.conf').exists())
                self.assertEqual(calls[-1],['systemctl','start','resmgrcheck-executor.service'])
                self.assertEqual(starts,2)
                self.assertTrue(all(command[0]=='systemctl' and (len(command)==2 or command[-1]=='resmgrcheck-executor.service') for command in calls))

    def test_unknown_override_is_preserved_without_stopping_any_service(self):
        with tempfile.TemporaryDirectory() as temporary:
            drop=Path(temporary);path=drop/'91-resmgrcheck-collection-recovery.conf';path.write_bytes(b'unknown');path.chmod(0o644)
            with patch.object(provision,'DROP_DIR',drop),patch.object(provision.ops,'command') as command,self.assertRaisesRegex(ValueError,'recovery_override_changed'):
                recovery.run_in_executor(drop/'tool',DRIVER)
            command.assert_not_called();self.assertEqual(path.read_bytes(),b'unknown')

class VerifiedLeaseReleaseTests(TestCase):
    def setUp(self):
        self.account=User.objects.create_user('accept-'+recovery.ATTEMPT[:18],None,is_active=False)
        org=Organization.objects.create(pk=plan.IDS['organization'],name='Exact fixture')
        project=Project.objects.create(pk=plan.IDS['project'],organization=org,name='Exact fixture',created_by=self.account)
        target=Target.objects.create(pk=plan.IDS['target'],project=project,name='Exact lab',approved=True,binding=plan.IDS['target'],state='quarantined',quarantine_reason='cleanup_or_coverage_unestablished')
        build=BuildRelease.objects.create(pk=plan.IDS['before'],target=target,label='Exact before',approved=True,binding=plan.IDS['before'])
        now=timezone.now();code=AccessCode.objects.create(organization=org,created_by=self.account,verifier='0'*64,revoked_at=now)
        AccessGrant.objects.create(code=code,project=project,can_run=True)
        session=AccessSession.objects.create(code=code,browser_key_hash='0'*64,policy_version=1,last_access=now,expires_at=now,revoked_at=now)
        token=uuid.uuid4();self.run=Run.objects.create(pk=recovery.RUN,project=project,target=target,build=build,access_session=session,
            actor_auth_hash='0'*64,mfa_at=now,native_run_id=recovery.NATIVE,operation='run',profile='sensor',suite='profile',fixture_mode='ignore-unblock',
            state='blocked',error_code='cleanup_or_coverage_unestablished',summary={'cases':[{'verdict':'ERROR'}]},lease_token=token,lease_expires=now,
            process_facts={'local_child_exit_observed':True,'local_child_returncode':2},
            started_at=now,finished_at=now,idempotency_key='recollection-fixture',intent_sha256='0'*64)
        self.slot=ExecutorSlot.objects.create(name='private-qnx',run=self.run,token=token,expires_at=now);ExecutorSlot.objects.create(name='dispatch')
        self.run.refresh_from_db()
        for action in ['https.acceptance.created','https.acceptance.closed']:
            AuditEvent.objects.create(actor=self.account,action=action,details={'acceptance_id':str(uuid.UUID(recovery.ATTEMPT))})
    def test_no_release_without_cleanup_and_idempotent_release_preserves_ERROR_and_authority(self):
        with patch.object(recovery,'original_inventory',return_value={'trusted':'fixture'}):
            with self.assertRaisesRegex(ValueError,'cleanup_proof_required'):recovery.release_verified(self.run,{'cleanup_verified':False},DRIVER)
            self.slot.refresh_from_db();self.assertEqual(self.slot.run_id,self.run.pk)
            proof={'cleanup_verified':True,'native_run_id':recovery.NATIVE,'original_ERROR_retained':True,'canonical_verdict':'FAIL',
                'same_supervisor':True,'partial_evidence_prefix_preserved':True,'bundle_id':'1'*64}
            recovery.release_verified(self.run,proof,DRIVER);recovery.release_verified(self.run,proof,DRIVER)
        self.run.refresh_from_db();self.slot.refresh_from_db();self.run.target.refresh_from_db()
        self.assertIsNone(self.slot.run_id);self.assertEqual(self.run.state,'blocked');self.assertEqual(self.run.summary['cases'][0]['verdict'],'ERROR')
        self.assertFalse(self.run.target_cleanup_verified);self.assertEqual(self.run.target.state,'available')
        self.assertEqual(AuditEvent.objects.filter(action='production.native_collection.recovered').count(),1)
        self.account.refresh_from_db();self.assertFalse(self.account.is_active)
    def test_other_work_wrong_lease_or_missing_audit_cannot_be_adopted(self):
        self.assertEqual(recovery.exact_run().pk,self.run.pk)
        ExecutorSlot.objects.filter(pk=self.slot.pk).update(token=uuid.uuid4())
        with self.assertRaisesRegex(ValueError,'blocked_lease_binding_differs'):recovery.exact_run()
        ExecutorSlot.objects.filter(pk=self.slot.pk).update(token=self.run.lease_token)
        User.objects.filter(pk=self.account.pk).update(is_active=True)
        with self.assertRaisesRegex(ValueError,'original_authority_not_closed'):recovery.exact_run()
