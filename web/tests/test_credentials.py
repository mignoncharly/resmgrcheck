"""Real file/ACL tests; root stat ownership is simulated without reading host keys."""
import errno
import base64,json,subprocess,sys
import os
from pathlib import Path
import stat
import struct
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from resmgr_web import credentials as c


class CredentialTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.directory=self.root/'unit';self.directory.mkdir(mode=0o700)
        self.key=self.directory/'application-key';self.raw=b'synthetic-credential-value-'+b'x'*40
        self.key.write_bytes(self.raw);self.key.chmod(0o600)
        self.uid=os.geteuid()
        account=patch.object(c.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=self.uid))
        account.start();self.addCleanup(account.stop)

    def read(self,path=None):
        return c.read_credential(str(path or self.key),'RMC_WEB_SECRET_KEY','web')

    def acl(self,path,entries):
        raw=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*entry) for entry in entries)
        try:os.setxattr(path,c.ACL_XATTR,raw)
        except OSError as error:
            if error.errno==errno.ENOTSUP:self.skipTest('Fixture filesystem lacks POSIX ACLs')
            raise

    def managed(self):
        self.acl(self.key,c.systemd_acl(self.uid))
        self.acl(self.directory,c.systemd_acl(self.uid,directory=True))
        self.directory.chmod(0o550)

    def root_owned_stats(self,owner=0,parent_owner=0):
        real_stat=os.fstat
        def fake(fd):
            info=real_stat(fd)
            values={field:getattr(info,field) for field in ['st_mode','st_uid','st_gid','st_size','st_nlink']}
            values['st_uid']=parent_owner if stat.S_ISDIR(info.st_mode) else owner
            values['st_gid']=0
            return SimpleNamespace(**values)
        return patch.object(c.os,'fstat',side_effect=fake)

    def environment(self):
        return patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.directory)})

    def test_private_files_stay_accepted_and_unmodified(self):
        for mode in [0o400,0o600]:
            self.key.chmod(mode);self.assertEqual(self.read(),self.raw.decode())
            self.assertEqual(stat.S_IMODE(self.key.stat().st_mode),mode)
            self.assertEqual(self.key.read_bytes(),self.raw)

    def test_private_file_does_not_require_listing_ancestor_directories(self):
        self.directory.chmod(0o111)
        try:self.assertEqual(self.read(),self.raw.decode())
        finally:self.directory.chmod(0o700)

    def test_insecure_modes_and_ordinary_group_read_are_rejected(self):
        for mode in [0o440,0o640,0o644,0o660,0o444,0o700,0o777]:
            with self.subTest(mode=oct(mode)):
                self.key.chmod(mode)
                with self.assertRaises(c.CredentialError):self.read()

    def test_real_systemd_acl_mask_is_accepted_only_with_exact_context(self):
        self.managed()
        self.assertTrue(self.key.stat().st_mode & 0o077)  # old validator rejects the ACL mask
        with self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}):
            self.assertEqual(self.read(),self.raw.decode())
            with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':'/unexpected'}):
                with self.assertRaises(c.CredentialError):self.read()
            with self.assertRaises(c.CredentialError):
                c.read_credential(str(self.key),'RMC_WEB_MFA_KEY','web')
            with self.assertRaises(c.CredentialError):
                c.read_credential(str(self.key),'RMC_WEB_SECRET_KEY','operator')

    def test_acl_outside_fixed_systemd_directory_is_rejected(self):
        self.managed()
        with self.root_owned_stats(),self.environment():
            with self.assertRaises(c.CredentialError):self.read()

    def test_unexpected_file_and_directory_owners_are_rejected(self):
        with self.root_owned_stats(owner=self.uid+10000):
            with self.assertRaises(c.CredentialError):self.read()
        self.managed()
        for owner,parent in [(self.uid,0),(0,self.uid+10000)]:
            with self.root_owned_stats(owner,parent),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}):
                with self.assertRaises(c.CredentialError):self.read()

    def test_extra_users_groups_writes_and_other_permissions_are_rejected(self):
        self.managed();expected=c.systemd_acl(self.uid)
        bad=[[(tag,perm,0 if tag==2 else ident) for tag,perm,ident in expected],
             [(tag,4 if tag==4 else perm,ident) for tag,perm,ident in expected],
             [(tag,4 if tag==32 else perm,ident) for tag,perm,ident in expected],
             [(tag,6 if tag in {2,16} else perm,ident) for tag,perm,ident in expected],
             expected[:3]+[(8,4,0)]+expected[3:]]
        with self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}):
            for entries in bad:
                with self.subTest(entries=entries):
                    # The sandbox maps only our UID/GID. Inject hostile ACL bytes
                    # at fgetxattr for other principals; valid ACLs above are real.
                    raw=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*e) for e in entries)
                    real_getxattr=os.getxattr
                    def hostile(fd,name):
                        return real_getxattr(fd,name) if stat.S_ISDIR(os.fstat(fd).st_mode) else raw
                    with patch.object(c.os,'getxattr',side_effect=hostile):
                        with self.assertRaises(c.CredentialError):self.read()

    def test_writable_systemd_directory_is_rejected(self):
        self.managed();self.directory.chmod(0o750)
        with self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}):
            with self.assertRaises(c.CredentialError):self.read()

    def test_symlinks_in_file_and_ancestors_are_rejected(self):
        leaf=self.directory/'linked';leaf.symlink_to(self.key)
        parent=self.root/'linked-parent';parent.symlink_to(self.directory,target_is_directory=True)
        for path in [leaf,parent/'application-key']:
            with self.assertRaises(OSError):self.read(path)

    def test_nonregular_hardlinked_and_oversized_files_are_rejected(self):
        with self.assertRaises(c.CredentialError):self.read(self.directory)
        fifo=self.directory/'fifo';os.mkfifo(fifo,0o600)
        with self.assertRaises(c.CredentialError):self.read(fifo)
        self.key.write_bytes(b'x'*4097)
        with self.assertRaises(c.CredentialError):self.read()
        self.key.write_bytes(self.raw);os.link(self.key,self.directory/'hardlink')
        with self.assertRaises(c.CredentialError):self.read()

    def test_read_bound_is_rechecked_and_bad_encoding_does_not_leak(self):
        with patch.object(c.os,'read',return_value=b'x'*4097):
            with self.assertRaises(c.CredentialError):self.read()
        self.key.write_bytes(b'private-synthetic-fragment\xff')
        with self.assertRaises(c.CredentialError) as error:self.read()
        self.assertNotIn('private-synthetic',str(error.exception))
        self.key.write_bytes(b'x'*40+b'\0')
        with self.assertRaises(c.CredentialError):self.read()

    def test_malformed_acl_and_missing_service_identity_fail_closed(self):
        self.managed()
        for raw in [b'',struct.pack('<I',1),struct.pack('<I',2)+b'x']:
            with patch.object(c.os,'getxattr',return_value=raw):
                with self.assertRaises(c.CredentialError):self.read()
        with self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}), \
                patch.object(c.pwd,'getpwnam',side_effect=KeyError('missing')):
            with self.assertRaises(c.CredentialError):self.read()

    def test_wrong_os_identity_and_untrusted_group_fail_closed(self):
        self.managed()
        with self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}), \
                patch.object(c.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=self.uid+1)):
            with self.assertRaises(c.CredentialError):self.read()
        real_stat=os.fstat
        def wrong_group(fd):
            info=real_stat(fd)
            return SimpleNamespace(st_mode=info.st_mode,st_size=info.st_size,st_nlink=1,st_uid=0,st_gid=12345)
        with patch.object(c.os,'fstat',side_effect=wrong_group),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}):
            with self.assertRaises(c.CredentialError):self.read()

    def test_production_settings_use_acl_validator_and_require_files(self):
        from resmgr_web import settings as actual
        self.managed()
        with patch.object(actual,'ENVIRONMENT','production'),patch.object(actual,'SERVICE_ROLE','web'), \
                self.root_owned_stats(),self.environment(),patch.dict(c.SYSTEMD_DIRECTORIES,{'web':self.directory}), \
                patch.dict(os.environ,{'RMC_WEB_SECRET_KEY_FILE':str(self.key)}):
            self.assertEqual(actual.secret('RMC_WEB_SECRET_KEY'),self.raw.decode())
            with patch.dict(os.environ,{'RMC_WEB_SECRET_KEY_FILE':'','RMC_WEB_SECRET_KEY':self.raw.decode()}):
                from django.core.exceptions import ImproperlyConfigured
                with self.assertRaises(ImproperlyConfigured):actual.secret('RMC_WEB_SECRET_KEY')

    def test_runtime_check_and_gunicorn_entrypoints_accept_observed_acl_fixture(self):
        (self.directory/'application-key').write_text('synthetic-application-'+'x'*64)
        (self.directory/'mfa-key').write_bytes(base64.urlsafe_b64encode(b'x'*32))
        fixture=Path(__file__).with_name('credential_entrypoint_fixture.py')
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1',
            'DJANGO_SETTINGS_MODULE':'resmgr_web.settings','RMC_WEB_ENV':'production','RMC_WEB_ROLE':'web',
            'RMC_WEB_DB_HOST':'/run/resmgrcheck-db','RMC_WEB_DB_PORT':'5448','RMC_WEB_DB_USER':'resmgr_web',
            'RMC_WEB_DB_NAME':'resmgrcheck_web','RMC_WEB_STATIC_ROOT':str(self.root/'static'),
            'RMC_WEB_ARTIFACT_ROOT':str(self.root/'evidence'),'RMC_WEB_PRIVATE_ROOT':str(self.root/'private'),
            'CREDENTIALS_DIRECTORY':str(self.directory),'RMC_WEB_SECRET_KEY_FILE':str(self.directory/'application-key'),
            'RMC_WEB_MFA_KEY_FILE':str(self.directory/'mfa-key')}
        for reader in ['runtime_check','gunicorn']:
            with self.subTest(reader=reader):
                result=subprocess.run([sys.executable,str(fixture),str(self.directory),reader],env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                final=json.loads(result.stdout.splitlines()[-1]);self.assertTrue(final['credential_read_succeeded'])
                self.assertFalse(final['production_runtime_qualification'])
                self.assertNotIn('synthetic-application-',result.stdout+result.stderr)
                denied=subprocess.run([sys.executable,str(fixture),str(self.directory),reader,'insecure-acl'],env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
                self.assertNotEqual(denied.returncode,0)
                self.assertIn('credential file permissions/type invalid',denied.stderr)
                self.assertNotIn('synthetic-application-'+'x'*64,denied.stdout+denied.stderr)
