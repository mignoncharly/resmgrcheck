"""Disposable real Git/FS, modeled root/units/schema. Never production deployment."""
import contextlib,hashlib,importlib.util,io,json,os,sys,time
from pathlib import Path
from unittest.mock import patch
import unittest
from . import test_restore_release as baseline

class PrivateUpgradeTests(unittest.TestCase):
    git=baseline.RestoreReleaseTests.git
    def setUp(self):
        baseline.RestoreReleaseTests.setUp(self)
        self.restore=self.m;active=self.revision
        with patch.object(self.credential,'require_root'),contextlib.redirect_stdout(io.StringIO()):self.restore.apply(active)
        self.previous=self.p.OPT/'releases'/active
        spec=importlib.util.spec_from_file_location('private_upgrade_fixture',Path(__file__).resolve().parents[1]/'ops/production/upgrade_private.py')
        self.m=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'recover_restore_drill':self.restore}):spec.loader.exec_module(self.m)
        self.m.ACTIVE=active;self.m.UNIT_NAMES=['resmgrcheck-web.service','resmgrcheck-web.socket','resmgrcheck-backup.service']
        for name in ['web/ops/production/upgrade_private.py','web/control/management/commands/private_release.py','web/ops/production/runner-grants.sql']:
            path=self.p.SOURCE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('# private fixture\n')
        self.git('-C',str(self.p.SOURCE),'add','.');self.git('-C',str(self.p.SOURCE),'commit','-m','private web fixture')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip();self.new_path=self.p.OPT/'releases'/self.revision
        self.p.BACKUP=self.root/'backups';self.p.write(self.p.CONFIG/'operator.json','{}\n')
        self.runtime=[]
        def runtime(new,operation,revision):self.runtime.append(operation)
        mock=patch.object(self.m,'runtime',side_effect=runtime);mock.start();self.addCleanup(mock.stop)
        self.verify_backup_function=self.m.verify_backup
        mock=patch.object(self.m,'verify_backup');self.backup_check=mock.start();self.addCleanup(mock.stop)
        self.protected.update({path:(path.read_bytes(),path.stat().st_mode,path.stat().st_mtime_ns) for path in [
            self.p.BASE/'RESTORE_RELEASE.json',self.previous/'.git/index',self.p.CONFIG/'operator.json']})

    def apply(self,operation='stage',archive=None):
        with patch.object(self.credential,'require_root'),contextlib.redirect_stdout(io.StringIO()):self.m.apply(self.revision,operation,archive)

    def snapshot(self):
        path=self.p.BACKUP/'snapshot_20261109T000000Z.rmc';path.write_bytes(b'new encrypted fixture');path.chmod(0o600)
        self.p.write(Path(str(path)+'.receipt.json'),json.dumps({'passed':True,'qnx_contacted':False,'encrypted_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})+'\n')
        return str(path)

    def preserved(self):baseline.RestoreReleaseTests.preserved(self)

    def test_stage_prepare_activate_retry_and_data_preserving_rollback(self):
        self.apply();self.assertEqual((self.p.OPT/'current').resolve(),self.previous);archive=self.snapshot()
        self.apply('prepare',archive);self.apply('activate');self.apply('activate');self.apply('rollback')
        self.assertEqual((self.p.OPT/'current').resolve(),self.previous)
        self.assertEqual(self.runtime,['prepare','check','check','rollback-check']);self.assertTrue(self.new_path.exists());self.preserved()
        self.assertEqual(self.backup_check.call_count,1)

    def test_partial_clone_and_switch_interruption_resume_exact_release(self):
        partial=[]
        def fail(path,revision):path.mkdir(mode=0o700);(path/'keep').write_text('partial');partial.append(path);raise RuntimeError('interrupted')
        with patch.object(self.p,'clone',side_effect=fail),self.assertRaisesRegex(RuntimeError,'interrupted'):self.apply()
        self.apply();self.assertEqual((partial[0]/'keep').read_text(),'partial');self.apply('prepare',self.snapshot())
        switch=self.credential.switch_current
        def after(*args):switch(*args);raise RuntimeError('after switch')
        with patch.object(self.credential,'switch_current',side_effect=after),self.assertRaisesRegex(RuntimeError,'after switch'):self.apply('activate')
        self.apply('activate');self.assertEqual((self.p.OPT/'current').resolve(),self.new_path);self.preserved()

    def test_unknown_release_and_partial_records_are_never_adopted(self):
        self.new_path.mkdir(mode=0o755);self.new_path.chmod(0o755);unknown=self.new_path/'private';unknown.write_text('keep');unknown.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'no private completion'):self.apply()
        self.assertEqual(unknown.read_text(),'keep');self.assertEqual(unknown.stat().st_mode&0o777,0o600);self.preserved()

    def test_schema_failure_does_not_switch_and_bound_backup_can_resume_days_later(self):
        self.apply();archive=self.snapshot()
        with patch.object(self.m,'runtime',side_effect=RuntimeError('migration failed')),self.assertRaisesRegex(RuntimeError,'migration failed'):self.apply('prepare',archive)
        self.assertFalse((self.p.BASE/'PRIVATE_WEB_PREPARED.json').exists());self.assertEqual((self.p.OPT/'current').resolve(),self.previous)
        with patch.object(self.m.time,'time',return_value=time.time()+172800):self.apply('prepare',archive)
        self.assertEqual((self.p.OPT/'current').resolve(),self.previous);self.preserved()

    def test_incompatible_schema_or_data_gate_prevents_activation_and_rollback(self):
        self.apply();self.apply('prepare',self.snapshot())
        with patch.object(self.m,'runtime',side_effect=RuntimeError('gate denied')):
            for operation in ['activate','rollback']:
                with self.assertRaisesRegex(RuntimeError,'gate denied'):self.apply(operation)
        self.assertEqual((self.p.OPT/'current').resolve(),self.previous);self.preserved()

    def test_failed_isolated_restore_prevents_schema_preparation(self):
        self.apply();archive=self.snapshot()
        self.backup_check.side_effect=RuntimeError('restore failed')
        with self.assertRaisesRegex(RuntimeError,'restore failed'):self.apply('prepare',archive)
        self.assertEqual(self.runtime,[]);self.assertFalse((self.p.BASE/'PRIVATE_WEB_PREPARED.json').exists())
        self.assertFalse((self.p.BASE/'PRIVATE_WEB_BACKUP_VERIFIED.json').exists());self.preserved()

    def test_backup_gate_requires_actual_audit_behavior_and_exact_archive_hash(self):
        binding={'archive':'/not-opened/snapshot.rmc','encrypted_sha256':'a'*64}
        flags=['passed','audit_behavior_tested','audit_update_denied','audit_delete_denied','audit_probe_rolled_back',
            'database_identity_matches','temporary_database_removed_on_exit','original_database_preserved']
        value={**{key:True for key in flags},'encrypted_sha256':'a'*64,'diagnostic_only':False,'qnx_contacted':False}
        # The fixture patches the root restore operation globally; call its original
        # implementation with a structured subprocess reply, never a real archive.
        with patch.object(self.p,'run',return_value=json.dumps(value).encode()):self.verify_backup_function(self.new_path,binding)
        for field in flags+['encrypted_sha256']:
            changed={**value,field:False}
            with patch.object(self.p,'run',return_value=json.dumps(changed).encode()),self.assertRaisesRegex(RuntimeError,'restore did not pass'):
                self.verify_backup_function(self.new_path,binding)

    def test_missing_stale_wrong_hash_or_symlink_backup_prevents_prepare(self):
        self.apply()
        with self.assertRaises(RuntimeError):self.apply('prepare')
        archive=self.snapshot();path=Path(archive)
        with patch.object(self.m.time,'time',return_value=time.time()+172800),self.assertRaisesRegex(RuntimeError,'fresh completed'):self.apply('prepare',archive)
        path.write_bytes(b'tampered')
        with self.assertRaisesRegex(RuntimeError,'receipt hash'):self.apply('prepare',archive)
        path.unlink();path.symlink_to(self.archive)
        with self.assertRaises(RuntimeError):self.apply('prepare',archive)
        self.assertEqual(self.runtime,[]);self.preserved()

    def test_unprepared_activation_and_unknown_unit_or_old_migration_changes_are_refused(self):
        self.apply()
        with self.assertRaises(FileNotFoundError):self.apply('activate')
        path=self.p.SOURCE/'web/control/migrations/0003_audit_append_only.py';path.parent.mkdir(exist_ok=True);path.write_text('# changed audit')
        self.git('-C',str(self.p.SOURCE),'add','.');self.git('-C',str(self.p.SOURCE),'commit','-m','forbidden audit change')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        with self.assertRaisesRegex(RuntimeError,'Historical schema'):self.apply()
        self.preserved()

    def test_active_units_and_exclusive_lock_and_nonroot_block_apply(self):
        run=self.p.run
        with patch.object(self.p,'run',side_effect=lambda args,**kw:b'active\n' if args[0]=='systemctl' else run(args,**kw)),self.assertRaisesRegex(RuntimeError,'must be inactive'):self.apply()
        with self.credential.release_lock(),self.assertRaises(BlockingIOError):self.apply()
        with patch.object(self.m.os,'geteuid',return_value=1000),self.assertRaises(SystemExit):self.m.apply(self.revision,'stage')
        self.assertFalse(self.new_path.exists());self.preserved()
