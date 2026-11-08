"""Disposable Git/UID fixtures for the second immutable private upgrade, never root."""
import contextlib,importlib.util,io,os,sys
from pathlib import Path
import unittest
from unittest.mock import patch
from . import test_credential_release as baseline


class SocketReleaseTests(unittest.TestCase):
    git=baseline.CredentialReleaseTests.git

    def setUp(self):
        baseline.CredentialReleaseTests.setUp(self)
        self.credential=self.m
        service='web/ops/production/resmgrcheck-web.service'
        source_unit=self.p.SOURCE/service
        original=source_unit.read_bytes().replace(b'/web/ops/gunicorn.conf.py\n',b'/web/ops/gunicorn.conf.py --bind fd://3\n',1)
        source_unit.write_bytes(original)
        self.socket_content=(Path(__file__).resolve().parents[1]/'ops/production/resmgrcheck-web.socket').read_bytes()
        (self.p.SOURCE/'web/ops/production/resmgrcheck-web.socket').write_bytes(self.socket_content)
        (self.p.SOURCE/'web/ops/gunicorn.conf.py').write_text('control_socket_disable=True\n')
        self.git('-C',str(self.p.SOURCE),'add','.');self.git('-C',str(self.p.SOURCE),'commit','-m','active legacy socket binding')
        active=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        self.active_path=self.p.OPT/'releases'/active
        self.p.write(self.p.BASE/'CREDENTIAL_RELEASE.json',__import__('json').dumps(self.credential.identity(active))+'\n')
        self.credential.stage(active,self.active_path)
        self.credential.switch_current(self.p.OPT/'current',self.active_path)
        self.unit=self.p.UNIT_ROOT/'resmgrcheck-web.service';self.unit.write_bytes(original)
        self.socket_unit=self.p.UNIT_ROOT/'resmgrcheck-web.socket';self.p.write(self.socket_unit,self.socket_content)
        path=Path(__file__).resolve().parents[1]/'ops/production/recover_socket_activation.py'
        spec=importlib.util.spec_from_file_location('socket_release_fixture',path);self.m=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'recover_credentials':self.credential}):spec.loader.exec_module(self.m)
        self.m.ACTIVE=active
        self.original=original;self.target=original.replace(b' --bind fd://3\n',b'\n',1)
        source_unit.write_bytes(self.target)
        (self.p.SOURCE/'web/ops/gunicorn.conf.py').write_text('bind=[]\n')
        (self.p.SOURCE/'web/ops/production/recover_socket_activation.py').write_text('# socket fixture\n')
        self.git('-C',str(self.p.SOURCE),'add','.');self.git('-C',str(self.p.SOURCE),'commit','-m','socket correction')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip();self.new_path=self.p.OPT/'releases'/self.revision
        paths=[self.socket_unit,self.p.BASE/'PROVISIONED.json',self.p.BASE/'CREDENTIAL_RELEASE.json',self.p.BASE/'database/audit',
            *list((self.p.CONFIG/'keys').iterdir()),self.old_path/'.git/index',self.active_path/'.git/index',
            self.active_path/service,self.active_path/'web/resmgr_web/settings.py']
        self.protected={p:p.read_bytes() for p in paths}
        self.times={p:(p.stat().st_mode,p.stat().st_mtime_ns) for p in [self.old_path/'.git/index',self.active_path/'.git/index',self.active_path/service]}

    def apply(self,rollback=False):
        with patch.object(self.credential,'require_root'),contextlib.redirect_stdout(io.StringIO()):self.m.apply(self.revision,rollback)

    def preserved(self):
        self.assertEqual(self.protected,{p:p.read_bytes() for p in self.protected})
        self.assertEqual(self.times,{p:(p.stat().st_mode,p.stat().st_mtime_ns) for p in self.times})
        self.assertTrue(all(c[1]=='show' for c in self.calls if c[0]=='systemctl'))
        self.assertEqual(self.unit.stat().st_mode&0o777,0o600)

    def test_upgrade_and_retry_change_only_known_unit_suffix_and_current(self):
        read=Path.read_bytes
        def refuse_private(path):
            if path.parent==self.p.CONFIG/'keys' or path==self.p.BASE/'database/audit':raise AssertionError('No key/DB reads')
            return read(path)
        with patch.object(Path,'read_bytes',refuse_private):self.apply();self.apply()
        self.assertEqual(self.unit.read_bytes(),self.target);self.assertEqual((self.p.OPT/'current').resolve(),self.new_path)
        self.assertEqual(os.readlink(self.new_path/'.venv'),self.credential.identity(self.m.ACTIVE)['venv']);self.preserved()

    def test_resume_after_unit_replacement_before_pointer_switch(self):
        with patch.object(self.credential,'switch_current',side_effect=RuntimeError('after unit replace')):
            with self.assertRaisesRegex(RuntimeError,'after unit replace'):self.apply()
        self.assertEqual(self.unit.read_bytes(),self.target);self.assertEqual((self.p.OPT/'current').resolve(),self.active_path)
        self.apply();self.preserved()

    def test_resume_after_pointer_switch(self):
        switch=self.credential.switch_current
        def interrupted(*args):switch(*args);raise RuntimeError('after pointer')
        with patch.object(self.credential,'switch_current',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'after pointer'):self.apply()
        self.apply();self.assertEqual(self.unit.read_bytes(),self.target);self.preserved()

    def test_interrupted_clone_is_retained_on_retry(self):
        attempts=[]
        def partial(path,revision):
            path.mkdir(mode=0o700);(path/'retained').write_text('partial');attempts.append(path);raise RuntimeError('partial clone')
        with patch.object(self.p,'clone',side_effect=partial):
            with self.assertRaisesRegex(RuntimeError,'partial clone'):self.apply()
        self.assertEqual(self.unit.read_bytes(),self.original);self.apply()
        self.assertEqual((attempts[0]/'retained').read_text(),'partial');self.preserved()

    def test_rollback_restores_original_binding_and_active_release_without_data_changes(self):
        self.apply();self.apply(rollback=True)
        self.assertEqual(self.unit.read_bytes(),self.original);self.assertEqual((self.p.OPT/'current').resolve(),self.active_path)
        self.assertTrue(self.new_path.exists());self.apply();self.preserved()

    def test_unknown_unit_is_never_overwritten(self):
        self.unit.write_bytes(b'unknown operator unit')
        with self.assertRaisesRegex(RuntimeError,'Unknown installed web unit'):self.apply()
        self.assertEqual(self.unit.read_bytes(),b'unknown operator unit');self.assertFalse(self.new_path.exists());self.preserved()

    def test_changed_socket_unit_is_refused_without_repair(self):
        self.socket_unit.write_bytes(b'unknown socket configuration');self.protected[self.socket_unit]=self.socket_unit.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'Unknown installed web unit'):self.apply()
        self.assertEqual(self.unit.read_bytes(),self.original);self.assertFalse(self.new_path.exists());self.preserved()
        self.socket_unit.write_bytes(self.socket_content);self.protected[self.socket_unit]=self.socket_content
        overrides=self.credential.DROP_ROOTS[0].parent/'resmgrcheck-web.socket.d';overrides.mkdir(mode=0o755)
        unknown=overrides/'unknown.conf';unknown.write_text('preserve')
        with self.assertRaisesRegex(RuntimeError,'Unknown socket overrides'):self.apply()
        self.assertEqual(unknown.read_text(),'preserve');self.preserved()

    def test_isolation_changes_are_rejected(self):
        path=self.p.SOURCE/self.m.SERVICE;path.write_bytes(self.target.replace(b'NoNewPrivileges=true',b'NoNewPrivileges=false'))
        self.git('-C',str(self.p.SOURCE),'commit','-am','unexpected unit change')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        with self.assertRaisesRegex(RuntimeError,'Only the reviewed web ExecStart'):self.apply()
        self.assertEqual(self.unit.read_bytes(),self.original);self.preserved()

    def test_credential_changes_are_out_of_scope(self):
        (self.p.SOURCE/'web/resmgr_web/credentials.py').write_text('# changed security policy')
        self.git('-C',str(self.p.SOURCE),'commit','-am','unexpected credential change')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        with self.assertRaisesRegex(RuntimeError,'socket-only upgrade'):self.apply()
        self.preserved()

    def test_unknown_release_and_untracked_content_are_preserved(self):
        self.new_path.mkdir(mode=0o755);unknown=self.new_path/'unknown';unknown.write_text('keep')
        with self.assertRaisesRegex(RuntimeError,'no completion manifest'):self.apply()
        self.assertEqual(unknown.read_text(),'keep');self.assertEqual(self.unit.read_bytes(),self.original);self.preserved()

    def test_modified_completed_release_blocks_retry(self):
        self.apply();unknown=self.new_path/'private';unknown.write_text('keep');unknown.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'Unknown untracked'):self.apply()
        self.assertEqual(unknown.stat().st_mode&0o777,0o600);self.preserved()

    def test_wrong_current_and_intent_are_not_repaired(self):
        current=self.p.OPT/'current';current.unlink();current.symlink_to(self.root/'unknown')
        with self.assertRaisesRegex(RuntimeError,'current release pointer'):self.apply()
        self.assertEqual(os.readlink(current),str(self.root/'unknown'));self.preserved()

    def test_active_units_and_concurrent_operators_block_upgrade(self):
        prior=self.p.run
        with patch.object(self.p,'run',side_effect=lambda argv,**kw:b'active\n' if argv[0]=='systemctl' else prior(argv,**kw)):
            with self.assertRaisesRegex(RuntimeError,'must be inactive'):self.apply()
        with self.credential.release_lock():
            with self.assertRaises(BlockingIOError):self.apply()
        self.assertEqual(self.unit.read_bytes(),self.original);self.preserved()


if __name__=='__main__':unittest.main(verbosity=2)
