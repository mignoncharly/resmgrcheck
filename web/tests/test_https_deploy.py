"""Real disposable filesystem rollback; root, systemd, renewal and HTTP are modeled."""
import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
OPS=Path(__file__).resolve().parents[1]/'ops/production'
sys.path.insert(0,str(OPS))
import deploy_https as deploy
from https_checks import CheckFailed

REVISION='5'*40;DRIVER='6'*40
class HTTPSDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.umask=os.umask(0o022);self.addCleanup(os.umask,self.umask)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        nginx=self.root/'nginx';config=self.root/'config'
        for path in [nginx/'sites-available',nginx/'sites-enabled',nginx/'conf.d',self.root/'hooks',config,
                self.root/'operator',self.root/'logs',self.root/'acme']:
            path.mkdir(parents=True,exist_ok=True);path.chmod(0o755)
        values={'NGINX':nginx,'SITE':nginx/'sites-available'/deploy.HOST,'HTTP':nginx/'conf.d/resmgrcheck-security.conf',
            'ENABLED':nginx/'sites-enabled'/deploy.HOST,'HOOK':self.root/'hooks/resmgrcheck-nginx','STATE':self.root/'operator/https-deployment',
            'LOGS':self.root/'logs','ACME':self.root/'acme','CONFIG':config}
        for name,value in values.items():self.stack.enter_context(patch.object(deploy,name,value))
        deploy.SITE.write_bytes((OPS/'nginx-bootstrap-site.conf').read_bytes());deploy.HTTP.write_bytes((OPS/'nginx-bootstrap-http.conf').read_bytes())
        deploy.ENABLED.symlink_to(deploy.SITE);self.other=nginx/'sites-available/other-application';self.other.write_text('Preserve unrelated private settings\n')
        for path in [deploy.SITE,deploy.HTTP,self.other]:path.chmod(0o644)
        self.before={p:p.read_bytes() for p in [deploy.SITE,deploy.HTTP,self.other]};self.calls=[]
        self.stack.enter_context(patch.object(deploy,'require_root'))
        self.stack.enter_context(patch.object(deploy,'source_check'))
        self.stack.enter_context(patch.object(deploy,'units_and_runtime',return_value={'nonroot_isolation':'passed'}))
        self.stack.enter_context(patch.object(deploy,'certificate_and_renewal',return_value='certificate-public-hash'))
        def logs():
            for name in ['resmgrcheck-access.log','resmgrcheck-error.log']:
                p=deploy.LOGS/name
                if not p.exists():deploy.new_file(p,b'',0o640)
        self.stack.enter_context(patch.object(deploy,'ensure_logs',side_effect=logs))
        self.stack.enter_context(patch.object(deploy,'checks',return_value=[{'check':'modeled-HTTPS','status':'passed'}]))
        self.static=self.root/'static'/REVISION;self.static.mkdir(parents=True);(self.static/'control').mkdir();(self.static/'control/app.css').write_text('body{}');(self.static/'control/app.js').write_bytes(b'')
        original=deploy.directory;original_read=deploy.read
        def redirected(path):
            prefix=Path('/var/lib/resmgrcheck/static')/REVISION
            return self.static/path.relative_to(prefix) if path.is_relative_to(prefix) else path
        def directory(path,mode=None):return original(redirected(path),mode)
        def read(path,**kwargs):return original_read(redirected(path),**kwargs)
        self.stack.enter_context(patch.object(deploy,'directory',side_effect=directory));self.stack.enter_context(patch.object(deploy,'read',side_effect=read))
        asset=deploy.static_asset;self.stack.enter_context(patch.object(deploy,'static_asset',side_effect=lambda path:asset(redirected(path))))
        owner=self
        class Client:
            def request(self,path,**kwargs):
                if path.startswith('/.well-known/acme-challenge/'):return 200,{},(deploy.ACME/path.rsplit('/',1)[1]).read_bytes()
                if path=='/' and kwargs.get('secure') is False:
                    return (404 if deploy.SITE.read_bytes()==owner.before[deploy.SITE] else 308),{},b''
                if path=='/static/control/app.js':return 200,{'content-type':'application/javascript'},b''
                return 404,{},b''
        self.stack.enter_context(patch.object(deploy,'Client',return_value=Client()))
        def command(argv,**kwargs):self.calls.append(list(map(str,argv)));return b''
        self.execute=self.stack.enter_context(patch.object(deploy,'command',side_effect=command))
    def apply(self,rollback=False):
        with contextlib.redirect_stdout(io.StringIO()):deploy.apply(REVISION,DRIVER,rollback,False)
    def state(self):return json.loads((deploy.STATE/'state.json').read_text())
    def preserved(self):self.assertEqual(self.other.read_bytes(),self.before[self.other])
    def test_deploy_and_repeat_backup_once_prove_rollback_and_preserve_other_sites(self):
        self.apply();self.apply();self.assertEqual(self.state()['phase'],'verified');self.assertTrue(self.state()['rollback_verified'])
        self.assertEqual(deploy.SITE.read_bytes(),deploy.site_config(REVISION).encode());self.assertEqual(deploy.HTTP.read_bytes(),deploy.http_config().encode())
        self.assertEqual(sum(args[0]=='certbot' for args in self.calls),1)
        self.assertEqual((deploy.STATE/'site.before').read_bytes(),self.before[deploy.SITE]);self.preserved()
        self.assertTrue(all(args==['nginx','-t'] or args==['systemctl','reload','nginx.service'] or args[0]=='certbot' for args in self.calls))
    def test_explicit_rollback_restores_only_owned_files_and_keeps_backup(self):
        self.apply();self.apply(True)
        self.assertEqual(deploy.SITE.read_bytes(),self.before[deploy.SITE]);self.assertEqual(deploy.HTTP.read_bytes(),self.before[deploy.HTTP]);self.assertFalse(deploy.HOOK.exists())
        self.assertEqual(self.state()['phase'],'rolled_back');self.preserved()
    def test_https_failure_restores_original_configuration_without_touching_other_sites(self):
        with patch.object(deploy,'checks',side_effect=CheckFailed('fixture_readiness_failed')),patch.object(deploy.time,'sleep'):
            with self.assertRaisesRegex(CheckFailed,'own_configuration_rolled_back'):self.apply()
        self.assertEqual(deploy.SITE.read_bytes(),self.before[deploy.SITE]);self.assertFalse(deploy.HOOK.exists());self.preserved()
    def test_preflight_failure_causes_no_reload_or_configuration_mutation(self):
        with patch.object(deploy,'units_and_runtime',side_effect=CheckFailed('fixture_runtime_failed')),self.assertRaises(CheckFailed):self.apply()
        self.assertEqual(self.calls,[]);self.assertEqual(deploy.SITE.read_bytes(),self.before[deploy.SITE]);self.preserved()
    def test_failed_candidate_nginx_test_never_reloads_invalid_config(self):
        def command(argv,**kwargs):
            self.calls.append(list(map(str,argv)))
            if argv==['nginx','-t'] and deploy.SITE.read_bytes()!=self.before[deploy.SITE]:raise CheckFailed('fixture_nginx_t_failed')
            return b''
        self.execute.side_effect=command
        with self.assertRaises(CheckFailed):self.apply()
        self.assertEqual(deploy.SITE.read_bytes(),self.before[deploy.SITE]);self.assertEqual(self.calls.count(['systemctl','reload','nginx.service']),1);self.preserved()
    def test_reload_failure_also_restores_and_validates_original(self):
        failed=False
        def command(argv,**kwargs):
            nonlocal failed
            self.calls.append(list(map(str,argv)))
            if argv==['systemctl','reload','nginx.service'] and not failed:failed=True;raise CheckFailed('fixture_reload_failed')
            return b''
        self.execute.side_effect=command
        with self.assertRaises(CheckFailed):self.apply()
        self.assertEqual(self.state()['phase'],'rolled_back_after_failure');self.assertEqual(deploy.SITE.read_bytes(),self.before[deploy.SITE]);self.preserved()
    def test_unknown_initial_resources_and_wrong_enabled_link_are_not_adopted(self):
        deploy.SITE.write_bytes(b'unknown configuration')
        with self.assertRaisesRegex(CheckFailed,'unknown_original'):self.apply()
        self.assertEqual(deploy.SITE.read_bytes(),b'unknown configuration');self.assertEqual(self.calls,[])
        deploy.SITE.write_bytes(self.before[deploy.SITE]);deploy.ENABLED.unlink();deploy.ENABLED.symlink_to(self.other)
        with self.assertRaisesRegex(CheckFailed,'enabled_site_link'):self.apply()
        self.preserved()
    def test_unknown_concurrent_edit_is_not_overwritten_during_rollback(self):
        def changed(*args,**kwargs):deploy.SITE.write_bytes(b'unknown concurrent operator edit');raise CheckFailed('fixture failure')
        with patch.object(deploy,'checks',side_effect=changed),patch.object(deploy.time,'sleep'),self.assertRaisesRegex(CheckFailed,'safe_rollback_could_not_complete'):self.apply()
        self.assertEqual(deploy.SITE.read_bytes(),b'unknown concurrent operator edit');self.assertEqual(self.state()['phase'],'rollback_requires_operator_review');self.preserved()
    def test_interrupted_initial_backup_can_resume_without_replacing_it(self):
        create=deploy.new_file;fired=False
        def interrupted(path,*args,**kwargs):
            nonlocal fired
            create(path,*args,**kwargs)
            if path.name=='site.before' and not fired:fired=True;raise KeyboardInterrupt
        with patch.object(deploy,'new_file',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):self.apply()
        before=(deploy.STATE/'site.before').stat().st_mtime_ns;self.apply();self.assertEqual((deploy.STATE/'site.before').stat().st_mtime_ns,before);self.preserved()
    def test_concurrent_deployment_and_symlink_backup_are_refused(self):
        self.apply()
        with deploy.locked(),self.assertRaises(BlockingIOError):self.apply()
        backup=deploy.STATE/'site.before';raw=backup.read_bytes();backup.unlink();backup.symlink_to(self.other)
        with self.assertRaises(OSError):self.apply()
        self.assertEqual(self.other.read_bytes(),self.before[self.other]);self.assertEqual(raw,self.before[deploy.SITE])

    def test_renewal_hook_is_a_noop_for_other_certificates_and_checks_before_reload(self):
        import subprocess
        hook=self.root/'test-renewal-hook.sh';hook.write_text(deploy.renewal_hook());hook.chmod(0o700)
        subprocess.run(['/bin/sh',str(hook)],env={'PATH':'/usr/bin:/bin','RENEWED_LINEAGE':'/fixture/other-lineage','RENEWED_DOMAINS':'other.invalid'},check=True,timeout=3)
        calls=self.root/'hook-calls';nginx=self.root/'fake-nginx';systemctl=self.root/'fake-systemctl'
        nginx.write_text('#!/bin/sh\nprintf \'nginx %s\\n\' "$*" >> '+str(calls)+'\n');nginx.chmod(0o700)
        systemctl.write_text('#!/bin/sh\nprintf \'systemctl %s\\n\' "$*" >> '+str(calls)+'\n');systemctl.chmod(0o700)
        hook.write_text(deploy.renewal_hook().replace('/usr/sbin/nginx',str(nginx)).replace('/usr/bin/systemctl',str(systemctl)))
        subprocess.run(['/bin/sh',str(hook)],env={'PATH':'/usr/bin:/bin','RENEWED_LINEAGE':'/etc/letsencrypt/live/'+deploy.HOST,'RENEWED_DOMAINS':deploy.HOST},check=True,timeout=3)
        self.assertEqual(calls.read_text().splitlines(),['nginx -t -q','systemctl reload nginx.service'])
        nginx.write_text('#!/bin/sh\nexit 1\n');result=subprocess.run(['/bin/sh',str(hook)],env={'PATH':'/usr/bin:/bin','RENEWED_LINEAGE':'/etc/letsencrypt/live/'+deploy.HOST,'RENEWED_DOMAINS':deploy.HOST},timeout=3)
        self.assertNotEqual(result.returncode,0);self.assertEqual(len(calls.read_text().splitlines()),2)

    def test_reviewed_failed_driver_resumes_only_after_exact_originals_are_restored(self):
        with patch.object(deploy,'units_and_runtime',side_effect=CheckFailed('fixture preflight')),self.assertRaises(CheckFailed):self.apply()
        previous=self.state();stamp=(deploy.STATE/'site.before').stat().st_mtime_ns
        with patch.object(deploy,'RECOVERABLE_DRIVER',DRIVER),contextlib.redirect_stdout(io.StringIO()):deploy.apply(REVISION,'7'*40,False,False)
        self.assertEqual(self.state()['driver_revision'],'7'*40)
        self.assertEqual(json.loads((deploy.STATE/('driver-'+DRIVER+'.json')).read_text()),previous)
        self.assertEqual((deploy.STATE/'site.before').stat().st_mtime_ns,stamp);self.preserved()
    def test_driver_transition_cannot_adopt_verified_or_changed_failed_resources(self):
        self.apply()
        with patch.object(deploy,'RECOVERABLE_DRIVER',DRIVER),self.assertRaisesRegex(CheckFailed,'another_https_deployment_recorded'):
            with contextlib.redirect_stdout(io.StringIO()):deploy.apply(REVISION,'7'*40,False,False)
        self.apply(True);deploy.SITE.write_bytes(b'Unknown concurrent change')
        with patch.object(deploy,'RECOVERABLE_DRIVER',DRIVER),self.assertRaisesRegex(CheckFailed,'not_rolled_back'):
            with contextlib.redirect_stdout(io.StringIO()):deploy.apply(REVISION,'7'*40,False,False)
        self.assertEqual(deploy.SITE.read_bytes(),b'Unknown concurrent change');self.preserved()

class BoundedDeploymentCommandTests(unittest.TestCase):
    def test_subprocess_failure_never_reflects_diagnostics_and_log_is_private(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            logfile=Path(temporary)/'diagnostic'
            with patch.object(deploy,'DIAGNOSTIC',logfile),self.assertRaises(CheckFailed) as raised:
                deploy.command([sys.executable,'-c','import sys;sys.stderr.write("fixture-sensitive-marker");raise SystemExit(3)'])
            self.assertNotIn('fixture-sensitive-marker',str(raised.exception));self.assertEqual(logfile.stat().st_mode&0o777,0o600)
            self.assertIn(b'fixture-sensitive-marker',logfile.read_bytes())
    def test_timeout_reaps_only_the_owned_command_group(self):
        import subprocess,time
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'child-pid'
            code='import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(20)'
            with patch.object(deploy,'DIAGNOSTIC',None),self.assertRaises(subprocess.TimeoutExpired):
                deploy.command([sys.executable,'-c',code,str(path)],timeout=.3)
            pid=int(path.read_text());status=Path('/proc')/str(pid)/'status'
            if status.exists():self.assertIn('Z',status.read_text().split('State:',1)[1].splitlines()[0])

class OwnLogPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.access=self.root/'resmgrcheck-access.log';self.error=self.root/'resmgrcheck-error.log'
        self.access.write_bytes(b'Preserve access fixture bytes');self.error.write_bytes(b'Preserve error fixture bytes')
        self.access.chmod(0o600);self.error.chmod(0o644)
    def test_tightens_only_own_logs_without_reading_truncating_chowning_or_broadening_0600(self):
        before={p:(p.read_bytes(),p.stat().st_uid,p.stat().st_gid,p.stat().st_ino,p.stat().st_mtime_ns) for p in [self.access,self.error]}
        with patch.object(deploy,'LOGS',self.root),patch.object(Path,'read_bytes',side_effect=AssertionError('No log-content read')):
            result=deploy.ensure_logs();deploy.ensure_logs()
        self.assertEqual(self.access.stat().st_mode&0o777,0o600);self.assertEqual(self.error.stat().st_mode&0o777,0o640)
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_uid,p.stat().st_gid,p.stat().st_ino,p.stat().st_mtime_ns) for p in before})
        self.assertTrue(result[self.error.name]['permissions_tightened']);self.assertFalse(result[self.access.name]['permissions_tightened'])
    def test_named_acl_and_world_writable_files_are_refused_without_permission_repair(self):
        import struct
        acl=struct.pack('<I',2)+b''.join(struct.pack('<HHI',tag,4,0xffffffff) for tag in [1,4,16,32])
        with patch.object(deploy,'LOGS',self.root),patch.object(deploy.os,'getxattr',return_value=acl),self.assertRaisesRegex(CheckFailed,'ACL_requires_review'):deploy.ensure_logs()
        self.assertEqual(self.error.stat().st_mode&0o777,0o644)
        self.error.chmod(0o666)
        with patch.object(deploy,'LOGS',self.root),self.assertRaisesRegex(CheckFailed,'own_log_protection'):deploy.ensure_logs()
        self.assertEqual(self.error.stat().st_mode&0o777,0o666)
    def test_symlink_and_hardlink_logs_never_modify_an_unknown_target(self):
        other=self.root/'other';other.write_bytes(b'Other application fixture');other.chmod(0o644)
        self.error.unlink();self.error.symlink_to(other)
        with patch.object(deploy,'LOGS',self.root),self.assertRaises(OSError):deploy.ensure_logs()
        self.error.unlink();os.link(other,self.error)
        with patch.object(deploy,'LOGS',self.root),self.assertRaisesRegex(CheckFailed,'own_log_protection'):deploy.ensure_logs()
        self.assertEqual(other.stat().st_mode&0o777,0o644);self.assertEqual(other.read_bytes(),b'Other application fixture')
