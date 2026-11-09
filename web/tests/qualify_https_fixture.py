"""Opt-in complete browser-driver rehearsal: actual PG/Django/nginx/private TLS.

Not production/root/systemd/native/external acceptance. Creates only a disposable
DB and a synthetic private CA. Chrome pins that fixture CA; Node trusts that CA.
The production driver exposes no insecure-TLS option.
"""
import base64,hashlib,io,json,os,secrets,shutil,signal,socket,socketserver,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIServer,WSGIRequestHandler
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.test import TransactionTestCase,override_settings
from django.db import connection
from .test_https_nginx import NginxFixture
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import acceptance_operator

class UnixWSGI(socketserver.ThreadingMixIn,WSGIServer):
    address_family=socket.AF_UNIX;daemon_threads=True
    def server_bind(self):
        socketserver.TCPServer.server_bind(self);self.server_name='localhost';self.server_port=0;self.setup_environ()
class Handler(WSGIRequestHandler):
    def __init__(self,request,address,server):super().__init__(request,('127.0.0.1',0),server)
    def log_message(self,*args):pass
    def get_environ(self):
        environ=super().get_environ();environ['REMOTE_ADDR']='';return environ

class ActualGunicorn:
    def __init__(self,directory,backend,origin):
        self.root=directory;self.backend=backend;self.process=None
        (directory/'fixture_wsgi.py').write_text("""import django
django.setup()
from django.test.utils import override_settings
from django.core.wsgi import get_wsgi_application
policy=override_settings(ENVIRONMENT='production',SESSION_COOKIE_SECURE=True,CSRF_COOKIE_SECURE=True,
 ALLAUTH_TRUSTED_CLIENT_IP_HEADER='X-Real-IP',SECURE_SSL_REDIRECT=True,
 SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),CSRF_TRUSTED_ORIGINS=["""+repr(origin)+"""],
 ALLOWED_HOSTS=['localhost','qnx-resmgrcheck.gestionatech.de'])
policy.enable()
application=get_wsgi_application()
""")
    def start(self):
        repo=settings.REPO_ROOT;self.log=(self.root/'gunicorn.log').open('wb')
        environment={**os.environ,'RMC_WEB_ENV':'test','RMC_WEB_DB_NAME':connection.settings_dict['NAME'],
            'PYTHONPATH':os.pathsep.join(map(str,[self.root,repo/'web',repo])),'PYTHONDONTWRITEBYTECODE':'1'}
        self.process=subprocess.Popen([str(repo/'.local/web/venv/bin/python'),'-B','-m','gunicorn','fixture_wsgi:application',
            '--config',str(repo/'web/ops/gunicorn.conf.py'),'--bind','unix:'+str(self.backend)],
            cwd=self.root,env=environment,stdout=self.log,stderr=self.log,start_new_session=True)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise AssertionError('Isolated Gunicorn boot failed')
            try:
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as probe:probe.connect(str(self.backend));return
            except OSError:time.sleep(.05)
        raise AssertionError('Isolated Gunicorn socket unavailable')
    def stop(self):
        if self.process and self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGTERM)
            try:self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=3)
        if hasattr(self,'log'):self.log.close()

class HTTPSBrowserRehearsal(TransactionTestCase):
    def test_full_driver_through_verified_fixture_TLS(self):
        self.assertEqual(os.environ.get('RMC_HTTPS_BROWSER_REHEARSAL'),'isolated-only')
        root=settings.REPO_ROOT/'.local/web/evidence'/('https-rehearsal-'+secrets.token_hex(8));root.mkdir(mode=0o700)
        with tempfile.TemporaryDirectory(prefix='rmc-browser-nginx-') as temporary:
            directory=Path(temporary);backend=directory/'application.sock'
            fixture=NginxFixture(directory,backend)
            fixture.css=(settings.REPO_ROOT/'web/control/static/control/app.css').read_bytes();(fixture.static/'control/app.css').write_bytes(fixture.css)
            shutil.copyfile(settings.REPO_ROOT/'web/control/static/control/app.js',fixture.static/'control/app.js')
            origin='https://localhost:'+str(fixture.https_port)
            config=override_settings(ENVIRONMENT='production',SESSION_COOKIE_SECURE=True,CSRF_COOKIE_SECURE=True,
                ALLAUTH_TRUSTED_CLIENT_IP_HEADER='X-Real-IP',
                SECURE_SSL_REDIRECT=True,SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),
                CSRF_TRUSTED_ORIGINS=[origin],ALLOWED_HOSTS=['localhost','qnx-resmgrcheck.gestionatech.de'])
            config.enable();self.addCleanup(config.disable)
            server=ActualGunicorn(directory,backend,origin);self.addCleanup(server.stop);server.start();self.addCleanup(fixture.stop)
            fixture.start()
            # Use the *same* preflight as production against real Django, including
            # its anonymous no-cache redirect. Synthetic backend headers are not
            # sufficient evidence for the boundary policy.
            from django.test import Client as DjangoClient
            upstream=DjangoClient().get('/app/',HTTP_HOST='qnx-resmgrcheck.gestionatech.de',HTTP_X_FORWARDED_PROTO='https')
            self.assertEqual(upstream.status_code,302);self.assertEqual(upstream['Cache-Control'],'no-cache')
            from https_checks import Client,checks
            try:checks(Client('127.0.0.1',fixture.https_port,fixture.http_port,str(fixture.cert)),hashlib.sha256(fixture.css).hexdigest(),rate=False)
            except BaseException:
                server.log.flush();diagnostic=root/'fixture-gunicorn.log';shutil.copyfile(directory/'gunicorn.log',diagnostic);diagnostic.chmod(0o600)
                raise
            if os.environ.get('RMC_HTTPS_PREFLIGHT_ONLY')=='1':
                result={'passed':True,'scope':'exact deployment probes against real isolated Django/PostgreSQL/nginx/private TLS; no production or native execution',
                    'upstream_anonymous_redirect_cache_control':'no-cache','boundary_anonymous_redirect_cache_control':'no-store','probes':13}
                (root/'preflight-report.json').write_text(json.dumps(result,indent=2)+'\n')
                print(json.dumps({**result,'output':str(root)}));return
            credentials=acceptance_operator.bootstrap(uuid.uuid4(),{'status':'blocked','reason':'isolated rehearsal executes no native work'})
            certificate=subprocess.run(['openssl','x509','-in',str(fixture.cert),'-pubkey','-noout'],capture_output=True,check=True).stdout
            public=subprocess.run(['openssl','pkey','-pubin','-outform','DER'],input=certificate,capture_output=True,check=True).stdout
            pin=base64.b64encode(hashlib.sha256(public).digest()).decode()
            launcher=directory/'browser.py';launcher.write_text('''import json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from public_acceptance import Journey
from playwright.sync_api import BrowserType
original=BrowserType.launch
def launch(self,**kwargs):
 kwargs['args']=[*(kwargs.get('args') or []),'--ignore-certificate-errors-spki-list='+sys.argv[4]]
 return original(self,**kwargs)
credentials=json.loads(sys.stdin.buffer.read())
journey=Journey(sys.argv[2],Path(sys.argv[3]),credentials)
try:
 with patch.object(BrowserType,'launch',launch):journey.run()
except BaseException as error:
 journey.results.update(passed=False,failed_step=journey.step,error_class=type(error).__name__)
 journey.checkpoint()
 raise SystemExit(1) from None
''')
            try:
                process=subprocess.run([str(settings.REPO_ROOT/'.local/browser-test/bin/python'),'-B',str(launcher),
                    str(settings.REPO_ROOT/'web/ops/production'),origin,str(root),pin],input=json.dumps(credentials).encode(),
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600,env={**os.environ,'NODE_EXTRA_CA_CERTS':str(fixture.cert)})
                report=json.loads((root/'browser-report.json').read_text())
                self.assertEqual(process.returncode,0,{'failure_step':report.get('failed_step'),'error_class':report.get('error_class'),'output':str(root)})
                self.assertTrue(report['browser_passed']);self.assertFalse(report['passed']);self.assertEqual(report['native']['status'],'blocked')
                self.assertEqual(report['administrator_password'],'passed');self.assertEqual(report['access_codes'],'passed')
                report['scope']='Actual isolated Django/PG/Gunicorn26.2/Unix socket/nginx/TLS/browser rehearsal; fixture CA only; no production/root/systemd/native/external qualification'
                (root/'browser-report.json').write_text(json.dumps(report,indent=2)+'\n')
                self.assertTrue(all(not scan['violations'] for scan in report['accessibility']))
                print(json.dumps({'browser_rehearsal':'passed','views':len(report['views']),'scans':len(report['accessibility']),'output':str(root)}))
            finally:
                closed=acceptance_operator.close(credentials);(root/'cleanup.json').write_text(json.dumps(closed,indent=2)+'\n')
                fixture.stop();server.stop()
