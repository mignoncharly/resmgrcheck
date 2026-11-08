"""Disposable metadata/temporary override tests; no real keys or host units touched."""
import contextlib
import errno
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch


class CredentialDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        source=Path(__file__).resolve().parents[1]/'ops/production/credential_diagnostic.py'
        spec=importlib.util.spec_from_file_location('credential_diagnostic_test',source)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.credentials=self.root/'credentials';self.credentials.mkdir(mode=0o700)
        self.raw=b'synthetic-only-secret-value-'+b'x'*40
        for identity in self.module.IDS.values():
            path=self.credentials/identity;path.write_bytes(self.raw);path.chmod(0o600)
        self.environment={'CREDENTIALS_DIRECTORY':str(self.credentials),
            **{key:str(self.credentials/value) for key,value in self.module.IDS.items()}}

    def capture(self):
        output=io.StringIO()
        with patch.dict(os.environ,self.environment),contextlib.redirect_stdout(output):
            self.assertEqual(self.module.probe(),0)
        self.assertNotIn(self.raw.decode(),output.getvalue())
        return json.loads(output.getvalue())

    def layout(self):
        m=self.module
        m.SCRIPT=self.root/'credential-diagnostic.py'
        m.DROP_ROOT=self.root/'runtime/web.service.d';m.DROP_ROOT.parent.mkdir(mode=0o755)
        m.DROP=m.DROP_ROOT/'50-resmgrcheck-credential-diagnostic.conf'
        m.PERSISTENT_DROP_ROOT=self.root/'persistent/web.service.d'
        m.UNIT=self.root/'installed.service';m.UNIT.write_bytes(m.REFERENCE.read_bytes());m.UNIT.chmod(0o600)

    def test_probe_outputs_only_requested_metadata_without_content_reads(self):
        before={p.name:(p.read_bytes(),p.stat().st_mode) for p in self.credentials.iterdir()}
        with patch.object(self.module.os,'read',side_effect=AssertionError('No secret reads')):
            data=self.capture()
        self.assertEqual(set(data),{'probe','credentials'})
        for row in data['credentials']:
            self.assertEqual(set(row),{'credential_id','uid','gid','mode','file_type','access_acl'})
            self.assertEqual(row['uid'],os.geteuid());self.assertEqual(row['mode'],'0o600')
            self.assertEqual(row['file_type'],'regular');self.assertIsNone(row['access_acl'])
        self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mode) for p in self.credentials.iterdir()})

    def test_probe_decodes_actual_posix_acl_mask_metadata(self):
        uid=os.geteuid();undefined=0xffffffff
        entries=[(1,4,undefined),(2,4,uid),(4,0,undefined),(16,4,undefined),(32,0,undefined)]
        raw=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*entry) for entry in entries)
        path=self.credentials/'application-key'
        try:os.setxattr(path,'system.posix_acl_access',raw)
        except OSError as error:
            if error.errno==errno.ENOTSUP:self.skipTest('Fixture filesystem has no POSIX ACL support')
            raise
        row=self.capture()['credentials'][0]
        self.assertEqual(row['mode'],'0o440')
        self.assertEqual(row['access_acl']['entries'][1],{'tag':'user','id':uid,'permissions':4})
        self.assertEqual(row['access_acl']['entries'][2]['permissions'],0)

    def test_symlink_is_reported_without_following_it(self):
        path=self.credentials/'application-key';path.unlink();path.symlink_to(self.credentials/'mfa-key')
        row=self.capture()['credentials'][0]
        self.assertEqual(row['file_type'],'symlink');self.assertIsNone(row['access_acl'])

    def test_missing_paths_and_metadata_errors_still_allow_runtime_check(self):
        self.environment['RMC_WEB_SECRET_KEY_FILE']='unexpected-path'
        (self.credentials/'mfa-key').unlink()
        rows=self.capture()['credentials']
        self.assertEqual(rows[0]['metadata_error'],'missing_or_unexpected_runtime_path')
        self.assertEqual(rows[1]['metadata_error'],'unavailable');self.assertEqual(rows[1]['errno'],errno.ENOENT)

    def test_malformed_acl_is_not_dumped(self):
        with patch.object(self.module.os,'getxattr',return_value=self.raw):
            row=self.capture()['credentials'][0]
        self.assertEqual(row['access_acl'],{'error':'invalid_acl_encoding'})

    def test_override_keeps_runtime_check_user_credentials_and_isolation(self):
        lines=self.module.OVERRIDE.decode().splitlines()
        self.assertEqual([line for line in lines if line.startswith('ExecStartPre=')],[
            'ExecStartPre=',
            'ExecStartPre=/opt/resmgrcheck/current/.venv/bin/python /run/resmgrcheck-credential-diagnostic.py --probe',
            'ExecStartPre=/opt/resmgrcheck/current/.venv/bin/python manage.py runtime_check'])
        self.assertEqual([line.split('=')[0] for line in lines if '=' in line],['ExecStartPre']*3+['Restart'])
        unit=self.module.REFERENCE.read_text()
        for line in ['User=resmgr-web','LoadCredential=application-key:/etc/resmgrcheck/keys/application-key',
                     'LoadCredential=mfa-key:/etc/resmgrcheck/keys/mfa-key','ProtectSystem=strict','NoNewPrivileges=true']:
            self.assertIn(line,unit)

    def test_install_remove_is_repeatable_and_preserves_canonical_unit(self):
        self.layout();m=self.module;original=m.UNIT.read_bytes()
        with patch.object(m,'require_root'),patch.object(m,'stopped'),contextlib.redirect_stdout(io.StringIO()):
            m.change(True);m.change(True)
            self.assertEqual(m.DROP.read_bytes(),m.OVERRIDE)
            self.assertEqual(m.SCRIPT.stat().st_mode&0o777,0o644)
            m.change(False);m.change(False)
        self.assertFalse(m.SCRIPT.exists());self.assertFalse(m.DROP.exists())
        self.assertEqual(m.UNIT.read_bytes(),original);self.assertEqual(m.UNIT.stat().st_mode&0o777,0o600)

    def test_unknown_files_are_never_overwritten_or_removed(self):
        self.layout();m=self.module;m.SCRIPT.write_bytes(b'unknown');m.SCRIPT.chmod(0o644)
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            for install in [True,False]:
                with self.assertRaisesRegex(RuntimeError,'unknown diagnostic'):m.change(install)
        self.assertEqual(m.SCRIPT.read_bytes(),b'unknown');self.assertFalse(m.DROP.exists())

    def test_unknown_overrides_are_preserved_before_any_install(self):
        self.layout();m=self.module;m.DROP_ROOT.mkdir(mode=0o755);unknown=m.DROP_ROOT/'other.conf';unknown.write_text('keep')
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'Existing runtime web overrides'):m.change(True)
        self.assertFalse(m.SCRIPT.exists());self.assertEqual(unknown.read_text(),'keep')

    def test_linked_diagnostic_paths_are_refused_without_reading_targets(self):
        self.layout();m=self.module;target=self.credentials/'application-key'
        m.SCRIPT.symlink_to(target)
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'unknown diagnostic'):m.change(True)
        m.SCRIPT.unlink();os.link(target,m.SCRIPT)
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'unknown diagnostic'):m.change(False)
        self.assertEqual(target.read_bytes(),self.raw);self.assertFalse(m.DROP.exists())

    def test_unit_changes_links_and_wrong_modes_are_rejected(self):
        self.layout();m=self.module
        m.UNIT.write_text('unknown service')
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'unknown diagnostic or unit'):m.change(True)
        m.UNIT.write_bytes(m.REFERENCE.read_bytes());m.UNIT.chmod(0o666)
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'unknown diagnostic or unit'):m.change(True)
        self.assertFalse(m.SCRIPT.exists())

    def test_install_remove_require_root_and_stopped_units(self):
        self.layout();m=self.module
        with patch.object(m.os,'geteuid',return_value=1000),self.assertRaises(SystemExit):m.change(True)
        with patch.object(m,'require_root'),patch.object(m.subprocess,'run',return_value=type('Result',(),{'stdout':b'active\n'})()):
            with self.assertRaisesRegex(RuntimeError,'Stop only the dedicated'):m.change(True)
        self.assertFalse(m.SCRIPT.exists())

    def test_extra_startup_checks_are_not_silently_replaced(self):
        self.layout();m=self.module
        m.REFERENCE=self.root/'reference.service'
        m.REFERENCE.write_bytes(m.UNIT.read_bytes()+b'ExecStartPre=/operator/check\n')
        m.UNIT.write_bytes(m.REFERENCE.read_bytes())
        with patch.object(m,'require_root'),patch.object(m,'stopped'):
            with self.assertRaisesRegex(RuntimeError,'Additional startup checks'):m.change(True)
        self.assertFalse(m.SCRIPT.exists());self.assertFalse(m.DROP.exists())


if __name__=='__main__':unittest.main()
