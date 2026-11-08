"""Third immutable upgrade fixtures; never reads real snapshots or deploys as root."""
import contextlib,importlib.util,io,json,os,sys
from pathlib import Path
import unittest
from unittest.mock import patch
from . import test_socket_release as baseline


class RestoreReleaseTests(unittest.TestCase):
    git=baseline.SocketReleaseTests.git

    def setUp(self):
        baseline.SocketReleaseTests.setUp(self);self.socket=self.m;self.credential=self.socket.release
        ops=Path(__file__).resolve().parents[1]/'ops/production'
        source=self.p.SOURCE
        (source/'web/control/management/commands').mkdir(parents=True,exist_ok=True)
        (source/'web/control/backup.py').write_text('# original verifier\n')
        (source/'web/control/management/commands/backup_snapshot.py').write_text('# original command\n')
        service=(ops/'resmgrcheck-backup.service').read_bytes()
        (source/'web/ops/production/resmgrcheck-backup.service').write_bytes(service)
        self.git('-C',str(source),'add','.');self.git('-C',str(source),'commit','-m','active socket fixed release')
        active=self.git('-C',str(source),'rev-parse','HEAD').strip();self.previous=self.p.OPT/'releases'/active
        self.p.write(self.p.BASE/'SOCKET_RELEASE.json',json.dumps(self.socket.identity(active))+'\n')
        self.socket.stage(active,self.previous);self.credential.switch_current(self.p.OPT/'current',self.previous)
        self.unit.write_bytes(self.target);self.p.write(self.p.UNIT_ROOT/'resmgrcheck-backup.service',service)
        path=ops/'recover_restore_drill.py';spec=importlib.util.spec_from_file_location('restore_release_fixture',path)
        self.m=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'recover_socket_activation':self.socket}):spec.loader.exec_module(self.m)
        self.m.ACTIVE=active
        (source/'web/control/backup.py').write_text('# corrected verifier\n')
        (source/'web/control/management/commands/backup_snapshot.py').write_text('# inspect command\n')
        (source/'web/ops/production/recover_restore_drill.py').write_text('# immutable restore release fixture\n')
        self.git('-C',str(source),'add','.');self.git('-C',str(source),'commit','-m','restore verifier correction')
        self.revision=self.git('-C',str(source),'rev-parse','HEAD').strip();self.new_path=self.p.OPT/'releases'/self.revision
        (self.root/'backups').mkdir(mode=0o700);self.archive=self.root/'backups/snapshot.rmc';self.archive.write_bytes(b'preserved encrypted fixture');self.archive.chmod(0o600)
        paths=[self.archive,self.p.BASE/'PROVISIONED.json',self.p.BASE/'CREDENTIAL_RELEASE.json',self.p.BASE/'SOCKET_RELEASE.json',
            self.p.BASE/'database/audit',*list((self.p.CONFIG/'keys').iterdir()),*list(self.p.UNIT_ROOT.iterdir()),
            self.old_path/'.git/index',self.previous/'.git/index',self.previous/'web/control/backup.py']
        self.protected={path:(path.read_bytes(),path.stat().st_mode,path.stat().st_mtime_ns) for path in paths}

    def apply(self,rollback=False):
        with patch.object(self.credential,'require_root'),contextlib.redirect_stdout(io.StringIO()):self.m.apply(self.revision,rollback)

    def preserved(self):
        self.assertEqual(self.protected,{path:(path.read_bytes(),path.stat().st_mode,path.stat().st_mtime_ns) for path in self.protected})
        self.assertTrue(all(args[1]=='show' for args in self.calls if args[0]=='systemctl'))

    def test_activation_and_repeat_leave_snapshots_keys_data_records_and_units_untouched(self):
        read=Path.read_bytes
        def no_private_reads(path):
            if path==self.archive or path.parent==self.p.CONFIG/'keys' or path==self.p.BASE/'database/audit':raise AssertionError('No snapshot/key/DB reads')
            return read(path)
        with patch.object(Path,'read_bytes',no_private_reads):self.apply();self.apply()
        self.assertEqual((self.p.OPT/'current').resolve(),self.new_path)
        self.assertEqual(os.readlink(self.new_path/'.venv'),self.m.identity(self.revision)['venv']);self.preserved()

    def test_resume_before_and_after_pointer_switch(self):
        with patch.object(self.credential,'switch_current',side_effect=RuntimeError('before switch')):
            with self.assertRaisesRegex(RuntimeError,'before switch'):self.apply()
        self.assertEqual((self.p.OPT/'current').resolve(),self.previous)
        original=self.credential.switch_current
        def after(*args):original(*args);raise RuntimeError('after switch')
        with patch.object(self.credential,'switch_current',side_effect=after):
            with self.assertRaisesRegex(RuntimeError,'after switch'):self.apply()
        self.apply();self.preserved()

    def test_partial_clone_is_retained_when_retry_uses_new_attempt(self):
        partial=[]
        def fail(path,revision):
            path.mkdir(mode=0o700);(path/'partial').write_text('preserve');partial.append(path);raise RuntimeError('partial clone')
        with patch.object(self.p,'clone',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'partial clone'):self.apply()
        self.apply();self.assertEqual((partial[0]/'partial').read_text(),'preserve');self.preserved()

    def test_pointer_rollback_preserves_all_releases_and_backup(self):
        self.apply();self.apply(rollback=True)
        self.assertEqual((self.p.OPT/'current').resolve(),self.previous);self.assertTrue(self.new_path.exists())
        self.apply();self.preserved()

    def test_unknown_release_is_not_adopted_or_permission_repaired(self):
        self.new_path.mkdir(mode=0o755);unknown=self.new_path/'private';unknown.write_text('keep');unknown.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'no manifest'):self.apply()
        self.assertEqual(unknown.read_text(),'keep');self.assertEqual(unknown.stat().st_mode&0o777,0o600);self.preserved()

    def test_audit_schema_changes_are_rejected_before_staging(self):
        path=self.p.SOURCE/'web/control/migrations/0003_audit_append_only.py';path.parent.mkdir(exist_ok=True);path.write_text('# forbidden schema change')
        self.git('-C',str(self.p.SOURCE),'add','.');self.git('-C',str(self.p.SOURCE),'commit','-m','unexpected schema change')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        with self.assertRaisesRegex(RuntimeError,'Changes exceed restore verification'):self.apply()
        self.assertFalse((self.p.BASE/'RESTORE_RELEASE.json').exists());self.preserved()

    def test_unknown_backup_unit_is_not_overwritten(self):
        path=self.p.UNIT_ROOT/'resmgrcheck-backup.service';path.write_bytes(b'unknown backup unit')
        self.protected[path]=(path.read_bytes(),path.stat().st_mode,path.stat().st_mtime_ns)
        with self.assertRaisesRegex(RuntimeError,'Unknown installed web unit'):self.apply()
        self.assertFalse(self.new_path.exists());self.preserved()

    def test_modified_completed_release_is_not_reused(self):
        self.apply();path=self.new_path/'web/control/backup.py';path.write_text('# unknown change')
        with self.assertRaisesRegex(RuntimeError,'tracked changes'):self.apply()
        self.assertEqual(path.read_text(),'# unknown change');self.preserved()

    def test_other_record_and_active_unit_or_operator_lock_block_upgrade(self):
        prior=self.p.run
        with patch.object(self.p,'run',side_effect=lambda args,**kw:b'active\n' if args[0]=='systemctl' else prior(args,**kw)):
            with self.assertRaisesRegex(RuntimeError,'must be inactive'):self.apply()
        with self.credential.release_lock():
            with self.assertRaises(BlockingIOError):self.apply()
        self.assertFalse(self.new_path.exists());self.preserved()

    def test_nonroot_cannot_apply(self):
        with patch.object(self.m.os,'geteuid',return_value=1000):
            with self.assertRaises(SystemExit):self.m.apply(self.revision)
        self.assertFalse(self.new_path.exists());self.preserved()
