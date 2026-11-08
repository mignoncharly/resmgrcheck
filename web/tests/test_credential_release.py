"""Real disposable Git/release recovery; UID fixtures, never production installation."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class CredentialReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        old_umask=os.umask(0o022);self.addCleanup(os.umask,old_umask)
        ops=Path(__file__).resolve().parents[1]/'ops/production'
        def load(name,path):
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
        p=load('release_prepare_fixture',ops/'prepare.py')
        with patch.dict(sys.modules,{'prepare':p}):self.m=load('release_fixture',ops/'recover_credentials.py')
        self.p=p;p.SOURCE=self.root/'source';p.SOURCE.mkdir(mode=0o755)
        p.ENV={**p.ENV,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
        self.git('init',str(p.SOURCE))
        files={'.gitignore':'.venv/\n','web/resmgr_web/settings.py':'# original\n',
            'web/requirements.lock':'# unchanged dependency lock\n',
            'web/ops/production/resmgrcheck-web.service':(ops/'resmgrcheck-web.service').read_text()}
        for name,raw in files.items():
            path=p.SOURCE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw)
        self.git('-C',str(p.SOURCE),'add','.');self.git('-C',str(p.SOURCE),'commit','-m','installed fixture')
        self.old=self.git('-C',str(p.SOURCE),'rev-parse','HEAD').strip();self.m.INSTALLED_REVISION=self.old
        (p.SOURCE/'web/resmgr_web/settings.py').write_text('# corrected\n')
        (p.SOURCE/'web/resmgr_web/credentials.py').write_text('# fixture validator\n')
        (p.SOURCE/'web/ops/production/recover_credentials.py').write_text('# fixture release\n')
        self.git('-C',str(p.SOURCE),'add','.');self.git('-C',str(p.SOURCE),'commit','-m','correction fixture')
        self.revision=self.git('-C',str(p.SOURCE),'rev-parse','HEAD').strip()
        for attr in ['OPT','BASE','CONFIG','UNIT_ROOT']:
            path=self.root/attr;path.mkdir(mode=0o755);setattr(p,attr,path)
        (p.OPT/'releases').mkdir(mode=0o755)
        (p.CONFIG/'keys').mkdir(mode=0o700)
        self.m.DROP_ROOTS=[self.root/'runtime-drop',self.root/'persistent-drop'];self.m.DIAGNOSTIC=self.root/'diagnostic.py'
        for module,attribute,value in [(p.pwd,'getpwnam',SimpleNamespace(pw_uid=os.geteuid())),
                                       (p.grp,'getgrnam',SimpleNamespace(gr_gid=os.getegid()))]:
            mock=patch.object(module,attribute,return_value=value);mock.start();self.addCleanup(mock.stop)
        p.write(p.BASE/'PROVISIONED.json',json.dumps({'kind':'resmgrcheck-private-preparation','revision':self.old})+'\n')
        for name in ['application-key','mfa-key','backup-key']:p.write(p.CONFIG/'keys'/name,b'synthetic-private-material-'+name.encode())
        self.old_path=p.OPT/'releases'/self.old;self.new_path=p.OPT/'releases'/self.revision
        p.clone(self.old_path,self.old)
        (self.old_path/'.venv/bin').mkdir(parents=True,mode=0o755);(self.old_path/'.venv').chmod(0o755)
        (self.old_path/'.venv/bin/python').symlink_to(sys.executable)
        (p.OPT/'current').symlink_to(self.old_path,target_is_directory=True)
        p.write(p.UNIT_ROOT/'resmgrcheck-web.service',files['web/ops/production/resmgrcheck-web.service'])
        (p.BASE/'database').mkdir(mode=0o700);(p.BASE/'database/audit').write_bytes(b'preserve synthetic DB and audit')
        self.calls=[];real_run=p.run
        def readonly_units(argv,**kwargs):
            self.calls.append(argv)
            if argv[0]=='systemctl':
                if argv[1]!='show':raise AssertionError('No service mutation allowed')
                return b'' if '--property=DropInPaths' in argv else b'inactive\n'
            return real_run(argv,**kwargs)
        mock=patch.object(p,'run',side_effect=readonly_units);mock.start();self.addCleanup(mock.stop)
        self.protected={path:path.read_bytes() for path in [p.BASE/'PROVISIONED.json',p.BASE/'database/audit',
            p.UNIT_ROOT/'resmgrcheck-web.service',*list((p.CONFIG/'keys').iterdir()),self.old_path/'web/resmgr_web/settings.py',self.old_path/'.git/index']}
        self.immutable_stats={path:(path.stat().st_mode,path.stat().st_mtime_ns) for path in [
            self.old_path/'web/resmgr_web/settings.py',self.old_path/'.git/index']}

    def git(self,*args):
        r=subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.test',*args],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self.p.ENV if hasattr(self,'p') else None,check=True,timeout=20)
        return r.stdout.decode()

    def apply(self,rollback=False):
        with patch.object(self.m,'require_root'),contextlib.redirect_stdout(io.StringIO()):self.m.apply(self.revision,rollback)

    def assert_preserved(self):
        self.assertEqual(self.protected,{path:path.read_bytes() for path in self.protected})
        self.assertTrue(all(c[1]=='show' for c in self.calls if c[0]=='systemctl'))
        self.assertEqual(self.immutable_stats,{path:(path.stat().st_mode,path.stat().st_mtime_ns) for path in self.immutable_stats})

    def test_new_release_activation_and_repeat_preserve_original_and_secrets(self):
        real_read=Path.read_bytes
        def refuse_secret_reads(path):
            if path.parent==self.p.CONFIG/'keys' or path==self.p.BASE/'database/audit':raise AssertionError('Secrets/DB must remain unopened')
            return real_read(path)
        with patch.object(Path,'read_bytes',refuse_secret_reads):self.apply();self.apply()
        self.assertEqual((self.p.OPT/'current').resolve(),self.new_path)
        self.assertEqual(os.readlink(self.new_path/'.venv'),str(self.old_path/'.venv'))
        self.assertEqual((self.new_path/'web/resmgr_web/settings.py').read_text(),'# corrected\n')
        self.assert_preserved()

    def test_resume_after_completed_stage_before_pointer_switch(self):
        with patch.object(self.m,'switch_current',side_effect=RuntimeError('interrupted switch')):
            with self.assertRaisesRegex(RuntimeError,'interrupted switch'):self.apply()
        self.assertEqual((self.p.OPT/'current').resolve(),self.old_path)
        self.assertTrue(self.new_path.exists());self.apply();self.assert_preserved()

    def test_resume_after_pointer_switch_is_idempotent(self):
        real_switch=self.m.switch_current
        def interrupted(*args):real_switch(*args);raise RuntimeError('after switch')
        with patch.object(self.m,'switch_current',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'after switch'):self.apply()
        self.assertEqual((self.p.OPT/'current').resolve(),self.new_path)
        self.apply();self.assert_preserved()

    def test_interrupted_clone_is_retained_and_retry_uses_fresh_attempt(self):
        retained=[]
        def partial(path,revision):
            path.mkdir(mode=0o700);(path/'retained').write_text('partial evidence');retained.append(path)
            raise RuntimeError('interrupted clone')
        with patch.object(self.p,'clone',side_effect=partial):
            with self.assertRaisesRegex(RuntimeError,'interrupted clone'):self.apply()
        self.assertFalse(self.new_path.exists());self.apply()
        self.assertEqual((retained[0]/'retained').read_text(),'partial evidence');self.assert_preserved()

    def test_unknown_release_is_not_adopted_or_overwritten(self):
        self.new_path.mkdir(mode=0o755);unknown=self.new_path/'unknown';unknown.write_text('preserve')
        with self.assertRaisesRegex(RuntimeError,'completion manifest'):self.apply()
        self.assertEqual(unknown.read_text(),'preserve')
        self.assertEqual((self.p.OPT/'current').resolve(),self.old_path);self.assert_preserved()

    def test_modified_completed_release_is_refused(self):
        self.apply();path=self.new_path/'web/resmgr_web/settings.py';path.write_text('unknown change')
        with self.assertRaisesRegex(RuntimeError,'tracked changes'):self.apply()
        self.assertEqual(path.read_text(),'unknown change');self.assert_preserved()

    def test_extra_untracked_content_is_not_chmodded_or_deleted(self):
        self.apply();path=self.new_path/'private';path.write_text('unknown');path.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,'Unknown untracked'):self.apply()
        self.assertEqual(path.read_text(),'unknown');self.assertEqual(path.stat().st_mode&0o777,0o600);self.assert_preserved()

    def test_out_of_scope_dependency_change_stops_before_deployment(self):
        (self.p.SOURCE/'web/requirements.lock').write_text('unexpected dependency')
        self.git('-C',str(self.p.SOURCE),'commit','-am','out of scope')
        self.revision=self.git('-C',str(self.p.SOURCE),'rev-parse','HEAD').strip()
        with self.assertRaisesRegex(RuntimeError,'outside credential recovery'):self.apply()
        self.assertFalse((self.p.BASE/'CREDENTIAL_RELEASE.json').exists());self.assert_preserved()

    def test_protected_source_key_mode_is_not_repaired(self):
        key=self.p.CONFIG/'keys/application-key';key.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'protection mismatch'):self.apply()
        self.assertEqual(key.stat().st_mode&0o777,0o644);self.assert_preserved()

    def test_rollback_preserves_both_releases_and_all_data(self):
        self.apply();self.apply(rollback=True)
        self.assertEqual((self.p.OPT/'current').resolve(),self.old_path);self.assertTrue(self.new_path.exists())
        self.apply();self.assertEqual((self.p.OPT/'current').resolve(),self.new_path);self.assert_preserved()

    def test_unknown_current_pointer_is_refused(self):
        current=self.p.OPT/'current';current.unlink();current.symlink_to(self.root/'unknown')
        with self.assertRaisesRegex(RuntimeError,'current release pointer'):self.apply()
        self.assertEqual(os.readlink(current),str(self.root/'unknown'));self.assert_preserved()

    def test_active_units_and_overrides_stop_before_staging(self):
        prior=self.p.run
        with patch.object(self.p,'run',side_effect=lambda argv,**kw: b'active\n' if argv[0]=='systemctl' else prior(argv,**kw)):
            with self.assertRaisesRegex(RuntimeError,'must be inactive'):self.apply()
        self.m.DROP_ROOTS[0].mkdir(mode=0o755);(self.m.DROP_ROOTS[0]/'unknown.conf').write_text('keep')
        with self.assertRaisesRegex(RuntimeError,'override path'):self.apply()
        self.assertFalse(self.new_path.exists());self.assert_preserved()

    def test_concurrent_activation_lock_refuses_second_operator(self):
        with self.m.release_lock():
            with self.assertRaises(BlockingIOError):self.apply()
        self.assertFalse(self.new_path.exists());self.assert_preserved()

    def test_nonroot_cannot_apply(self):
        with patch.object(self.m.os,'geteuid',return_value=1000):
            with self.assertRaises(SystemExit):self.m.apply(self.revision)
        self.assertFalse(self.new_path.exists());self.assert_preserved()

    def test_unknown_canonical_unit_is_preserved(self):
        path=self.p.UNIT_ROOT/'resmgrcheck-web.service';path.write_bytes(b'unknown unit')
        self.protected[path]=path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'Canonical web unit changed'):self.apply()
        self.assertFalse(self.new_path.exists());self.assert_preserved()

    def test_foreign_intent_and_manifest_are_not_overwritten(self):
        intent=self.p.BASE/'CREDENTIAL_RELEASE.json';self.p.write(intent,'{"kind":"unknown"}\n')
        with self.assertRaisesRegex(RuntimeError,'Another credential release'):self.apply()
        self.assertEqual(intent.read_text(),'{"kind":"unknown"}\n');self.assertFalse(self.new_path.exists())
        self.assert_preserved()

    def test_atomic_publication_never_replaces_even_an_empty_unknown_directory(self):
        attempt=self.p.OPT/'releases/attempt';attempt.mkdir();(attempt/'owned').write_text('preserve')
        self.new_path.mkdir();inode=self.new_path.stat().st_ino
        with self.assertRaises(FileExistsError):self.m.publish_new_release(attempt,self.new_path)
        self.assertEqual(self.new_path.stat().st_ino,inode);self.assertEqual((attempt/'owned').read_text(),'preserve')


if __name__=='__main__':unittest.main()
