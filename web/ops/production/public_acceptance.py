#!/usr/bin/env python3
"""Actual HTTPS browser acceptance. Reads fresh temporary credentials on stdin only.
No TLS bypass, trace, HAR, screenshots, cookies or raw access codes are saved.
"""
import argparse,base64,hashlib,hmac,json,os,struct,sys,time,uuid,zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[3]
HOST='qnx-resmgrcheck.gestionatech.de'

def require(value,code):
    if not value:raise AssertionError(code)

def totp(secret):
    raw=hmac.new(base64.b32decode(secret),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=raw[-1]&15
    return str((struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)

class Journey:
    def __init__(self,origin,out,credentials):
        self.origin=origin;self.host=urlsplit(origin).netloc;self.out=out;self.secret=credentials;self.step='initializing';self.views=[];self.scans=[];self.runs=[];self.last_post=0
        self.results={'kind':'actual-production-HTTPS-browser-acceptance','origin':origin,'passed':False,
            'administrator_password_MFA':'not_run','access_codes':'not_run','native':credentials['native'],
            'views':self.views,'accessibility':self.scans,'runs':self.runs,'independent_external_client':False,
            'credentials_cookies_traces_saved':False,'AI':'disabled','separate_customer_host':'not_qualified'}
    def checkpoint(self):
        path=self.out/'browser-report.json';path.write_text(json.dumps(self.results,indent=2)+'\n');path.chmod(0o600)
    def pace(self):
        # Nginx caps all auth POSTs10/min; avoid exhausting the public test address.
        delay=6.3-(time.monotonic()-self.last_post)
        if delay>0:time.sleep(delay)
        self.last_post=time.monotonic()
    def click(self,page,name,exact=True):self.pace();page.get_by_role('button',name=name,exact=exact).click()
    def visit(self,page,path,label,mode='desktop',status=200,scan=False):
        self.step=label;response=page.goto(self.origin+path,wait_until='networkidle');require(response.status==status,'unexpected_page_status')
        require(urlsplit(page.url).netloc==self.host,'redirect_left_intended_origin')
        require(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'horizontal_overflow')
        headers=response.all_headers();require('max-age=31536000'==headers.get('strict-transport-security'),'hsts_missing')
        require(headers.get('x-content-type-options')=='nosniff','nosniff_missing');require('content-security-policy' in headers,'csp_missing')
        self.views.append({'view':label,'mode':mode,'http_status':response.status})
        if scan:
            page.evaluate((ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text())
            violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
            self.scans.append({'view':label,'violations':violations});require(not violations,'accessibility_violations')
        self.checkpoint();return response
    def login(self,page,mode):
        self.visit(page,'/administrator/login/','administrator-login',mode,scan=mode=='desktop')
        page.locator('[name=login]').fill(self.secret['username']);page.locator('[name=password]').fill(self.secret['password'])
        if mode=='desktop':
            page.locator('[name=password]').fill('Deliberately invalid acceptance probe')
            self.click(page,'Sign in as administrator');page.wait_for_load_state('networkidle')
            require(urlsplit(page.url).path=='/administrator/login/','incorrect_password_authorized')
            page.locator('[name=login]').fill(self.secret['username']);page.locator('[name=password]').fill(self.secret['password'])
        self.click(page,'Sign in as administrator');page.wait_for_url('**/administrator/2fa/authenticate/**')
        require(page.context.request.get(self.origin+'/app/',max_redirects=0).status==302,'password_bypassed_MFA')
        for attempt in range(3):
            page.locator('[name=code]').fill(totp(self.secret['totp_secret']));self.click(page,'Sign In');page.wait_for_timeout(200)
            if urlsplit(page.url).path=='/app/':break
            require(attempt<2,'MFA_failed');time.sleep(30-time.time()%30+.1)
        require(urlsplit(page.url).path=='/app/','MFA_not_completed')
        for cookie in page.context.cookies():
            if cookie['name'] in {'resmgrcheck_session','resmgrcheck_csrf'}:
                require(cookie['secure'] and cookie['httpOnly'] and cookie['sameSite']=='Lax','cookie_security_flags')
        self.visit(page,'/app/','administrator-overview',mode,scan=mode=='desktop')
        self.results['administrator_password_MFA']='passed'
    def issue(self,page,label,*,live=False,max_sessions=2,max_redemptions=2,expires=None):
        self.step='code-issuance';path='/administrator/organizations/'+self.secret['organization_id']+'/codes/'
        self.visit(page,path,'access-code-form')
        page.locator('[name=description]').fill('HTTPS acceptance '+label+' '+self.secret['acceptance_id'][:8])
        page.locator('[name=projects]').select_option([self.secret['project_id']])
        native=self.secret['native']
        if native.get('target_id'):page.locator('[name=targets]').select_option([native['target_id']])
        page.locator('[name=all_evidence]').check();page.locator('[name=can_download]').check()
        if live:page.locator('[name=allow_live]').check()
        page.locator('[name=max_sessions]').fill(str(max_sessions));page.locator('[name=max_redemptions]').fill(str(max_redemptions))
        if expires:page.locator('[name=expires_at]').fill(expires.strftime('%Y-%m-%d %H:%M:%S'))
        self.click(page,'Generate access code');raw=page.locator('#new-access-code').inner_text().strip()
        require(raw.startswith('rmc_') and len(raw)==80,'access_code_not_issued')
        page.get_by_role('link',name='Manage permissions and sessions').click();page.wait_for_load_state('networkidle')
        detail=urlsplit(page.url).path;require(raw not in page.locator('body').inner_text(),'code_not_one_time_display')
        return raw,detail
    def redeem(self,page,raw,success=True):
        self.visit(page,'/access/','code-entry');page.locator('[name=code]').fill(raw)
        self.click(page,'Open permitted workspace');page.wait_for_load_state('networkidle')
        if success:
            require(urlsplit(page.url).path=='/app/','code_redemption_failed')
            cookies=[c for c in page.context.cookies() if c['name']=='resmgrcheck_session']
            require(len(cookies)==1 and cookies[0]['secure'] and cookies[0]['httpOnly'] and cookies[0]['sameSite']=='Lax','code_cookie_security_flags')
        else:
            require(urlsplit(page.url).path=='/access/','invalid_code_authorized')
            require('Access denied' in page.locator('main').inner_text(),'generic_code_denial_missing')
            require(page.locator('[name=code]').input_value()=='','access_code_reflected')
    def revoke(self,page,detail):
        self.visit(page,detail,'code-management');self.click(page,'Revoke this code immediately');page.wait_for_load_state('networkidle')
    def denied(self,context,path,status,label):
        self.step=label;response=context.request.get(self.origin+path,max_redirects=0)
        require(response.status==status,'protected_route_not_denied');self.views.append({'view':label,'http_status':response.status});self.checkpoint()
    def execute(self,page,profile,build,expected,original=None):
        self.step='native-'+profile+('-replay' if original else '')
        native=self.secret['native']
        if original:
            self.visit(page,'/app/runs/'+original['web_run_id']+'/replay/','native-source-replay')
            page.locator('[name=build]').select_option(build);self.click(page,'Confirm and queue saved-input replay')
        else:
            self.visit(page,'/app/projects/'+native['project_id']+'/runs/new/','native-run-form')
            page.locator('[name=target]').select_option(native['target_id']);page.locator('[name=build]').select_option(build)
            page.locator('[name=profile]').select_option(profile);page.locator('[name=suite]').select_option('profile');page.locator('[name=fixture_mode]').select_option('fixed')
            self.click(page,'Preview test request');self.click(page,'Confirm and queue')
        page.wait_for_url('**/app/runs/*/');identifier=urlsplit(page.url).path.split('/')[3]
        row={'web_run_id':identifier,'profile':profile,'operation':'replay' if original else 'run','expected':expected,'status':'pending'}
        self.runs.append(row);self.checkpoint();deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            response=page.context.request.get(self.origin+'/api/runs/'+identifier+'/',max_redirects=0);require(response.status==200,'native_status_unavailable');value=response.json()
            require(value['native_run_id']=='w'+uuid.UUID(identifier).hex[:18],'native_identity_not_bound_to_web_request')
            if row.get('native_run_id'):require(row['native_run_id']==value['native_run_id'],'native_identity_changed')
            row['native_run_id']=value['native_run_id'];row['orchestration']=value['state'];self.checkpoint()
            if value['state'] in {'completed','blocked','rejected','cancelled'}:break
            time.sleep(1)
        require(value['state']=='completed' and value['cleanup_verified'] and value['evidence_integrity']=='verified','native_or_cleanup_not_complete')
        verdicts=[case['verdict'] for case in value['summary']['cases']]
        row.update(verdicts=verdicts,cleanup_verified=value['cleanup_verified'],evidence_integrity=value['evidence_integrity']);self.checkpoint()
        require(verdicts==[expected],'native_outcome_mismatch')
        row.update(status='passed',verdicts=verdicts,cleanup_verified=True,evidence_integrity='verified');self.checkpoint()
        self.visit(page,'/app/runs/'+identifier+'/','native-report-'+profile,scan=True)
        return row
    def download(self,page,row):
        self.step='authenticated-evidence-download'
        self.visit(page,'/app/runs/'+row['web_run_id']+'/','download-report')
        with page.expect_download() as pending:page.get_by_role('link',name='Download verified offline ZIP').click()
        target=self.out/('evidence-'+row['web_run_id']+'.zip');pending.value.save_as(target);target.chmod(0o600)
        require(target.stat().st_size<=70*1024**2,'export_size_invalid')
        with zipfile.ZipFile(target) as archive:
            require(len(archive.namelist())==len(set(archive.namelist())),'duplicate_export_member')
            require(len(archive.infolist())<=520 and sum(member.file_size for member in archive.infolist())<=70*1024**2 and archive.getinfo('EXPORT.json').file_size<=1024**2,'export_uncompressed_bound')
            record=json.loads(archive.read('EXPORT.json'));require(record['native_run_id']==row['native_run_id'],'export_native_identity_changed')
            for name,identity in record['files'].items():
                raw=archive.read(name);require(hashlib.sha256(raw).hexdigest()==identity['sha256'] and len(raw)==identity['bytes'],'export_hash_mismatch')
        row['download_verified']=True;self.checkpoint()
    def run(self):
        from playwright.sync_api import sync_playwright
        binary=Path('/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
        require(binary.is_file(),'installed_chromium_missing')
        with sync_playwright() as driver:
            browser=driver.chromium.launch(executable_path=str(binary))
            anonymous=browser.new_context(viewport={'width':1440,'height':1000});page=anonymous.new_page()
            self.visit(page,'/','public-landing',scan=True)
            for selection in ['before','after','job']:
                self.visit(page,'/demo/'+selection+'/','genuine-recorded-'+selection,scan=True)
            self.denied(anonymous,'/app/',302,'anonymous-dashboard-denial');self.denied(anonymous,'/administrator/signup/',404,'public-registration-absent')
            bad=anonymous.request.post(self.origin+'/runner/v1/exchange/',data='{}',headers={'Content-Type':'application/json'});require(bad.status==404,'customer_runner_endpoint_enabled')
            self.results['customer_runner_endpoints']='disabled';self.results['public_landing_recorded_evidence']='passed'
            admin=browser.new_context(viewport={'width':1440,'height':1000});administrator=admin.new_page();self.login(administrator,'desktop')
            # A token from the right browser still cannot authorize a foreign origin.
            self.visit(administrator,'/administrator/settings/','administrator-security',scan=True)
            token=administrator.locator('[name=csrfmiddlewaretoken]').first.get_attribute('value')
            self.pace();response=admin.request.post(self.origin+'/administrator/logout-all/',form={'csrfmiddlewaretoken':token,'password':'invalid-probe'},headers={'Origin':'https://untrusted.invalid'})
            require(response.status==403,'cross_origin_post_not_rejected');self.results['csrf_origin']='passed'
            live=self.secret['native']['status']=='approved-existing-route'
            raw,detail=self.issue(administrator,'scoped-native' if live else 'scoped-viewer',live=live)
            sessions=[]
            for mode,width,javascript in [('desktop',1440,True),('mobile-no-js',390,False)]:
                context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript);document=context.new_page()
                self.visit(document,'/','public-landing-'+mode,mode)
                self.redeem(document,raw)
                for path,label in [('/app/','overview'),('/app/projects/','projects'),('/app/targets/','targets'),('/app/runs/','history'),('/app/session/','session')]:
                    self.visit(document,path,'code-'+label,mode,scan=javascript)
                self.denied(context,'/app/projects/'+self.secret['foreign_project_id']+'/',404,'cross-tenant-project')
                self.denied(context,'/administrator/settings/',404,'code-administrator-denial')
                self.denied(context,'/sign-out/',405,'get-signout-has-no-side-effect')
                sessions.append((context,document))
            excess=browser.new_context();self.redeem(excess.new_page(),raw,False);excess.close()
            if live:
                self.results['native']={'status':'running','scope':'existing approved production lab executor; real public HTTPS dashboard'}
                before=self.execute(sessions[0][1],'sensor',self.secret['native']['before_build'],'FAIL')
                after=self.execute(sessions[0][1],'sensor',self.secret['native']['after_build'],'PASS',before)
                sensor=self.execute(sessions[0][1],'sensor',self.secret['native']['after_build'],'PASS')
                job=self.execute(sessions[0][1],'job',self.secret['native']['after_build'],'PASS')
                self.visit(sessions[0][1],'/app/compare/?before='+before['web_run_id']+'&after='+after['web_run_id'],'source-fixed-comparison',scan=True)
                badge=sessions[0][1].get_by_role('heading',name='Canonical comparison').locator('..').locator('.badge').inner_text().strip()
                require(badge=='fixed','source_correction_not_proven')
                for row in [before,after,sensor,job]:self.download(sessions[0][1],row)
                for row in [before,after,job]:self.visit(sessions[1][1],'/app/runs/'+row['web_run_id']+'/','mobile-existing-live-report','mobile-no-js')
                self.results['native']={'status':'passed','new_native_executions':4,'cleanup_observed':True,'exact_IDs_preserved':True,'source_corrected_comparison':'fixed'}
            self.revoke(administrator,detail)
            for context,_ in sessions:self.denied(context,'/app/',302,'revoked-active-session')
            raw=None
            # Independently prove usage exhaustion after releasing session capacity.
            once,once_detail=self.issue(administrator,'single-use',max_sessions=2,max_redemptions=1)
            usage=browser.new_context();usage_page=usage.new_page();self.redeem(usage_page,once)
            self.visit(usage_page,'/app/session/','single-use-session');self.click(usage_page,'Sign out and revoke this session');usage_page.wait_for_load_state('networkidle')
            self.redeem(usage_page,once,False);once=None;usage.close()
            # Actual clock expiration via the supported administrator form, never a DB clock edit.
            expiry=datetime.now(timezone.utc)+timedelta(seconds=65)
            expiring,expiry_detail=self.issue(administrator,'short-expiration',max_sessions=1,max_redemptions=2,expires=expiry)
            expired=browser.new_context();expired_page=expired.new_page();self.redeem(expired_page,expiring)
            while datetime.now(timezone.utc)<=expiry+timedelta(seconds=1):time.sleep(.5)
            self.denied(expired,'/app/',302,'actual-expired-code-session');self.redeem(expired_page,expiring,False);expiring=None;expired.close()
            self.results.update(access_codes='passed',code_expiration='passed with actual clock',usage_limit='passed',scope_and_revocation='passed',
                idle_30minute_and_absolute_12hour_session_expiration='unit-qualified; production duration not waited')
            mobile_admin=browser.new_context(viewport={'width':390,'height':900},java_script_enabled=False);self.login(mobile_admin.new_page(),'mobile-no-js')
            self.results['browser_version']=browser.version;self.results['browser_passed']=True
            self.results['passed']=self.results['native'].get('status')=='passed';self.checkpoint();browser.close()
        return self.results

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--origin',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    require(args.origin=='https://'+HOST,'intended_https_origin_required');require(os.geteuid()!=0,'browser_must_run_nonroot')
    out=Path(args.out);require(out.is_absolute() and out.is_dir() and out.stat().st_uid==os.geteuid() and out.stat().st_mode&0o077==0,'private_output_required')
    credentials=json.loads(sys.stdin.buffer.read(32769));journey=Journey(args.origin,out,credentials)
    try:
        result=journey.run();print(json.dumps({'passed':result['passed'],'browser_passed':result['browser_passed'],'administrator_password_MFA':result['administrator_password_MFA'],
            'access_codes':result['access_codes'],'native':result['native'],'views':len(result['views']),'accessibility_scans':len(result['accessibility']),
            'protected_browser_report':str(out/'browser-report.json')}))
    except BaseException as error:
        journey.results.update(passed=False,failed_step=journey.step,error_class=type(error).__name__);journey.checkpoint()
        print(json.dumps({'passed':False,'failed_step':journey.step,'error_class':type(error).__name__,'secrets_printed':False}))
        raise SystemExit(1) from None

if __name__=='__main__':main()
