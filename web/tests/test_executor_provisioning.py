"""Real disposable files/PostgreSQL; privileged systemd/signal effects modeled."""
import json,os,pwd,stat,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch,Mock
from django.test import TestCase
from django.utils import timezone
from control.models import User,Organization,Project,Target,BuildRelease,AuditEvent,Run
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import executor_plan as plan
import executor_operator as operator
import provision_executor as driver
import executor_probe as probe
from executor_native_browser import NativeJourney

DRIVER='6'*40

class PrivateBindingFilesTests(unittest.TestCase):
    def failed_selection_fixture(self,root):
        config=root/'executor';config.mkdir(mode=0o700)
        names=['ssh-key','known-hosts','ssh-config','target.json','registry.json','before-deployment.json','after-deployment.json']
        for name in names:(config/name).write_bytes(name.encode());(config/name).chmod(0o600)
        journal={'kind':'approved-production-qnx-executor-v1','application':plan.APPLICATION,'driver_revision':driver.FAILED_SELECTION_DRIVER,
            'ids':plan.IDS,'phase':'approved_after_actual_runtime_probe','baseline':{'fixed':'fixture'},
            'private_resource_hashes':{name:plan.digest(name.encode()) for name in names}}
        proof={'passed':True,'kind':'actual-systemd-executor-probe','application':plan.APPLICATION,'driver_revision':driver.FAILED_SELECTION_DRIVER,'database_grants_verified':True}
        failure={'passed':False,'phase':'acceptance','driver_revision':driver.FAILED_SELECTION_DRIVER,'failed_check':'exact_approved_native_plan_required','secrets_printed':False}
        for name,value in [('state.json',journal),('runtime-proof.json',proof),('operator-failure.json',failure)]:driver.ops.record(root/name,value)
        return config,journal,proof,failure

    def test_known_completed_provisioning_resume_preserves_history_and_runtime_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);config,journal,proof,failure=self.failed_selection_fixture(root)
            with patch.object(plan,'STATE',root),patch.object(plan,'CONFIG',config):
                path=driver.preserve_failed_selection(journal,os.getuid());self.assertEqual(json.loads(path.read_text()),{'journal':journal,'runtime_proof':proof,'operator_failure':failure})
                # Simulate interruption after archive but before journal transition;
                # a failed read-only preflight may have replaced the latest failure.
                driver.ops.record(root/'operator-failure.json',{'failed_check':'later_read_only_probe'})
                self.assertEqual(driver.preserve_failed_selection(journal,os.getuid()),path)
                updated=driver.bind_resume(journal,root/'state.json',DRIVER);driver.verify_resume_history(updated)
                self.assertEqual(updated['private_resource_hashes'],journal['private_resource_hashes'])
                self.assertEqual(json.loads((root/'runtime-proof.json').read_text()),proof)
                self.assertEqual(json.loads(path.read_text())['journal'],journal)

    def test_unknown_failure_native_intent_or_changed_private_bytes_cannot_be_adopted(self):
        for change in ['failure','intent','bytes','phase']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);config,journal,proof,failure=self.failed_selection_fixture(root)
                if change=='failure':driver.ops.record(root/'operator-failure.json',{**failure,'failed_check':'different'})
                if change=='intent':(root/'native-unknown.intent.json').write_text('{}')
                if change=='bytes':(config/'ssh-key').write_bytes(b'preserve changed bytes')
                if change=='phase':journal={**journal,'phase':'prepared'}
                with patch.object(plan,'STATE',root),patch.object(plan,'CONFIG',config),self.assertRaises(ValueError):driver.preserve_failed_selection(journal,os.getuid())
                self.assertFalse((root/('attempt-'+driver.FAILED_SELECTION_DRIVER+'.json')).exists())
    def test_exact_private_file_is_resumable_and_unknown_contents_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'key'
            driver.exact_file(path,b'fixture only',os.getuid(),0o600)
            before=(path.read_bytes(),path.stat().st_mtime_ns)
            driver.exact_file(path,b'fixture only',os.getuid(),0o600)
            self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)
            with self.assertRaisesRegex(ValueError,'existing_resource_differs'):driver.exact_file(path,b'different',os.getuid(),0o600)
            self.assertEqual(path.read_bytes(),before[0])

    def test_private_file_symlinks_modes_links_and_oversize_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'key';path.write_bytes(b'keep');path.chmod(0o600)
            link=root/'alias';link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'symlink'):plan.read_owned(link,os.getuid(),{0o600})
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError,'protection'):plan.read_owned(path,os.getuid(),{0o600})
            path.chmod(0o600);os.link(path,root/'hardlink')
            with self.assertRaisesRegex(ValueError,'protection'):plan.read_owned(path,os.getuid(),{0o600})
            (root/'hardlink').unlink()
            with self.assertRaisesRegex(ValueError,'protection'):plan.read_owned(path,os.getuid(),{0o600},limit=2)
            self.assertEqual(path.read_bytes(),b'keep')

    def test_interrupted_owned_file_publication_resumes_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);first=root/'first';second=root/'second'
            driver.exact_file(first,b'one',os.getuid(),0o600)
            with patch.object(driver.ops,'new_file',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
                driver.exact_file(second,b'two',os.getuid(),0o600)
            driver.exact_file(first,b'one',os.getuid(),0o600);driver.exact_file(second,b'two',os.getuid(),0o600)
            self.assertEqual(first.read_bytes(),b'one');self.assertEqual(second.read_bytes(),b'two')

    def test_interruption_after_fsync_retains_temporary_and_retry_publishes_complete_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'registry.json'
            with patch('customer_runner.archive.publish',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
                driver.exact_file(path,b'complete fixture',os.getuid(),0o600)
            self.assertFalse(path.exists());retained=list(root.iterdir());self.assertEqual(len(retained),1)
            self.assertEqual(retained[0].read_bytes(),b'complete fixture')
            driver.exact_file(path,b'complete fixture',os.getuid(),0o600)
            self.assertEqual(path.read_bytes(),b'complete fixture');self.assertTrue(retained[0].exists())

    def test_probe_refuses_root_outside_service_context_before_any_private_read(self):
        with patch.object(probe.os,'geteuid',return_value=0),patch.object(probe.plan,'read_owned') as read:
            with self.assertRaisesRegex(ValueError,'actual_executor_context_required'):probe.probe()
            read.assert_not_called()

    def test_exact_registry_and_ssh_options_cannot_select_a_browser_host(self):
        data=plan.registry();self.assertEqual(set(data['targets']),{plan.IDS['target']})
        row=data['targets'][plan.IDS['target']]
        self.assertEqual(row['project_id'],plan.IDS['project']);self.assertEqual(set(row['builds']),{plan.IDS['before'],plan.IDS['after']})
        raw=plan.ssh_config();self.assertIn(b'HostName 127.0.0.1',raw);self.assertIn(b'Port 22220',raw)
        self.assertIn(b'StrictHostKeyChecking yes',raw);self.assertIn(b'ForwardAgent no',raw)
        for forbidden in [b'ProxyCommand',b'ProxyJump',b'Include',b'ForwardX11']:self.assertNotIn(forbidden,raw)

    def test_probe_dropin_keeps_identity_credentials_and_sandbox_in_canonical_unit(self):
        raw=driver.dropin(Path('/opt/resmgrcheck/operator-tools')/DRIVER)
        self.assertIn(b'-I -B',raw);self.assertIn(b'Type=oneshot',raw)
        for setting in [b'User=',b'Group=',b'LoadCredential=',b'ProtectSystem=',b'IPAddressAllow=',b'NoNewPrivileges=']:
            self.assertNotIn(setting,raw)
        unit=(Path(__file__).resolve().parents[1]/'ops/production/resmgrcheck-executor.service').read_bytes()
        self.assertIn(b'User=resmgr-exec',unit);self.assertIn(b'LoadCredential=application-key:',unit);self.assertIn(b'ProtectSystem=strict',unit)

    def test_own_probe_override_removed_and_unknown_override_never_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'own.d';directory.mkdir();path=directory/'probe.conf';path.write_bytes(b'known');path.chmod(0o644)
            with patch.object(driver,'DROP_DIR',directory),patch.object(driver,'DROP',path),patch.object(driver.ops,'command',return_value=b''):
                with self.assertRaisesRegex(ValueError,'qualification_override_changed'):driver.remove_dropin(b'other')
                self.assertEqual(path.read_bytes(),b'known');driver.remove_dropin(b'known')
                self.assertFalse(path.exists());self.assertFalse(directory.exists())

    def test_manifest_pair_requires_exact_tracked_hash_and_distinct_sensor_source(self):
        pair=plan.manifest_pair(Path(__file__).resolve().parents[2])
        self.assertNotEqual(pair['before']['build']['source_tree_sha256'],pair['after']['build']['source_tree_sha256'])
        self.assertEqual(pair['before']['files']['worker'],pair['after']['files']['worker'])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);name=plan.MANIFESTS['before'][0];p=root/name;p.parent.mkdir(parents=True);p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'manifest_hash_differs'):plan.manifest_pair(root)

    def test_signal_guard_refuses_every_process_without_exact_service_custody(self):
        with patch.object(operator.ops,'command',return_value=b'123'),patch.object(operator,'descendants',return_value=[]),patch.object(operator.signal,'pidfd_send_signal') as send:
            self.assertEqual(operator.pause_collection('w'+'1'*18+'-timeout'),(None,None));send.assert_not_called()

    def test_signal_identity_requires_exact_UID_cgroup_alias_and_readonly_command(self):
        case='w'+'1'*18+'-timeout';helper='/data/resmgrcheck/b-'+'2'*48+'/targetctl'
        uid=pwd.getpwnam('resmgr-exec').pw_uid;group='0::/system.slice/resmgrcheck-executor.service\n'
        argv=[b'ssh',b'-F',os.fsencode(plan.CONFIG/'ssh-config'),b'resmgrcheck-lab',(helper+' read-run '+case+' events.jsonl').encode(),b'']
        self.assertTrue(operator.collection_identity(uid,argv,group,case,helper))
        self.assertFalse(operator.collection_identity(uid+1,argv,group,case,helper))
        self.assertFalse(operator.collection_identity(uid,argv,group.replace('executor','web'),case,helper))
        for command in [helper+' read-run '+case+' events.jsonl; id',helper+' start '+case+' events.jsonl',helper+' read-run different events.jsonl']:
            self.assertFalse(operator.collection_identity(uid,[*argv[:-2],command.encode(),b''],group,case,helper))

    def test_native_queue_buttons_do_not_spend_authentication_rate_capacity(self):
        journey=NativeJourney('https://qnx-resmgrcheck.gestionatech.de',Path('/tmp'),{'native':{}});page=Mock()
        page.url=journey.origin+'/app/projects/approved/runs/new/'
        with patch.object(journey,'pace') as pace:journey.click(page,'Confirm and queue');pace.assert_not_called()
        page.url=journey.origin+'/administrator/codes/approved/'
        with patch.object(journey,'pace') as pace:journey.click(page,'Revoke this code immediately');pace.assert_called_once()

    def test_verified_retry_rechecks_all_private_bytes_before_reusing_native_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);names=['ssh-key','known-hosts','ssh-config','target.json','registry.json','before-deployment.json','after-deployment.json']
            for name in names:(root/name).write_bytes(name.encode());(root/name).chmod(0o600)
            journal={'private_resource_hashes':{name:plan.digest(name.encode()) for name in names}}
            with patch.object(plan,'CONFIG',root):
                driver.verify_private(journal,os.getuid())
                (root/'registry.json').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'verified_private_resource_changed'):driver.verify_private(journal,os.getuid())
            self.assertEqual((root/'registry.json').read_bytes(),b'changed')

    def test_finishing_retained_native_receipt_only_rehearses_idle_executor_and_records(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);journal={'phase':'approved_after_actual_runtime_probe'};baseline={'fixed':'fixture'}
            result={'native_runs':[],'observations':[],'cleanup':{'fixture':True}}
            with patch.object(plan,'STATE',root),patch.object(driver,'helper',return_value={'passed':True}) as helper,patch.object(driver,'own_baseline',return_value=baseline),patch.object(driver,'public_health'),contextlib.redirect_stdout(io.StringIO()):
                driver.finish(DRIVER,{'driver_revision':DRIVER},journal,root/'state.json',baseline,result)
            helper.assert_called_once_with('rehearse',DRIVER)
            self.assertEqual(json.loads((root/'state.json').read_text())['phase'],'verified')
            self.assertEqual(json.loads((root/'report.json').read_text())['application_rollback'],'not_run')

class ApprovedProductionBindingTests(TestCase):
    def setUp(self):
        mocked=patch('executor_locking.install',return_value={'role':'resmgr_exec','columns':['id'],'actual_updates':'denied'})
        mocked.start();self.addCleanup(mocked.stop)
    def prepare(self):operator.prepare()
    def proof(self):
        pair=plan.manifest_pair(Path(__file__).resolve().parents[2])
        from resmgrcheck.contracts import Profile,load
        return {'passed':True,'kind':'actual-systemd-executor-probe','application':plan.APPLICATION,'driver_revision':DRIVER,
            'database_grants_verified':True,'compiled_adapters':{name+'-v1':Profile.parse(load(plan.SOURCE/'profiles'/(name+'.json'))).data['capabilities']['required'] for name in ['sensor','job']},
            'deployments':{role:{'deployment_id':row['deployment_id'],'verified_files':5} for role,row in pair.items()}}
    def publish(self,proof=None):
        with patch.object(operator.ops,'read',return_value=json.dumps(proof or self.proof()).encode()):operator.publish(DRIVER)

    def selected_fixture(self,root):
        self.prepare();self.publish()
        registry=root/'registry.json'
        for name,value in [('registry.json',plan.registry()),('target.json',plan.target_config()),('state.json',{
            'kind':'approved-production-qnx-executor-v1','application':plan.APPLICATION,'ids':plan.IDS,'driver_revision':DRIVER}),('runtime-proof.json',self.proof())]:
            operator.ops.record(root/name,value)
        (root/'ssh-config').write_bytes(plan.ssh_config());(root/'ssh-config').chmod(0o600)
        (root/'known-hosts').write_bytes((plan.SOURCE/'.local/qnx-known-hosts').read_bytes());(root/'known-hosts').chmod(0o600)
        for role,(name,_) in plan.MANIFESTS.items():
            (root/(role+'-deployment.json')).write_bytes((plan.SOURCE/name).read_bytes());(root/(role+'-deployment.json')).chmod(0o600)
        return registry

    def test_root_generic_selector_rejects_executor_owned_registry_but_fixed_selector_accepts(self):
        from types import SimpleNamespace
        import acceptance_operator as generic
        from control.engine import PolicyError,registry as worker_registry
        uid=os.getuid();gid=os.getgid()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(plan,'STATE',root),patch.object(plan,'CONFIG',root):
                registry=self.selected_fixture(root)
                with patch.object(generic,'REGISTRY',registry),patch.object(operator.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=uid,pw_gid=gid)),patch('control.engine.os.getuid',return_value=0):
                    rejected=generic.native_plan();self.assertEqual(rejected.get('candidate_pairs'),0)
                    self.assertEqual(rejected['reason'],'exactly_one_operator_approved_before_after_lab_pair_required')
                    BuildRelease.objects.filter(pk__in=[plan.IDS['before'],plan.IDS['after']]).update(label='Human display label only')
                    selected=operator.approved_plan();self.assertEqual(selected['target_id'],plan.IDS['target'])
                    self.assertEqual(selected['before_build'],plan.IDS['before']);self.assertEqual(selected['after_build'],plan.IDS['after'])
                    # The generic worker rule remains strict under an unrelated UID.
                    from django.test import override_settings
                    with override_settings(EXECUTOR_REGISTRY=str(registry)),self.assertRaisesRegex(PolicyError,'executor_registry_permissions'):
                        worker_registry(Target.objects.get(pk=plan.IDS['target']))

    def test_fixed_selector_rejects_cross_tenant_insecure_or_changed_registry(self):
        from types import SimpleNamespace
        uid=os.getuid();gid=os.getgid()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(plan,'STATE',root),patch.object(plan,'CONFIG',root):
                registry=self.selected_fixture(root);original=registry.read_bytes()
                with patch.object(operator.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=uid,pw_gid=gid)):
                    registry.chmod(0o644)
                    with self.assertRaisesRegex(ValueError,'resource_protection'):operator.approved_plan()
                    registry.chmod(0o600);changed=json.loads(original);changed['targets'][plan.IDS['target']]['project_id']=str(uuid.uuid4());registry.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError,'approved_registry_binding_differs'):operator.approved_plan()
                    registry.write_bytes(original)
                    with patch.object(operator.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=uid+1,pw_gid=gid)),self.assertRaisesRegex(ValueError,'resource_protection'):operator.approved_plan()
                    (root/'before-deployment.json').write_text('{}')
                    with self.assertRaisesRegex(ValueError,'approved_manifest_identity_differs'):operator.approved_plan()

    def test_prepare_is_additive_disabled_and_idempotent_then_exact_probe_publishes(self):
        from .helpers import tenant
        existing,org,project=tenant('Unrelated preserved organization','preserved-executor@example.test');original=User.objects.values().get(pk=existing.pk)
        self.prepare();self.prepare();target=Target.objects.get(pk=plan.IDS['target'])
        self.assertFalse(target.approved);self.assertEqual(target.state,'unknown')
        custodian=User.objects.get(pk=plan.IDS['custodian']);self.assertFalse(custodian.is_active);self.assertFalse(custodian.has_usable_password())
        self.assertEqual(BuildRelease.objects.filter(target=target).count(),2)
        self.publish();self.publish();target.refresh_from_db();self.assertTrue(target.approved);self.assertEqual(target.binding,str(target.pk))
        self.assertEqual(target.state,'available');self.assertEqual(AuditEvent.objects.filter(action='production.executor.approved').count(),1)
        self.assertEqual(User.objects.values().get(pk=existing.pk),original);self.assertEqual(project.organization_id,org.pk)
        self.assertFalse(custodian.membership_set.exists())

    def test_identifier_occupation_and_changed_tenant_binding_are_refused(self):
        self.prepare();Target.objects.filter(pk=plan.IDS['target']).update(binding='unknown')
        with self.assertRaisesRegex(ValueError,'target_approval_changed'):self.prepare()
        Target.objects.filter(pk=plan.IDS['target']).update(binding='')
        project=Project.objects.get(pk=plan.IDS['project']);other=Organization.objects.create(name='Unrelated')
        project.organization=other;project.save(update_fields=['organization'])
        with self.assertRaisesRegex(ValueError,'approved_project_changed'):self.prepare()

    def test_changed_manifest_and_revoked_or_quarantined_approval_never_repaired(self):
        self.prepare();self.publish()
        build=BuildRelease.objects.get(pk=plan.IDS['before']);original=build.manifest;build.manifest={};build.save(update_fields=['manifest'])
        with self.assertRaisesRegex(ValueError,'approved_build_changed'):operator.check_bindings()
        build.manifest=original;build.save(update_fields=['manifest'])
        Target.objects.filter(pk=plan.IDS['target']).update(approved=False)
        with self.assertRaisesRegex(ValueError,'target_approval_changed'):self.publish()
        Target.objects.filter(pk=plan.IDS['target']).update(approved=True,state='quarantined')
        with self.assertRaisesRegex(ValueError,'approved_target_changed'):self.publish()

    def test_publication_requires_matching_actual_runtime_receipt(self):
        self.prepare()
        for altered in [{'passed':False},{'driver_revision':'7'*40},{'application':'8'*40},{'database_grants_verified':False}]:
            proof={**self.proof(),**altered}
            with self.assertRaisesRegex(ValueError,'runtime_probe_required'):self.publish(proof)
        with self.assertRaisesRegex(ValueError,'required_capabilities_missing'):self.publish({**self.proof(),'compiled_adapters':{}})
        self.assertFalse(Target.objects.get(pk=plan.IDS['target']).approved)

    def test_no_runtime_provisioner_can_adopt_an_unrelated_native_run(self):
        from .helpers import tenant
        actor,_,project=tenant('Different tenant','different-executor@example.test')
        target=Target.objects.create(project=project,name='Other lab');run=Run.objects.create(project=project,target=target,actor=actor,
            actor_auth_hash='0'*64,mfa_at=timezone.now(),operation='run',native_run_id='w'+'0'*18,idempotency_key='fixture'+'0'*16,intent_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'run_not_owned_by_acceptance'):
            operator.qualified_run(str(run.pk),{'account_id':str(actor.pk)})

    def test_guarded_rehearsal_is_idle_only_and_never_stops_web_or_database(self):
        self.prepare();self.publish()
        with patch.object(operator.ops,'command',side_effect=[b'',b'',b'active']) as command:
            result=operator.rehearse()
        self.assertTrue(result['passed'])
        self.assertEqual([call.args[0][:2] for call in command.call_args_list],[['systemctl','stop'],['systemctl','start'],['systemctl','show']])
        self.assertTrue(all('resmgrcheck-executor.service' in call.args[0] for call in command.call_args_list))
        with patch.object(operator,'idle',side_effect=ValueError('existing_work_requires_reconciliation')),patch.object(operator.ops,'command') as command:
            with self.assertRaisesRegex(ValueError,'existing_work_requires_reconciliation'):operator.rehearse()
            command.assert_not_called()

class LockOnlyDatabasePrivilegeTests(TestCase):
    def test_real_nonprivileged_role_can_lock_but_cannot_mutate_authorization_rows(self):
        from django.db import connection,transaction,DatabaseError
        from control.models import AccessCode
        from executor_locking import install
        role='exec_lock_'+uuid.uuid4().hex[:12];prefix='guard_'+uuid.uuid4().hex[:12]
        quote=connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('CREATE ROLE '+quote(role)+' NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
            cursor.execute('GRANT USAGE ON SCHEMA public TO '+quote(role))
            cursor.execute('GRANT SELECT ON public.control_user,public.control_accesscode TO '+quote(role))
        owner=User.objects.create_user('lock-only-fixture',None,is_active=False)
        org=Organization.objects.create(name='Lock-only disposable qualification')
        code=AccessCode.objects.create(organization=org,created_by=owner,description='fixture',verifier='0'*64)
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+quote(role))
            try:
                with self.assertRaises(DatabaseError),transaction.atomic():
                    cursor.execute('SELECT id FROM public.control_user WHERE id=%s FOR UPDATE',[owner.pk])
            finally:cursor.execute('RESET ROLE')
        install(connection,role,prefix);install(connection,role,prefix)
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as queries:install(connection,role,prefix,check_only=True)
        self.assertFalse(any(row['sql'].lstrip().split()[0].upper() in {'GRANT','CREATE','ALTER','INSERT','UPDATE','DELETE'} for row in queries))
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+quote(role))
            try:
                for table,identifier in [('control_user',owner.pk),('control_accesscode',code.pk)]:
                    cursor.execute('SELECT id FROM public.'+table+' WHERE id=%s FOR UPDATE',[identifier]);self.assertEqual(cursor.fetchone()[0],identifier)
                    with self.assertRaisesRegex(DatabaseError,'executor_authorization_update_forbidden'),transaction.atomic():
                        cursor.execute('UPDATE public.'+table+' SET id=id WHERE id=%s',[identifier])
                with self.assertRaises(DatabaseError),transaction.atomic():cursor.execute("UPDATE public.control_user SET is_superuser=true WHERE id=%s",[owner.pk])
                with self.assertRaises(DatabaseError),transaction.atomic():cursor.execute('ALTER TABLE public.control_user DISABLE TRIGGER '+quote(prefix+'_0'))
            finally:cursor.execute('RESET ROLE')
            # Existing owner/web authorization writes are not made append-only.
            cursor.execute('UPDATE public.control_accesscode SET description=%s WHERE id=%s',['owner edit remains allowed',code.pk])
        owner.refresh_from_db();code.refresh_from_db();self.assertFalse(owner.is_superuser);self.assertFalse(owner.is_active)
        self.assertEqual(code.description,'owner edit remains allowed')

    def test_unknown_guard_or_unprotected_existing_grants_are_refused(self):
        from django.db import connection,transaction
        from executor_locking import install
        role='exec_lock_'+uuid.uuid4().hex[:12];prefix='guard_'+uuid.uuid4().hex[:12];quote=connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('CREATE ROLE '+quote(role)+' NOLOGIN')
            cursor.execute('GRANT SELECT,UPDATE(id) ON public.control_user TO '+quote(role))
        with self.assertRaisesRegex(ValueError,'unprotected_existing_authorization_grant'),transaction.atomic():install(connection,role,prefix)
        with connection.cursor() as cursor:
            cursor.execute('REVOKE UPDATE(id) ON public.control_user FROM '+quote(role))
            cursor.execute('CREATE FUNCTION public.'+quote(prefix+'_guard')+"() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END;$$")
        with self.assertRaisesRegex(ValueError,'existing_lock_guard_differs'),transaction.atomic():install(connection,role,prefix)
