"""Actual unprivileged nginx1.24/TLS/Unix proxy. Synthetic backend, not production."""
import hashlib,http.server,json,os,signal,socket,socketserver,ssl,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
OPS=Path(__file__).resolve().parents[1]/'ops/production';sys.path.insert(0,str(OPS))
from https_config import HOST,http_config,site_config
from https_checks import Client,checks
import deploy_https as deploy

class UnixServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.server.observed.append(dict(self.headers))
        status=200;headers={};body=b'<!doctype html><html lang="en"><title>Isolated fixture</title><h1>Fixture</h1></html>'
        if self.path=='/readyz/':body=b'{"status":"ready"}';headers['Content-Type']='application/json'
        elif self.path in {'/access/','/administrator/login/'}:
            headers.update({'Set-Cookie':'resmgrcheck_csrf=fixture-public-token; Path=/; Secure; HttpOnly; SameSite=Lax','Cache-Control':'no-store'})
        elif self.path=='/app/' or self.path.startswith('/api/projects/'):
            status=302;headers={'Location':'/access/','Cache-Control':'no-cache'}
        elif self.path=='/custom-evidence/':
            headers={'Content-Security-Policy':"sandbox allow-same-origin; default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'; form-action 'none'",'X-Frame-Options':'SAMEORIGIN','Cache-Control':'no-store'}
        elif self.path!='/':status=404
        self.send_response(status)
        for name,value in headers.items():self.send_header(name,value)
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        self.send_response(403);self.send_header('Content-Length','0');self.end_headers()

def free_port():
    with socket.socket() as connection:connection.bind(('127.0.0.1',0));return connection.getsockname()[1]

class NginxFixture:
    def __init__(self,root,backend,*,http_extra='',master=False):
        self.root=root;self.http_port=free_port();self.https_port=free_port();self.backend=backend
        self.cert=root/'certificate.pem';self.key=root/'private.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(self.key),'-out',str(self.cert),
            '-days','2','-subj','/CN='+HOST,'-addext','subjectAltName=DNS:'+HOST+',DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        self.key.chmod(0o600);self.cert.chmod(0o644)
        self.static=root/'static';(self.static/'control').mkdir(parents=True);self.css=b'body { color: #123; }\n';(self.static/'control/app.css').write_bytes(self.css)
        self.acme=root/'acme/.well-known/acme-challenge';self.acme.mkdir(parents=True,mode=0o755)
        site=site_config('5'*40).replace('listen 80;','listen 127.0.0.1:'+str(self.http_port)+';').replace('listen [::]:80;','')
        site=site.replace('listen 443 ssl http2;','listen 127.0.0.1:'+str(self.https_port)+' ssl http2;').replace('listen [::]:443 ssl http2;','')
        site=site.replace('/etc/letsencrypt/live/'+HOST+'/fullchain.pem',str(self.cert)).replace('/etc/letsencrypt/live/'+HOST+'/privkey.pem',str(self.key))
        site=site.replace('/var/lib/resmgrcheck/static/'+'5'*40,str(self.static)).replace('/run/resmgrcheck-web/application.sock',str(backend))
        site=site.replace('/var/www/resmgrcheck-acme',str(root/'acme')).replace('/var/log/nginx/resmgrcheck-access.log',str(root/'access.log')).replace('/var/log/nginx/resmgrcheck-error.log',str(root/'error.log'))
        self.site=site
        self.configuration=root/'nginx.conf';self.configuration.write_text('daemon off; master_process '+('on' if master else 'off')+';\npid '+str(root/'nginx.pid')+';\nerror_log '+str(root/'master.log')+' crit;\nevents { worker_connections 128; }\nhttp {\ninclude /etc/nginx/mime.types;\n'+
            '\n'.join(key+' '+str(root/name)+';' for key,name in [('client_body_temp_path','body'),('proxy_temp_path','proxy'),('fastcgi_temp_path','fastcgi'),('uwsgi_temp_path','uwsgi'),('scgi_temp_path','scgi')])+ '\n'+http_config()+http_extra+'\n'+site+'\n}\n')
        self.process=None
    def start(self):
        subprocess.run(['/usr/sbin/nginx','-t','-p',str(self.root)+'/', '-c',str(self.configuration)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        self.log=(self.root/'launcher.log').open('wb');self.process=subprocess.Popen(['/usr/sbin/nginx','-p',str(self.root)+'/', '-c',str(self.configuration)],stdout=self.log,stderr=self.log)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                with socket.create_connection(('127.0.0.1',self.https_port),.1):return
            except OSError:time.sleep(.03)
        raise AssertionError('Isolated nginx did not start')
    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
        if hasattr(self,'log'):self.log.close()

class ActualNginxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rmc-nginx-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.backend=self.root/'backend.sock';self.server=UnixServer(str(self.backend),Handler);self.server.observed=[]
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.fixture=NginxFixture(self.root,self.backend,http_extra='set_real_ip_from 127.0.0.1; real_ip_header X-Forwarded-For;');self.addCleanup(self.fixture.stop);self.fixture.start()
        self.client=Client('127.0.0.1',self.fixture.https_port,self.fixture.http_port,str(self.fixture.cert))
    def test_actual_tls_unix_proxy_headers_static_acme_and_post_rate_limits(self):
        results=checks(self.client,hashlib.sha256(self.fixture.css).hexdigest());self.assertEqual(len(results),14)
        with patch.object(deploy,'ACME',self.fixture.acme):deploy.acme_probe(self.client)
        with patch.object(deploy,'LOGS',self.root):
            # Fixture log filenames differ; use the same exact confidentiality logic.
            marker='rmc-confidential-probe-test';status,_,_=self.client.request('/'+marker+'?credential='+marker);self.assertEqual(status,404)
            self.assertNotIn(marker,(self.root/'access.log').read_text());self.assertNotIn(marker,(self.root/'error.log').read_text())
    def test_app_sandbox_policy_and_identity_headers_survive_proxy(self):
        status,headers,_=self.client.request('/custom-evidence/',headers={'X-Real-IP':'192.0.2.7','X-Forwarded-For':'192.0.2.7','Forwarded':'proto=http','X-Forwarded-Proto':'http'})
        self.assertEqual(status,200);self.assertEqual(headers['x-frame-options'],'SAMEORIGIN');self.assertIn("style-src 'unsafe-inline'",headers['content-security-policy']);self.assertNotIn("script-src 'self'",headers['content-security-policy'])
        observed={key.lower():value for key,value in self.server.observed[-1].items()}
        self.assertEqual(observed['host'],HOST);self.assertEqual(observed['x-real-ip'],'127.0.0.1');self.assertEqual(observed['x-forwarded-proto'],'https');self.assertNotIn('forwarded',observed);self.assertNotIn('x-forwarded-for',observed)
    def test_tls_cannot_be_bypassed_and_large_body_is_rejected_at_nginx(self):
        untrusted=Client('127.0.0.1',self.fixture.https_port,self.fixture.http_port)
        with self.assertRaises(ssl.SSLCertVerificationError):untrusted.request('/readyz/')
        status,headers,_=self.client.request('/access/','POST',body=b'x'*262145)
        self.assertEqual(status,413);self.assertEqual(headers['x-content-type-options'],'nosniff');self.assertIn('frame-ancestors',headers['content-security-policy'])

    def test_proxy_failure_keeps_security_headers_and_spoofed_forwarding_cannot_evade_rate_limit(self):
        statuses=[]
        for index in range(12):
            status,_,_=self.client.request('/administrator/login/','POST',b'invalid',{'X-Forwarded-For':'192.0.2.'+str(index+1)})
            statuses.append(status)
        self.assertIn(429,statuses)
        self.server.shutdown();self.server.server_close()
        status,headers,_=self.client.request('/readyz/')
        self.assertEqual(status,502)
        from https_checks import security
        security(headers,True)

class ActualGracefulReloadTests(unittest.TestCase):
    def test_queued_reload_can_serve_old_redirect_until_master_applies_original(self):
        with tempfile.TemporaryDirectory(prefix='rmc-reload-') as temporary:
            root=Path(temporary);fixture=NginxFixture(root,root/'unused.sock',master=True)
            try:
                fixture.start();client=Client('127.0.0.1',fixture.https_port,fixture.http_port,str(fixture.cert))
                self.assertEqual(client.request('/',secure=False)[0],308)
                original=(OPS/'nginx-bootstrap-site.conf').read_text().replace('listen 80;','listen 127.0.0.1:'+str(fixture.http_port)+';').replace('listen [::]:80;','')
                original=original.replace('/var/www/resmgrcheck-acme',str(root/'acme')).replace('/var/log/nginx/resmgrcheck-error.log',str(root/'error.log'))
                restored=fixture.configuration.read_text().replace(fixture.site,original).encode()
                # Stop only this owned master: workers keep serving. SIGHUP queues
                # successfully before the master processes/reconfigures workers.
                os.kill(fixture.process.pid,signal.SIGSTOP)
                fixture.configuration.write_bytes(restored);fixture.configuration.chmod(0o644)
                subprocess.run(['/usr/sbin/nginx','-t','-p',str(root)+'/', '-c',str(fixture.configuration)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
                os.kill(fixture.process.pid,signal.SIGHUP)
                self.assertEqual(client.request('/',secure=False)[0],308)
                (root/'site.before').write_bytes(restored);(root/'site.before').chmod(0o600)
                enabled=root/'enabled';enabled.symlink_to(fixture.configuration)
                state={'before':{'site':deploy.digest(restored)},'modes':{'site':0o644}}
                released=False
                real_sleep=time.sleep
                def wait_for_workers(delay):
                    nonlocal released
                    if not released:os.kill(fixture.process.pid,signal.SIGCONT);released=True
                    real_sleep(delay)
                with patch.object(deploy,'STATE',root),patch.object(deploy,'SITE',fixture.configuration),patch.object(deploy,'ENABLED',enabled),patch.object(deploy,'ACME',fixture.acme),patch.object(deploy.time,'sleep',side_effect=wait_for_workers):
                    deploy.verify_original_http(state,[('site',fixture.configuration,b'old HTTPS candidate',0o644)],client)
                self.assertEqual(state['rollback_http_observations'][0]['status'],308)
                self.assertEqual(state['rollback_http_observations'][-1]['status'],404)
                self.assertEqual(fixture.configuration.read_bytes(),restored)
            finally:
                if fixture.process and fixture.process.poll() is None:os.kill(fixture.process.pid,signal.SIGCONT)
                fixture.stop()
