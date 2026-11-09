"""OPT-IN actual browser/TLS/outbound-runner/QNX qualification, never production.

Explicit label only; no test_* discovery. Reuses the approved local lab and new
immutable before/good builds. No separate-customer-host or public HTTPS claim.
"""
import base64,hashlib,io,json,os,secrets,ssl,subprocess,sys,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from wsgiref.simple_server import make_server,WSGIRequestHandler
from django.conf import settings
from django.test import TransactionTestCase,override_settings
from django.core.handlers.wsgi import WSGIHandler
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.db import connection,connections
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP,generate_totp_secret,hotp_value,format_hotp_value
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from control.models import User,Organization,Membership,Project,Target,CustomerRunner,BuildRelease,Run,RunnerJob,AuditEvent
from control import runner_ingest
from customer_runner.client import create
from customer_runner import protocol as wire
from resmgrcheck.workflow import inspect_execution,compare_executions
from control.engine import run_path
from .test_runner_tls import certificate

PASSWORD='Isolated qualification fixture password 792!'

class QuietHandler(WSGIRequestHandler):
    def log_message(self,*args):pass

class CustomerNativeQualification(TransactionTestCase):
    def setUp(self):
        if os.environ.get('RMC_CUSTOMER_NATIVE_QUALIFY')!='approved-local-lab':self.skipTest('Explicit local-lab qualification flag required')
        self.assertEqual(settings.ENVIRONMENT,'test');self.assertEqual(connection.settings_dict['NAME'],'test_resmgrcheck_web')
        self.base=settings.REPO_ROOT/'.local/customer-qualification'
        self.out=self.base/('actual-'+uuid.uuid4().hex[:12]);self.out.mkdir(mode=0o700)
        certificate(self.out);self.seed=secrets.token_hex(32);self.fault={'remaining':0,'observed':0}
        self.stage='setup';self.views=[];self.scans=[];self.records=[];self.result={'passed':False}
        self.server=make_server('127.0.0.1',0,self.application,handler_class=QuietHandler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.out/'ca.pem',self.out/'tls-key');self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.origin='https://localhost:'+str(self.server.server_port)
        self.overrides=override_settings(RUNNER_ENABLED=True,RUNNER_SIGNING_KEY=self.seed,RUNNER_ORIGIN=self.origin,
            ALLOWED_HOSTS=['localhost'],CSRF_TRUSTED_ORIGINS=[self.origin],SESSION_COOKIE_SECURE=True,CSRF_COOKIE_SECURE=True,
            MEDIA_ROOT=self.out/'evidence',PRIVATE_ROOT=self.out/'private')
        self.overrides.enable();self.addCleanup(self.overrides.disable)
        self.handler=StaticFilesHandler(WSGIHandler())
        self.thread=threading.Thread(target=self.serve,daemon=True);self.thread.start();self.addCleanup(self.stop)
        self.user=User.objects.create_user('customer-qualification-'+uuid.uuid4().hex[:8],PASSWORD)
        self.org=Organization.objects.create(name='Actual local runner qualification')
        Membership.objects.create(organization=self.org,user=self.user,role='owner')
        self.project=Project.objects.create(organization=self.org,name='Owned mailbox lab',created_by=self.user)
        self.secret=generate_totp_secret();TOTP.activate(self.user,self.secret)
        self.axe=(settings.REPO_ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text()
        self.database=ThreadPoolExecutor(max_workers=1)
        self.addCleanup(self.database.shutdown,wait=True)
        # Reuse the already installed browser tooling, without production deps.
        for site in (settings.REPO_ROOT/'.local/browser-test/lib').glob('python*/site-packages'):
            if str(site) not in sys.path:sys.path.append(str(site))

    def application(self,environ,start_response):
        environ['wsgi.url_scheme']='https';environ['HTTPS']='on'
        if self.fault['remaining'] and environ.get('PATH_INFO')=='/runner/v1/exchange/':
            length=int(environ.get('CONTENT_LENGTH','0'))
            raw=environ['wsgi.input'].read(min(length,wire.MAX_MESSAGE+1));environ['wsgi.input']=io.BytesIO(raw)
            try:operation=wire.parse(raw)['payload']['body']['operation']
            except (KeyError,ValueError):operation=None
            if operation=='chunk':
                self.fault['remaining']-=1;self.fault['observed']+=1
                body=b'{"error":"isolated network interruption fixture"}'
                start_response('503 Service Unavailable',[('Content-Type','application/json'),('Content-Length',str(len(body)))])
                return [body]
        return self.handler(environ,start_response)

    def serve(self):
        try:self.server.serve_forever(poll_interval=.05)
        finally:connections.close_all()

    def db(self,function):
        # Playwright drives an event loop in its sync caller. Keep ORM/ingestion
        # in an owned synchronous thread, without waiving Django async safety.
        def invoke():
            try:return function()
            finally:connections.close_all()
        return self.database.submit(invoke).result(timeout=60)

    def stop(self):
        self.server.shutdown();self.thread.join(timeout=5);self.server.server_close()
        record={'kind':'actual-local-browser-tls-outbound-runner-qnx-qualification','last_stage':self.stage,**self.result,
            'views':self.views,'accessibility':self.scans,'native_runs':self.records,
            'network_faults_observed':self.fault['observed'],'production_changed':False,'public_https_qualified':False,
            'separate_customer_host_qualified':False,'scope':self.result.get('scope','Real browser/locally trusted TLS and independent runner process against the approved reused local QNX lab. Dedicated disposable PostgreSQL test DB, UID1000 staging, no production keys/roles/config.')}
        (self.out/'qualification.json').write_text(json.dumps(record,indent=2)+'\n')
        self.assertFalse(self.thread.is_alive())

    def visit(self,page,path,label,scan=False):
        response=page.goto(self.origin+path,wait_until='networkidle');self.assertEqual(response.status,200)
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label+' horizontal overflow')
        self.views.append({'page':label,'width':page.viewport_size['width'],'status':response.status})
        if scan:
            page.evaluate(self.axe)
            issues=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
            self.scans.append({'page':label,'violations':issues});self.assertFalse([v for v in issues if v['impact'] in {'critical','serious'}],label+' accessibility')

    def agent(self,operation,expected=0):
        args=[sys.executable,'-B','-m','customer_runner',operation,'--config',str(self.out/'runner.json'),
            '--state',str(self.out/'runner-state'),'--ca-file',str(self.out/'ca.pem')]
        if operation=='enroll':args+=['--enrollment-file',str(self.out/'enrollment')]
        else:args+=['--once']
        process=subprocess.run(args,cwd=settings.REPO_ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
        # Outputs contain public IDs/status only; raw errors stay protected locally.
        create(self.out/(operation+'-'+uuid.uuid4().hex[:8]+'.log'),process.stdout+process.stderr)
        self.assertEqual(process.returncode,expected,'customer runner operation failed; protected diagnostics retained')
        return json.loads(process.stdout) if expected==0 else None

    def queue(self,page,profile,build):
        self.visit(page,'/app/projects/'+str(self.project.pk)+'/runs/new/','new '+profile)
        page.locator('[name=target]').select_option(str(self.target.pk));page.locator('[name=build]').select_option(str(build.pk))
        page.locator('[name=profile]').select_option(profile);page.locator('[name=suite]').select_option('profile')
        page.locator('[name=fixture_mode]').select_option('fixed');page.get_by_role('button',name='Preview test request').click()
        page.get_by_role('button',name='Confirm and queue',exact=True).click();page.wait_for_url('**/app/runs/*/')
        identifier=urlsplit(page.url).path.rstrip('/').split('/')[-1]
        return self.db(lambda:Run.objects.select_related('build','project__organization','target','original__project').get(pk=identifier))

    def collect(self,run,expected):
        self.assertEqual(self.agent('work')['state'],'received')
        self.assertTrue(self.db(runner_ingest.ingest_one))
        run=self.db(lambda:Run.objects.select_related('build','project__organization','target','original__project').get(pk=run.pk));self.assertEqual(run.state,'completed')
        self.assertTrue(run.target_cleanup_verified);request,summary,_=inspect_execution(run_path(run))
        self.assertEqual(request.data['run_id'],run.native_run_id)
        self.assertEqual({row['verdict'] for row in summary['cases']},{expected})
        self.records.append({'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'profile':run.profile,
            'operation':run.operation,'source_revision':run.build.manifest['build']['source_revision'],
            'deployment_id':run.build.manifest['deployment_id'],'verdicts':[row['verdict'] for row in summary['cases']],
            'cleanup_verified':run.target_cleanup_verified,'path':str(run_path(run).relative_to(self.out)),
            'native_executed':True})
        return run

    def test_actual_customer_workflow(self):
        from playwright.sync_api import sync_playwright,Error as BrowserError
        try:
            with sync_playwright() as driver:
                cert=x509.load_pem_x509_certificate((self.out/'ca.pem').read_bytes())
                pin=base64.b64encode(hashlib.sha256(cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).digest()).decode()
                executable=Path('/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
                self.assertTrue(executable.is_file(),'Existing qualified headless browser is unavailable')
                browser=driver.chromium.launch(executable_path=str(executable),args=['--ignore-certificate-errors-spki-list='+pin])
                context=browser.new_context(viewport={'width':1440,'height':900});admin=context.new_page()
                self.stage='public landing and real administrator MFA'
                self.visit(admin,'/','public landing',True);self.visit(admin,'/demo/','recorded demo',True)
                self.visit(admin,'/administrator/login/','administrator login')
                admin.locator('[name=login]').fill(self.user.username);admin.locator('[name=password]').fill(PASSWORD)
                admin.get_by_role('button',name='Sign in as administrator').click();admin.wait_for_url('**/administrator/2fa/authenticate/**')
                for attempt in range(3):
                    code=format_hotp_value(hotp_value(self.secret,int(time.time())//30))
                    admin.locator('[name=code]').fill(code);admin.get_by_role('button',name='Sign In',exact=True).click();admin.wait_for_timeout(150)
                    if urlsplit(admin.url).path=='/app/':break
                    self.assertLess(attempt,2,'fixture MFA did not authenticate');time.sleep(min(30,30-time.time()%30+.1))
                self.assertEqual(urlsplit(admin.url).path,'/app/')
                self.stage='browser enrollment and customer-local discovery'
                targets='/app/projects/'+str(self.project.pk)+'/targets/'
                self.visit(admin,targets,'customer targets',True)
                admin.locator('[name=name]').fill('Explicitly owned local QNX mailbox lab')
                admin.get_by_role('button',name='Create runner enrollment').click()
                token=admin.locator('#enrollment-token').input_value();create(self.out/'enrollment',token.encode());token=None
                self.target=self.db(lambda:Target.objects.get(project=self.project,kind='customer-runner'))
                manifests={}
                for label in ['before','good']:
                    path=self.base/label/'build/qnx-x86_64/manifest.json';value=json.loads(path.read_text());manifests[value['deployment_id']]=str(path)
                cfg={'origin':self.origin,'server_public_key':wire.public(self.seed),'target_id':str(self.target.pk),
                    'project_id':str(self.project.pk),'organization_id':str(self.org.pk),'engine_root':str(self.base/'good'),
                    'target_config':str(self.base/'customer-target.json'),'alias':'customer-lab','manifests':manifests,
                    'attachment':'managed-fixture','allowed_modes':['corrected']}
                create(self.out/'runner.json',wire.canonical(cfg));self.agent('enroll')
                detail='/app/projects/'+str(self.project.pk)+'/runners/'+str(self.target.pk)+'/'
                self.visit(admin,detail,'runner pending approval',True)
                admin.get_by_role('button',name='Approve this exact runner inventory').click()
                self.assertTrue(self.db(lambda:CustomerRunner.objects.get(pk=self.target.pk).approved_at))
                for label in ['before','good']:
                    self.visit(admin,targets+str(self.target.pk)+'/builds/import/','import '+label+' manifest')
                    admin.locator('[name=label]').fill('Qualified '+label+' candidate')
                    admin.locator('[name=manifest]').set_input_files(str(self.base/label/'build/qnx-x86_64/manifest.json'))
                    admin.get_by_role('button',name='Submit manifest for approval').click()
                    card=admin.locator('.list-card').filter(has_text='Qualified '+label+' candidate')
                    card.get_by_role('button',name='Approve this exact build').click()
                self.before=self.db(lambda:BuildRelease.objects.get(target=self.target,label='Qualified before candidate'))
                self.good=self.db(lambda:BuildRelease.objects.get(target=self.target,label='Qualified good candidate'))
                self.assertTrue(self.before.approved and self.good.approved)
                self.stage='actual code issue and developer redemption'
                codes='/administrator/organizations/'+str(self.org.pk)+'/codes/'
                self.visit(admin,codes,'issue customer access code')
                for name,value in [('description','Actual local QNX customer qualification'),('max_sessions','2'),('max_redemptions','2')]:admin.locator('[name='+name+']').fill(value)
                admin.locator('[name=projects]').select_option(str(self.project.pk));admin.locator('[name=targets]').select_option(str(self.target.pk))
                for name in ['all_evidence','can_download','allow_live']:admin.locator('[name='+name+']').check()
                admin.get_by_role('button',name='Generate access code').click();raw=admin.locator('#new-access-code').inner_text().strip()
                code_id=str(uuid.UUID(hex=raw.split('_')[1]));self.visit(admin,'/administrator/codes/'+code_id+'/','code usage and revocation',True)
                developer=browser.new_context(viewport={'width':1440,'height':900});page=developer.new_page()
                self.visit(page,'/access/','developer code entry');page.locator('[name=code]').fill(raw)
                page.get_by_role('button',name='Open permitted workspace').click();page.wait_for_url('**/app/')
                cookie=next(c for c in developer.cookies() if c['name']=='resmgrcheck_session');self.assertTrue(cookie['secure'] and cookie['httpOnly'])
                self.stage='real mailbox source-defect run through browser and outbound runner'
                before=self.collect(self.queue(page,'mailbox',self.before),'FAIL')
                self.visit(page,'/app/runs/'+str(before.pk)+'/','actual mailbox failure',True)
                self.stage='actual corrected replay with a real upload connection interruption'
                page.get_by_role('link',name='Replay with candidate').click();page.locator('[name=build]').select_option(str(self.good.pk))
                page.get_by_role('button',name='Confirm and queue saved-input replay').click();page.wait_for_url('**/app/runs/*/')
                identifier=urlsplit(page.url).path.rstrip('/').split('/')[-1]
                after=self.db(lambda:Run.objects.select_related('build','project__organization','target','original__project').get(pk=identifier));identity=after.native_run_id
                self.fault['remaining']=1;self.agent('work',expected=1)
                grant=self.db(lambda:RunnerJob.objects.get(pk=after.pk).launch_granted_at)
                self.assertEqual(self.fault['observed'],1);self.assertEqual(self.db(lambda:Run.objects.get(pk=after.pk).native_run_id),identity)
                after=self.collect(after,'PASS');self.assertEqual(self.db(lambda:RunnerJob.objects.get(pk=after.pk).launch_granted_at),grant)
                self.assertEqual(self.db(lambda:AuditEvent.objects.filter(action='runner.launch_granted',object_id=str(after.pk)).count()),1)
                comparison=compare_executions(run_path(before),run_path(after));self.assertEqual(comparison['label'],'fixed')
                self.visit(page,'/app/compare/?before='+str(before.pk)+'&after='+str(after.pk),'actual identified source comparison',True)
                self.stage='original sensor and job regressions through the same outbound route'
                sensor=self.collect(self.queue(page,'sensor',self.good),'PASS')
                job=self.collect(self.queue(page,'job',self.good),'PASS')
                self.stage='desktop/mobile evidence authorization and accessibility'
                self.visit(page,'/app/runs/'+str(after.pk)+'/','actual mailbox corrected replay',True)
                # Use Chromium's explicitly pinned test certificate for the real
                # download, rather than a separate API client's CA trust store.
                with page.expect_download() as download:
                    page.get_by_role('link',name='Download verified offline ZIP').click()
                self.assertIsNone(download.value.failure())
                with open(download.value.path(),'rb') as stream:self.assertEqual(stream.read(2),b'PK')
                for width in [390,768]:
                    page.set_viewport_size({'width':width,'height':900})
                    for path,label in [('/app/projects/'+str(self.project.pk)+'/','customer project'),('/app/runs/'+str(after.pk)+'/','corrected run'),('/app/compare/?before='+str(before.pk)+'&after='+str(after.pk),'source comparison')]:
                        self.visit(page,path,label+' mobile',width==390)
                mobile=browser.new_context(viewport={'width':390,'height':900},java_script_enabled=False);mobile_page=mobile.new_page()
                self.visit(mobile_page,'/access/','no-JS mobile code entry');mobile_page.locator('[name=code]').fill(raw)
                mobile_page.get_by_role('button',name='Open permitted workspace').click();mobile_page.wait_for_url('**/app/')
                self.visit(mobile_page,'/app/runs/'+str(after.pk)+'/','no-JS native replay')
                foreign=self.db(lambda:Organization.objects.create(name='Unrelated tenant fixture'))
                foreign_project=self.db(lambda:Project.objects.create(organization=foreign,name='Denied',created_by=self.user))
                self.assertEqual(page.goto(self.origin+'/app/projects/'+str(foreign_project.pk)+'/').status,404)
                self.assertEqual(page.goto(self.origin+detail).status,404)
                self.stage='revocation blocks active sessions and pending unauthorized native work'
                pending=self.queue(page,'mailbox',self.good)
                self.visit(admin,'/administrator/codes/'+code_id+'/','review actual code usage')
                admin.get_by_role('button',name='Revoke this code immediately').click()
                self.agent('work');pending=self.db(lambda:Run.objects.get(pk=pending.pk));self.assertEqual(pending.state,'rejected')
                page.goto(self.origin+'/app/');mobile_page.goto(self.origin+'/app/')
                self.assertEqual(urlsplit(page.url).path,'/access/');self.assertEqual(urlsplit(mobile_page.url).path,'/access/')
                self.result={'passed':True,'administrator_password_totp':True,'code_issued_redeemed_revoked':True,
                    'pending_job_denied_after_revocation':True,'immutable_source_comparison':comparison['label'],
                    'reconnection_preserved_native_id':identity,'reconnection_launch_grants':1,'evidence_download':True,
                    'cross_tenant_denial':True,'desktop_mobile_no_js':True,'cookie_secure_httponly':True,
                    'native_cases':len(self.records),'AI_provider_calls':0,'AI':'disabled','browser_version':browser.version}
                raw=None;browser.close();self.stage='complete'
        except BrowserError as error:
            create(self.out/'browser-error.log',str(error).encode())
            raise AssertionError('Browser qualification failed; protected local diagnostics and safe stage metadata retained') from None
