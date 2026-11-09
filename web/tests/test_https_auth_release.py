"""Disposable pointer/receipt recovery; privileged services, backup and HTTP modeled."""
import contextlib,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import recover_https_auth as auth
from https_checks import CheckFailed
REVISION='5'*40;DRIVER='6'*40

class AuthReleaseTests(unittest.TestCase):
    def setUp(self):
        previous_umask=os.umask(0o022);self.addCleanup(os.umask,previous_umask)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.opt=self.root/'opt';(self.opt/'releases').mkdir(parents=True)
        self.old=self.opt/'releases'/auth.ACTIVE;self.old.mkdir();self.new=self.opt/'releases'/REVISION
        (self.opt/'current').symlink_to(self.old);self.state=self.root/'state';self.state.mkdir(mode=0o700)
        units=self.root/'units';units.mkdir();(self.old/'web/ops/production').mkdir(parents=True)
        for name in auth.p.UNITS:
            (units/name).write_bytes(b'Preserve canonical unit\n');(units/name).chmod(0o644)
            (self.old/'web/ops/production'/name).write_bytes(b'Preserve canonical unit\n')
        keys=self.root/'config/keys';keys.mkdir(parents=True)
        for name in ['application-key','mfa-key','backup-key']:(keys/name).write_bytes(b'Preserve existing value');(keys/name).chmod(0o600)
        self.original_keys={p:p.read_bytes() for p in keys.iterdir()}
        for module,name,value in [(auth.p,'OPT',self.opt),(auth.p,'UNIT_ROOT',units),(auth.p,'CONFIG',keys.parent),(auth.https,'OPT',self.opt),(auth.https,'STATE',self.state)]:
            self.stack.enter_context(patch.object(module,name,value))
        self.stack.enter_context(patch.object(auth.https,'require_root'));self.stack.enter_context(patch.object(auth,'scope'))
        self.stack.enter_context(patch.object(auth.release,'release_lock',side_effect=contextlib.nullcontext))
        self.stack.enter_context(patch.object(auth.previous,'validate'))
        self.original=self.stack.enter_context(patch.object(auth,'original_http'))
        self.ready=self.stack.enter_context(patch.object(auth,'private_ready'))
        self.runtime=self.stack.enter_context(patch.object(auth.https,'units_and_runtime',return_value={'nonroot_isolation':'passed'}))
        self.backup=self.stack.enter_context(patch.object(auth,'snapshot'))
        self.calls=[]
        def command(argv,**kwargs):
            self.calls.append(list(map(str,argv)))
            if 'ActiveState' in argv:return b'inactive'
            if '--property=ActiveState' in argv:return b'inactive'
            if '--property=DropInPaths' in argv:return b''
            return b'{"passed":true}'
        self.command=self.stack.enter_context(patch.object(auth.https,'command',side_effect=command))
        def stage(revision,path):path.mkdir(exist_ok=True)
        self.staging=self.stack.enter_context(patch.object(auth,'stage',side_effect=stage))
        self.stack.enter_context(patch.object(auth,'validate'))
        self.old_state={'kind':'resmgrcheck-https-deployment','application_revision':auth.ACTIVE,'driver_revision':auth.FAILED_DRIVER,
            'phase':'rolled_back_after_failure','failure':'command_failed_python','renewal_verified_certificate':'same-certificate',
            'rollback_verified':True,'after':{'previous':'payload'},'before':{'site':'original-backup-hash'}}
        auth.https.record(self.state/'state.json',self.old_state)
        self.stack.enter_context(patch.object(auth.https,'recorded_candidate_hashes',return_value=self.old_state['after']))
        def deploy(revision,driver,rollback=False,acceptance=True):
            state=json.loads((self.state/'state.json').read_text());state['phase']='rolled_back' if rollback else 'verified';auth.https.record(self.state/'state.json',state)
        self.deploy=self.stack.enter_context(patch.object(auth.https,'apply',side_effect=deploy))
    def apply(self,rollback=False):
        with contextlib.redirect_stdout(io.StringIO()):auth.apply(REVISION,DRIVER,rollback)
    def journal(self):return json.loads((self.state/'auth-upgrade.json').read_text())
    def preserved(self):
        for path,raw in self.original_keys.items():self.assertEqual(path.read_bytes(),raw)
        self.assertTrue(self.old.is_dir())
        self.assertTrue(all(call[0]=='systemctl' or call[0].endswith('/.venv/bin/python') for call in self.calls))
        for call in self.calls:
            if call[:2] in [['systemctl','start'],['systemctl','stop']]:self.assertEqual(call[2:],['resmgrcheck-web.socket','resmgrcheck-web.service'])
    def test_upgrade_retains_history_and_renewal_proof_and_requires_new_private_checks(self):
        self.apply();self.assertEqual((self.opt/'current').resolve(),self.new)
        saved=json.loads((self.state/('driver-'+auth.FAILED_DRIVER+'.json')).read_text())
        self.assertEqual(saved['application_revision'],auth.ACTIVE);self.assertTrue(saved['rollback_verified'])
        new=json.loads((self.state/'state.json').read_text());self.assertEqual(new['renewal_verified_certificate'],'same-certificate');self.assertFalse(new['rollback_verified'])
        self.assertEqual(self.journal()['phase'],'HTTPS_browser_workflow_completed');self.runtime.assert_called_once_with(REVISION)
        self.backup.assert_called_once();self.ready.assert_called_once();self.preserved()
    def test_completed_retry_reuses_release_without_restarting_private_service(self):
        self.apply();self.calls.clear();self.apply()
        self.assertFalse(any(call[:2] in [['systemctl','start'],['systemctl','stop']] for call in self.calls));self.preserved()
    def test_private_runtime_failure_restores_original_pointer_and_health(self):
        original=self.command.side_effect
        def failed(argv,**kwargs):
            if str(argv[0]).endswith('/.venv/bin/python'):raise CheckFailed('fixture_runtime_failure')
            return original(argv,**kwargs)
        self.command.side_effect=failed
        with self.assertRaisesRegex(CheckFailed,'original_private_restored'):self.apply()
        self.assertEqual((self.opt/'current').resolve(),self.old);self.assertTrue(self.new.is_dir())
        self.assertEqual(self.journal()['phase'],'failed_original_private_restored');self.runtime.assert_called_once_with(auth.ACTIVE);self.preserved()
    def test_browser_failure_restores_original_private_and_resumes_same_immutable_release(self):
        self.deploy.side_effect=CheckFailed('fixture_browser_failure')
        with self.assertRaisesRegex(CheckFailed,'original_private_restored'):self.apply()
        self.assertEqual((self.opt/'current').resolve(),self.old)
        self.deploy.side_effect=None;self.apply();self.assertEqual((self.opt/'current').resolve(),self.new);self.preserved()
    def test_interrupted_new_pointer_resumes_without_touching_old_release(self):
        self.new.mkdir();auth.release.switch_current(self.opt/'current',self.new)
        auth.https.record(self.state/'auth-upgrade.json',{**auth.identity(REVISION),'driver_revision':DRIVER,'phase':'private_pointer_switched'})
        self.apply();self.assertEqual((self.opt/'current').resolve(),self.new);self.preserved()
    def test_unknown_current_or_unit_is_not_overwritten(self):
        unknown=self.opt/'releases/unknown';unknown.mkdir();auth.release.switch_current(self.opt/'current',unknown)
        with self.assertRaises(RuntimeError):self.apply()
        self.assertEqual((self.opt/'current').resolve(),unknown);self.assertEqual(self.calls,[]);self.preserved()
    def test_changed_canonical_unit_is_refused_before_service_mutation(self):
        path=auth.p.UNIT_ROOT/auth.p.UNITS[0];path.write_bytes(b'Unknown unit edit')
        with self.assertRaisesRegex(CheckFailed,'installed_unit_differs'):self.apply()
        self.assertEqual(path.read_bytes(),b'Unknown unit edit');self.assertEqual((self.opt/'current').resolve(),self.old);self.preserved()
    def test_unknown_https_record_or_changed_old_payload_is_not_adopted(self):
        state=self.old_state.copy();state['after']={'unreviewed':'payload'};auth.https.record(self.state/'state.json',state)
        with self.assertRaisesRegex(CheckFailed,'original_private_restored'):self.apply()
        self.assertEqual(json.loads((self.state/'state.json').read_text()),state);self.assertEqual((self.opt/'current').resolve(),self.old);self.preserved()
    def test_explicit_rollback_retains_new_release_and_restores_original_service(self):
        self.apply();self.apply(True)
        self.assertEqual((self.opt/'current').resolve(),self.old);self.assertTrue(self.new.is_dir());self.assertEqual(self.journal()['phase'],'rolled_back');self.preserved()
    def test_unknown_original_routing_prevents_pointer_mutation(self):
        self.original.side_effect=CheckFailed('fixture_unknown_original')
        with self.assertRaisesRegex(CheckFailed,'fixture_unknown_original'):self.apply()
        self.assertEqual((self.opt/'current').resolve(),self.old);self.assertFalse(any(call[:2]==['systemctl','stop'] for call in self.calls));self.preserved()

class AuthScopeTests(unittest.TestCase):
    def test_only_exact_production_setting_insertion_is_allowed(self):
        old=b'prefix\n'+auth.ANCHOR+b'suffix\n';correct=old.replace(auth.ANCHOR,auth.ANCHOR+auth.SETTING)
        for candidate,allowed in [(correct,True),(correct+b'UNREVIEWED=True\n',False)]:
            with patch.object(auth.https,'source_check'),patch.object(auth.https,'git',side_effect=[b'',b'web/resmgr_web/settings.py\n',b'',old,candidate]):
                if allowed:auth.scope(REVISION,DRIVER)
                else:
                    with self.assertRaisesRegex(CheckFailed,'settings_differs'):auth.scope(REVISION,DRIVER)
    def test_scope_rejects_native_changes_and_runtime_unit_changes(self):
        for replies,code in [([b'',b'native/core.c\n'],'scope_exceeded'),([b'',b'web/resmgr_web/settings.py\n',b'web/ops/production/resmgrcheck-web.service\n'],'runtime_or_units_changed')]:
            with patch.object(auth.https,'source_check'),patch.object(auth.https,'git',side_effect=replies),self.assertRaisesRegex(CheckFailed,code):auth.scope(REVISION,DRIVER)
    def test_stage_never_overwrites_unknown_existing_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);sentinel=root/'unrelated';sentinel.write_bytes(b'preserve unknown bytes')
            with self.assertRaises((FileNotFoundError,CheckFailed,RuntimeError)):auth.stage(REVISION,root)
            self.assertEqual(sentinel.read_bytes(),b'preserve unknown bytes')

class SnapshotRecoveryTests(unittest.TestCase):
    def test_verified_snapshot_is_hash_checked_and_not_repeated(self):
        journal={'backup_verified':True,'backup':{'archive':'/fixture/archive','encrypted_sha256':'expected'}}
        with patch.object(auth.previous,'backup_binding',return_value=journal['backup']) as checked,patch.object(auth.previous,'verify_backup') as restore,patch.object(auth.https,'command') as command:
            auth.snapshot(journal,Path('/fixture/receipt'),Path('/fixture/new'))
        checked.assert_called_once();restore.assert_not_called();command.assert_not_called()
    def test_changed_verified_snapshot_is_refused(self):
        journal={'backup_verified':True,'backup':{'archive':'/fixture/archive','encrypted_sha256':'expected'}}
        with patch.object(auth.previous,'backup_binding',return_value={}),self.assertRaisesRegex(CheckFailed,'backup_binding_differs'):auth.snapshot(journal,Path('/fixture/receipt'),Path('/fixture/new'))
