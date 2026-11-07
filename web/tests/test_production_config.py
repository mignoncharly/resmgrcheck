"""Real settings imports and role-denial checks; no public deployment claimed."""
import io,json,logging,os,subprocess,sys,tempfile
from unittest.mock import patch
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase,override_settings

class ProductionConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.key=self.root/'key';self.key.write_text('private-test-key-'+'x'*60);self.key.chmod(0o600)
        self.environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','RMC_WEB_ENV':'production',
            'RMC_WEB_SECRET_KEY_FILE':str(self.key),'RMC_WEB_MFA_KEY_FILE':str(self.key),
            'RMC_WEB_DB_HOST':'/run/resmgrcheck-db','RMC_WEB_DB_PORT':'5448',
            'RMC_WEB_STATIC_ROOT':str(self.root/'static'),'RMC_WEB_ARTIFACT_ROOT':str(self.root/'evidence'),'RMC_WEB_PRIVATE_ROOT':str(self.root/'private')}
    def load(self,**extra):
        return subprocess.run([sys.executable,'-c',"from resmgr_web import settings as s; print(s.SESSION_COOKIE_SECURE,s.CSRF_COOKIE_SECURE,s.SECURE_SSL_REDIRECT,s.SECURE_HSTS_SECONDS)"],cwd=settings.BASE_DIR,env={**self.environment,**extra},stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
    def test_production_secure_cookie_https_defaults_and_valid_private_files(self):
        result=self.load();self.assertEqual(result.returncode,0);self.assertEqual(result.stdout.strip(),b'True True True 31536000')
    def test_production_refuses_exposed_keys_symlinks_env_values_and_bad_hosts(self):
        self.key.chmod(0o644);self.assertNotEqual(self.load().returncode,0);self.key.chmod(0o600)
        link=self.root/'link';link.symlink_to(self.key)
        for options in [{'RMC_WEB_SECRET_KEY_FILE':str(link)},{'RMC_WEB_SECRET_KEY_FILE':'','RMC_WEB_SECRET_KEY':'never-log-this-test-only-key'},
            {'RMC_WEB_ALLOWED_HOSTS':'*'},{'RMC_WEB_CSRF_ORIGINS':'https://unapproved.example'}, {'RMC_WEB_ARTIFACT_ROOT':'relative'}, {'RMC_WEB_DB_HOST':'127.0.0.1'}]:
            self.assertNotEqual(self.load(**options).returncode,0)
    def test_http_role_refuses_executor_and_provider_configuration(self):
        for options in [{'RMC_WEB_EXECUTOR_REGISTRY':'/private/registry.json'},{'RMC_WEB_AI_CONFIG':'/private/provider.json'}]:self.assertNotEqual(self.load(**options).returncode,0)
    def test_executor_requires_registry_and_ai_role_cannot_receive_it(self):
        self.assertNotEqual(self.load(RMC_WEB_ROLE='executor').returncode,0)
        self.assertEqual(self.load(RMC_WEB_ROLE='executor',RMC_WEB_EXECUTOR_REGISTRY='/private/registry.json',RMC_WEB_MFA_KEY_FILE='').returncode,0)
        self.assertNotEqual(self.load(RMC_WEB_ROLE='ai',RMC_WEB_EXECUTOR_REGISTRY='/private/registry.json').returncode,0)
    def test_http_role_cannot_start_native_or_ai_dispatchers(self):
        with override_settings(ENVIRONMENT='production',SERVICE_ROLE='web'):
            for command in ['dispatch','dispatch_ai']:
                with self.assertRaises(CommandError):call_command(command,once=True)
    def test_private_executor_role_cannot_expose_wsgi(self):
        environment={**self.environment,'RMC_WEB_ROLE':'executor','RMC_WEB_EXECUTOR_REGISTRY':'/private/registry.json'}
        result=subprocess.run([sys.executable,'-c','import resmgr_web.wsgi'],cwd=settings.BASE_DIR,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertIn(b'Only the web service role may expose WSGI',result.stderr)
    def test_untrusted_url_or_exception_cannot_log_raw_access_codes(self):
        from control.logging import PrivateFormatter
        raw='rmc_'+'0'*32+'_'+'a'*42+'-';output=io.StringIO();handler=logging.StreamHandler(output);handler.setFormatter(PrivateFormatter())
        logger=logging.Logger('isolated-redaction-test');logger.addHandler(handler)
        try:raise ValueError('An attacker-controlled path /'+raw+'/')
        except ValueError:logger.exception('Request path %s',raw)
        self.assertNotIn(raw,output.getvalue());self.assertIn('[REDACTED_ACCESS_CODE]',output.getvalue())
    def test_production_review_does_not_waive_an_unexpected_deployment_warning(self):
        from django.core.checks import Warning
        with override_settings(ENVIRONMENT='production'),patch('control.management.commands.production_check.run_checks',return_value=[Warning('Host-only test warning',id='security.NEW')]),self.assertRaises(CommandError):
            call_command('production_check',stdout=io.StringIO())
    def test_private_preparation_plan_cannot_expose_public_services(self):
        script=settings.BASE_DIR/'ops/production/prepare.py'
        result=subprocess.run([sys.executable,str(script),'--revision','0'*40],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertEqual(result.returncode,0);plan=json.loads(result.stdout);self.assertFalse(plan['public_exposure']);self.assertTrue(plan['root_required_to_apply'])
    def test_evidence_sharing_preserves_bytes_and_native_readonly_state(self):
        from control.storage import share_verified_file
        from control.engine import PolicyError
        path=self.root/'evidence';path.write_bytes(b'exact native evidence bytes');path.chmod(0o400)
        share_verified_file(path,os.getgid());self.assertEqual(path.stat().st_mode&0o777,0o440);self.assertEqual(path.read_bytes(),b'exact native evidence bytes')
        link=self.root/'evidence-link';os.link(path,link)
        with self.assertRaises(PolicyError):share_verified_file(path,os.getgid())
    def test_installation_public_permissions_do_not_follow_links_to_private_state(self):
        import importlib.util
        script=settings.BASE_DIR/'ops/production/prepare.py';spec=importlib.util.spec_from_file_location('private_preparation_test',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        public=self.root/'public';public.mkdir(mode=0o700);code=public/'app.py';code.write_text('# public code');code.chmod(0o600)
        private=self.root/'protected';private.mkdir(mode=0o700);credential=private/'credential';credential.write_text('synthetic-protected-value');credential.chmod(0o600)
        (public/'private-state').symlink_to(private,target_is_directory=True);(public/'private-file').symlink_to(credential)
        module.public_code_permissions(public)
        self.assertEqual(code.stat().st_mode&0o777,0o644);self.assertEqual(private.stat().st_mode&0o777,0o700);self.assertEqual(credential.stat().st_mode&0o777,0o600)
