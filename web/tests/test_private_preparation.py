"""Disposable Git/process and partial-install checks; never installs host services."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class PrivatePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rmc-prepare-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        script = Path(__file__).resolve().parents[1] / 'ops/production/prepare.py'
        spec = importlib.util.spec_from_file_location('prepare_regression', script)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.source = self.root / "source 'quoted"
        self.global_config = self.root / 'global-config'
        self.global_config.write_text('[user]\n\tname = Fixture\n\temail = fixture@example.test\n')
        self.environment = {**self.module.ENV, 'GIT_CONFIG_NOSYSTEM': '1',
                            'GIT_CONFIG_GLOBAL': str(self.global_config)}
        self.git('init', str(self.source))
        (self.source / 'tracked.txt').write_text('original source\n')
        self.git('-C', str(self.source), 'add', 'tracked.txt')
        self.git('-C', str(self.source), 'commit', '-m', 'fixture')
        self.revision = self.git('-C', str(self.source), 'rev-parse', 'HEAD').stdout.decode().strip()
        (self.source / 'tracked.txt').write_text('later source HEAD\n')
        self.git('-C', str(self.source), 'commit', '-am', 'later revision')
        self.module.SOURCE = self.source
        self.module.ENV = {**self.environment, 'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1'}
        for key, name in [('BASE', 'data'), ('CONFIG', 'config'), ('OPT', 'opt'),
                          ('BACKUP', 'backups'), ('UNIT_ROOT', 'units')]:
            setattr(self.module, key, self.root / name)
        self.module.RUNTIME = [self.root / 'run-db', self.root / 'run-web']
        # These fixtures exercise root-only ownership logic with the current UID.
        # The production entry point still requires euid 0. No sudo is used here.
        account = SimpleNamespace(pw_uid=os.geteuid(), pw_dir='/nonexistent', pw_shell='/usr/sbin/nologin')
        group = SimpleNamespace(gr_gid=os.getegid())
        self.accounts = patch.object(self.module.pwd, 'getpwnam', return_value=account)
        self.groups = patch.object(self.module.grp, 'getgrnam', return_value=group)
        self.accounts.start(); self.groups.start()
        self.addCleanup(self.accounts.stop); self.addCleanup(self.groups.stop)

    def git(self, *args, extra=None):
        return subprocess.run(['git', *args], env={**self.environment, **(extra or {})},
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=20)

    def layout(self):
        m = self.module
        for path in [m.BASE, m.CONFIG, m.OPT, m.OPT/'releases', m.BASE/'private']:
            path.mkdir(mode=0o755)
            path.chmod(0o755)  # Fixture metadata must not depend on another test's umask.
        for path, mode in [(m.BACKUP, 0o700), (m.BASE/'evidence', 0o2750),
                           (m.BASE/'engine-state', 0o700), (m.CONFIG/'keys', 0o700),
                           (m.CONFIG/'executor', 0o700), (m.CONFIG/'ai', 0o700)]:
            path.mkdir(); path.chmod(mode)
        for role in ['web', 'executor', 'ai', 'operator', 'backup']:
            (m.BASE/'private'/role).mkdir(mode=0o700)
        m.write(m.BASE/'PROVISIONED.json', json.dumps({
            'kind': 'resmgrcheck-private-preparation', 'revision': self.revision})+'\n')
        m.write(m.CONFIG/'prepare-error.log', b'synthetic retained diagnostic\n')

    def test_original_clone_reproduces_root_ownership_failure(self):
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.git('-c', 'safe.directory='+str(self.source), '-c', 'core.hooksPath=/dev/null',
                     'clone', '--no-hardlinks', '--no-checkout', str(self.source), str(self.root/'old'),
                     extra={'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1'})
        self.assertIn(b'dubious ownership', caught.exception.stderr)
        self.assertIn(str(self.source/'.git').encode(), caught.exception.stderr)

    def test_exact_upload_pack_trust_clones_and_resumes_without_global_change(self):
        destination = self.root/'release'
        before = self.global_config.read_bytes()
        self.module.clone(destination, self.revision)
        self.assertEqual((destination/'tracked.txt').read_text(), 'original source\n')
        def objects(path):
            return {(p.stat().st_dev, p.stat().st_ino) for p in (path/'.git/objects').rglob('*') if p.is_file()}
        self.assertTrue(objects(destination)); self.assertTrue(objects(self.source))
        self.assertFalse(objects(destination) & objects(self.source))
        self.module.clone(destination, self.revision)
        self.assertEqual(self.global_config.read_bytes(), before)
        self.assertNotIn(b'safe', (destination/'.git/config').read_bytes())
        with self.assertRaises(subprocess.CalledProcessError):
            self.git('-C', str(self.source), 'status', '--porcelain',
                     extra={'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1'})

    def test_marked_preclone_failure_can_resume_same_revision(self):
        self.layout(); m = self.module
        marker = (m.BASE/'PROVISIONED.json').read_bytes()
        log = (m.CONFIG/'prepare-error.log').read_bytes()
        destination = m.OPT/'releases'/self.revision
        # Execute the old failing command, retaining the early install layout.
        with self.assertRaises(subprocess.CalledProcessError):
            self.git('-c', 'safe.directory='+str(self.source), 'clone', '--no-hardlinks',
                     '--no-checkout', str(self.source), str(destination),
                     extra={'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1'})
        self.assertFalse(destination.exists())
        m.check_early_resume(self.revision)
        m.clone(destination, self.revision)
        self.assertEqual((m.BASE/'PROVISIONED.json').read_bytes(), marker)
        self.assertEqual((m.CONFIG/'prepare-error.log').read_bytes(), log)

    def test_early_resume_refuses_unknown_files_without_touching_them(self):
        self.layout(); unknown = self.module.CONFIG/'keys/operator-material'
        unknown.write_bytes(b'synthetic protected data'); unknown.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError, 'Unknown resource'):
            self.module.check_early_resume(self.revision)
        self.assertEqual(unknown.read_bytes(), b'synthetic protected data')
        self.assertEqual(unknown.stat().st_mode & 0o777, 0o600)

    def test_early_resume_refuses_symlinks_and_changed_permissions(self):
        self.layout(); path = self.module.BASE/'engine-state'
        path.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.check_early_resume(self.revision)
        path.chmod(0o700)
        path.rmdir(); path.symlink_to(self.root)
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.check_early_resume(self.revision)

    def test_early_resume_refuses_unexpected_units(self):
        self.layout(); self.module.UNIT_ROOT.mkdir()
        path = self.module.UNIT_ROOT/self.module.UNITS[0]; path.write_text('unknown unit')
        with self.assertRaisesRegex(RuntimeError, 'Unexpected pre-clone resource'):
            self.module.check_early_resume(self.revision)
        self.assertEqual(path.read_text(), 'unknown unit')

    def test_existing_directory_is_validated_without_repairing_permissions(self):
        path = self.root/'unknown'; path.mkdir(mode=0o700)
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.directory(path)
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_unknown_and_interrupted_clones_are_preserved(self):
        destination = self.root/'release'; destination.mkdir()
        sentinel = destination/'unknown'; sentinel.write_bytes(b'preserve')
        with self.assertRaisesRegex(RuntimeError, 'no completion receipt'):
            self.module.clone(destination, self.revision)
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_interrupted_checkout_is_preserved_and_not_adopted(self):
        destination = self.root/'release'; real_run = self.module.run
        def interrupt_checkout(argv, **kwargs):
            if 'checkout' in argv:raise RuntimeError('synthetic checkout interruption')
            return real_run(argv, **kwargs)
        with patch.object(self.module, 'run', side_effect=interrupt_checkout):
            with self.assertRaisesRegex(RuntimeError, 'checkout interruption'):
                self.module.clone(destination, self.revision)
        head = (destination/'.git/HEAD').read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'no completion receipt'):
            self.module.clone(destination, self.revision)
        self.assertEqual((destination/'.git/HEAD').read_bytes(), head)
        self.assertFalse((destination/'tracked.txt').exists())

    def test_completed_clone_refuses_other_revision_or_modified_source(self):
        destination = self.root/'release'; self.module.clone(destination, self.revision)
        with self.assertRaisesRegex(RuntimeError, 'receipt mismatch'):
            self.module.clone(destination, '0'*40)
        (destination/'tracked.txt').write_text('unknown modification\n')
        with self.assertRaisesRegex(RuntimeError, 'tracked changes'):
            self.module.clone(destination, self.revision)
        self.assertEqual((destination/'tracked.txt').read_text(), 'unknown modification\n')

    def test_marker_refuses_links_and_exposed_modes(self):
        self.layout(); marker = self.module.BASE/'PROVISIONED.json'
        marker.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.protected_json(marker)
        marker.chmod(0o600); os.link(marker, self.root/'hardlink')
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.protected_json(marker)

    def test_apply_requires_root_before_touching_resources(self):
        with patch.object(self.module.os, 'geteuid', return_value=1000), patch.object(self.module, 'run') as run:
            with self.assertRaisesRegex(SystemExit, 'requires the local root operator'):
                self.module.prepare(self.revision)
        run.assert_not_called()

    def test_early_resume_refuses_linked_diagnostics(self):
        self.layout(); diagnostic = self.module.CONFIG/'prepare-error.log'
        os.link(diagnostic, self.root/'other-log')
        with self.assertRaisesRegex(RuntimeError, 'protection mismatch'):
            self.module.check_early_resume(self.revision)
        self.assertEqual(diagnostic.read_bytes(), b'synthetic retained diagnostic\n')

    def test_different_revision_stops_before_any_mutation(self):
        self.layout(); m = self.module
        with patch.object(m.os, 'geteuid', return_value=0), patch.object(m, 'protected_json', return_value={
                'kind': 'resmgrcheck-private-preparation', 'revision': self.revision}), \
                patch.object(m, 'run') as run, patch.object(m, 'directory') as directory:
            with self.assertRaisesRegex(RuntimeError, 'Existing preparation differs'):
                m.prepare('0'*40)
        run.assert_not_called(); directory.assert_not_called()

    def test_prepare_resumes_marked_layout_through_both_clones(self):
        self.layout(); m = self.module; m.ENGINE = self.revision
        marker = (m.BASE/'PROVISIONED.json').read_bytes()
        real_run = m.run; real_json = m.protected_json; uid = os.geteuid()
        commands = []
        def fixture_record(path):
            with patch.object(m.os, 'geteuid', return_value=uid):
                return real_json(path)
        def bounded_run(argv, **kwargs):
            commands.append(argv)
            if argv[0] == 'usermod': return b''
            if argv[0] == 'git': return real_run(argv, **kwargs)
            raise RuntimeError('fixture stop before venv/database/service operations')
        real_private = m.check_private_file
        def fixture_private(path):
            with patch.object(m.os, 'geteuid', return_value=uid):
                return real_private(path)
        with patch.object(m.os, 'geteuid', return_value=0), \
                patch.object(m, 'protected_json', side_effect=fixture_record), \
                patch.object(m, 'check_private_file', side_effect=fixture_private), \
                patch.object(m, 'run', side_effect=bounded_run):
            with self.assertRaisesRegex(RuntimeError, 'fixture stop before venv'):
                m.prepare(self.revision)
        self.assertEqual((m.BASE/'PROVISIONED.json').read_bytes(), marker)
        for destination in [m.OPT/'releases'/self.revision, m.OPT/'engine']:
            self.assertEqual((destination/'tracked.txt').read_text(), 'original source\n')
        self.assertEqual((m.OPT/'engine/.local/state').resolve(), m.BASE/'engine-state')
        self.assertFalse(any(c[0] in {'systemctl', 'groupadd', 'useradd'} for c in commands))


if __name__ == '__main__':
    unittest.main()
