"""OPT-IN presentation continuation using the already executed native evidence.

No QNX connection or new native work. Does not erase the earlier full-driver
failure or label these imports new live executions. Uses a fresh disposable DB.
"""
import hashlib,json,os,shutil,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
from cryptography import x509
from cryptography.hazmat.primitives import serialization
import base64
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Organization,Membership,Project,Target,BuildRelease,Run,Artifact
from control.storage import verify_inventory
from control.engine import run_path
from resmgrcheck.workflow import inspect_execution
from resmgrcheck.artifacts import inspect_bundle
from . import qualify_customer_native as native

class CustomerRecordedUIQualification(native.CustomerNativeQualification):
    def setUp(self):
        super().setUp()
        source=Path(os.environ['RMC_CUSTOMER_UI_EVIDENCE']).resolve()
        self.assertEqual(source.parent,self.base.resolve());self.assertTrue(source.name.startswith('actual-'))
        self.saved=json.loads((source/'qualification.json').read_text());self.assertEqual(len(self.saved['native_runs']),4)
        first=source/self.saved['native_runs'][0]['path'];marker=json.loads((first/'web-evidence-v2.json').read_text())
        self.org=Organization.objects.create(id=marker['organization_id'],name='Captured actual native UI continuation')
        Membership.objects.create(organization=self.org,user=self.user,role='owner')
        self.project=Project.objects.create(id=marker['project_id'],organization=self.org,name='Recorded qualified QNX results',created_by=self.user)
        self.target=Target.objects.create(project=self.project,name='Captured local lab evidence — no live route',kind='customer-request',state='unsupported')
        self.captured=[];before=None
        for record in self.saved['native_runs']:
            path=source/record['path'];self.assertTrue(path.is_relative_to(source/'evidence'))
            request,summary,_=inspect_execution(path)
            build=BuildRelease.objects.create(target=self.target,label='Captured '+record['profile']+' '+record['operation'],manifest=request.data['deployment'])
            cleanup=all(inspect_bundle(path/'cases'/row['case_id']/'bundle').status['cleanup_ok'] for row in summary['cases'])
            run=Run.objects.create(id=record['web_run_id'],project=self.project,target=self.target,build=build,actor=self.user,
                actor_auth_hash='0'*64,mfa_at=self.user.date_joined,native_run_id=request.data['run_id'],operation=record['operation'],
                profile=record['profile'],suite='profile',fixture_mode='fixed',original=before if record['operation']=='replay' else None,
                idempotency_key='captured-'+record['native_run_id'],intent_sha256='1'*64,state='completed',summary=summary,
                target_cleanup_verified=cleanup,progress='RECORDED actual outbound QNX qualification; imported only for browser presentation checks. No new execution.',
                process_facts={'execution_plane':'Recorded actual local outbound-runner qualification'})
            destination=run_path(run);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(path,destination)
            inventory=json.loads((destination/'web-evidence-v2.json').read_text())
            for name,facts in inventory['files'].items():
                Artifact.objects.create(run=run,relative_path=name,sha256=facts['sha256'],byte_count=facts['bytes'],
                    content_type='text/html' if name.endswith('.html') else 'application/json' if name.endswith('.json') else 'text/plain')
            data=(destination/'web-evidence-v2.json').read_bytes()
            Artifact.objects.create(run=run,relative_path='web-evidence-v2.json',sha256=hashlib.sha256(data).hexdigest(),byte_count=len(data),content_type='application/json')
            verify_inventory(run);self.captured.append(run)
            if before is None:before=run
        self.before=self.captured[0];self.after=self.captured[1]
        self.saved_directory=source.name

    def test_actual_customer_workflow(self):
        from playwright.sync_api import sync_playwright,Error as BrowserError
        try:
            with sync_playwright() as driver:
                cert=x509.load_pem_x509_certificate((self.out/'ca.pem').read_bytes())
                pin=base64.b64encode(hashlib.sha256(cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).digest()).decode()
                executable='/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell'
                browser=driver.chromium.launch(executable_path=executable,args=['--ignore-certificate-errors-spki-list='+pin])
                admin_context=browser.new_context(viewport={'width':1440,'height':900});admin=admin_context.new_page()
                self.stage='presentation continuation; actual administrator MFA'
                self.visit(admin,'/administrator/login/','administrator login')
                admin.locator('[name=login]').fill(self.user.username);admin.locator('[name=password]').fill(native.PASSWORD)
                admin.get_by_role('button',name='Sign in as administrator').click();admin.wait_for_url('**/administrator/2fa/authenticate/**')
                code=format_hotp_value(hotp_value(self.secret,int(time.time())//30))
                admin.locator('[name=code]').fill(code);admin.get_by_role('button',name='Sign In',exact=True).click();admin.wait_for_url('**/app/')
                codes='/administrator/organizations/'+str(self.org.pk)+'/codes/'
                self.visit(admin,codes,'issue scoped recorded-evidence code')
                admin.locator('[name=description]').fill('Recorded native continuation scope')
                admin.locator('[name=projects]').select_option(str(self.project.pk));admin.locator('[name=targets]').select_option(str(self.target.pk))
                for name in ['all_evidence','can_download']:admin.locator('[name='+name+']').check()
                admin.locator('[name=max_sessions]').fill('2');admin.locator('[name=max_redemptions]').fill('2')
                admin.get_by_role('button',name='Generate access code').click();raw=admin.locator('#new-access-code').inner_text().strip()
                code_id=str(uuid.UUID(hex=raw.split('_')[1]));self.visit(admin,'/administrator/codes/'+code_id+'/','actual code usage',True)
                contexts=[];after=self.after;before=self.before
                for width,javascript in [(1440,True),(390,False)]:
                    context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript)
                    contexts.append(context);page=context.new_page()
                    self.visit(page,'/access/','recorded evidence code entry');page.locator('[name=code]').fill(raw)
                    page.get_by_role('button',name='Open permitted workspace').click();page.wait_for_url('**/app/')
                    for path,label in [('/app/projects/'+str(self.project.pk)+'/','recorded project'),
                        ('/app/runs/'+str(before.pk)+'/','captured actual FAIL'),('/app/runs/'+str(after.pk)+'/','captured corrected PASS'),
                        ('/app/compare/?before='+str(before.pk)+'&after='+str(after.pk),'captured identified source comparison')]:
                        self.visit(page,path,label,javascript)
                    self.visit(page,'/app/runs/'+str(after.pk)+'/','authorized offline ZIP')
                    with page.expect_download() as download:page.get_by_role('link',name='Download verified offline ZIP').click()
                    self.assertIsNone(download.value.failure())
                    with open(download.value.path(),'rb') as stream:self.assertEqual(stream.read(2),b'PK')
                    self.assertEqual(page.goto(self.origin+'/app/projects/'+str(uuid.uuid4())+'/').status,404)
                    self.assertEqual(page.goto(self.origin+'/app/projects/'+str(self.project.pk)+'/runners/'+str(self.target.pk)+'/').status,404)
                self.stage='recorded evidence session revocation'
                admin.get_by_role('button',name='Revoke this code immediately').click()
                for context in contexts:
                    page=context.pages[0];page.goto(self.origin+'/app/');self.assertEqual(urlsplit(page.url).path,'/access/')
                raw=None;self.result={'passed':True,'native_executed_in_this_continuation':False,
                    'captured_native_source':self.saved_directory,'captured_native_run_ids':[run.native_run_id for run in self.captured],
                    'actual_browser_code_issue_redeem_revoke':True,'actual_offline_zip_download':True,
                    'desktop_and_no_js_mobile':True,'cross_tenant_and_runner_admin_denials':True,
                    'independent_acceptance':False,'public_https':False,'AI':'disabled','browser_version':browser.version,
                    'scope':'Browser/TLS/code/download/accessibility continuation using preserved native IDs and bytes. Fresh disposable DB with recorded labels; no QNX contact or new native execution.'}
                browser.close();self.stage='recorded presentation continuation complete'
        except BrowserError as error:
            from customer_runner.client import create
            create(self.out/'browser-error.log',str(error).encode())
            raise AssertionError('Browser presentation continuation failed; protected safe diagnostics retained') from None
