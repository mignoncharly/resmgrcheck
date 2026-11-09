#!/usr/bin/env python3
"""Three actual dashboard cases. Credentials stay on stdin/in memory."""
import argparse,json,os,secrets,sys,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from public_acceptance import Journey,require,HOST

class NativeJourney(Journey):
    def click(self,page,name,exact=True):
        # Only authentication/code management POSTs use the public auth zone.
        # Native queue confirmations have their own application quotas.
        if urlsplit(page.url).path.startswith(('/access/','/administrator/')):self.pace()
        page.get_by_role('button',name=name,exact=exact).click()

    def queue(self,page,profile,build,*,mode='fixed',original=None):
        native=self.secret['native'];self.step='queue-'+profile
        if original:
            self.visit(page,'/app/runs/'+original['web_run_id']+'/replay/','source-replay')
            page.locator('[name=build]').select_option(build);self.click(page,'Confirm and queue saved-input replay')
        else:
            self.visit(page,'/app/projects/'+native['project_id']+'/runs/new/','native-run-form')
            for name,value in [('target',native['target_id']),('build',build),('profile',profile),('suite','profile'),('fixture_mode',mode)]:
                page.locator('[name='+name+']').select_option(value)
            self.click(page,'Preview test request');self.click(page,'Confirm and queue')
        page.wait_for_url('**/app/runs/*/');identifier=urlsplit(page.url).path.split('/')[3]
        row={'web_run_id':identifier,'native_run_id':'w'+uuid.UUID(identifier).hex[:18],'profile':profile,
            'operation':'replay' if original else 'run','mode':mode,'status':'pending'}
        self.runs.append(row);self.checkpoint();return row

    def wait(self,page,row,expected):
        self.step='collect-'+row['profile'];deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            response=page.context.request.get(self.origin+'/api/runs/'+row['web_run_id']+'/',max_redirects=0)
            require(response.status==200,'native_status_unavailable');value=response.json()
            require(value['native_run_id']==row['native_run_id'],'native_identity_changed')
            if value['state'] in {'completed','blocked','rejected','cancelled'}:break
            time.sleep(.25)
        require(value['state']=='completed' and value['cleanup_verified'] and value['evidence_integrity']=='verified','native_or_cleanup_not_complete')
        verdicts=[case['verdict'] for case in value['summary']['cases']];require(verdicts==[expected],'native_outcome_mismatch')
        row.update(status='passed',verdicts=verdicts,cleanup_verified=True,evidence_integrity='verified');self.checkpoint()
        self.visit(page,'/app/runs/'+row['web_run_id']+'/','actual-native-report',scan=True)

    def control(self,action,**fields):
        identifier=uuid.uuid4().hex;path=self.out/('request-'+identifier+'.json')
        raw=json.dumps({'request_id':identifier,'action':action,**fields}).encode()
        temporary=self.out/('.request-'+identifier)
        with temporary.open('xb') as stream:stream.write(raw)
        temporary.chmod(0o600);os.rename(temporary,path);return identifier

    def response(self,identifier,stage='ready',timeout=100):
        path=self.out/('response-'+identifier+'-'+stage+'.json');deadline=time.monotonic()+timeout
        while not path.exists() and time.monotonic()<deadline:time.sleep(.05)
        require(path.is_file(),'operator_observation_timeout');data=json.loads(path.read_text())
        require(data.get('passed') is True,'operator_observation_failed');return data

    def run(self):
        from playwright.sync_api import sync_playwright
        binary=Path('/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
        with sync_playwright() as driver:
            browser=driver.chromium.launch(executable_path=str(binary))
            anonymous=browser.new_context()
            response=anonymous.request.post(self.origin+'/runner/v1/exchange/',data='{}',headers={'Content-Type':'application/json'})
            require(response.status==404,'customer_runner_endpoint_enabled');anonymous.close()
            admin=browser.new_context(viewport={'width':1440,'height':1000});administrator=admin.new_page();self.login(administrator,'desktop')
            raw,detail=self.issue(administrator,'production-native',live=True,max_sessions=2,max_redemptions=2)
            user=browser.new_context(viewport={'width':1440,'height':1000});page=user.new_page();self.redeem(page,raw);raw=None
            native=self.secret['native']
            self.denied(user,'/app/projects/'+self.secret['foreign_project_id']+'/',404,'cross-tenant-project')
            self.denied(user,'/administrator/settings/',404,'code-cannot-approve-targets')
            before=self.queue(page,'sensor',native['before_build'],mode='ignore-unblock')
            recovery=self.control('recover',run_id=before['web_run_id'])
            self.response(recovery);self.wait(page,before,'FAIL');proof=self.response(recovery,'complete')
            self.results['same_ID_recovery']=proof
            after=self.queue(page,'sensor',native['after_build'],mode='ignore-unblock',original=before);self.wait(page,after,'PASS')
            self.visit(page,'/app/compare/?before='+before['web_run_id']+'&after='+after['web_run_id'],'source-correction-comparison',scan=True)
            badge=page.get_by_role('heading',name='Canonical comparison').locator('..').locator('.badge').inner_text().strip()
            require(badge=='fixed','source_correction_not_proven')
            self.results['source_corrected_comparison']='fixed'
            for row in [before,after]:self.download(page,row)
            # Leave auth-zone capacity for immediate revocation once native pending
            # is actually observed. Queue POSTs do not consume that zone.
            time.sleep(max(0,6.5-(time.monotonic()-self.last_post)))
            live=self.queue(page,'job',native['after_build'])
            revocation=self.control('revoke-observe',run_id=live['web_run_id'])
            pending=self.response(revocation);require(pending['timed_pending_observed'],'actual_native_pending_unproven')
            queued=self.queue(page,'job',native['after_build']);queued['expected']='rejected_before_launch'
            self.revoke(administrator,detail)
            self.denied(user,'/app/',302,'revoked-live-code-session')
            # Collection after revocation uses existing service supervision and an
            # independent still-authorized administrator, never the revoked code.
            self.wait(administrator,live,'PASS');self.download(administrator,live)
            proof=self.response(revocation,'complete');require(proof['queued_run_id']==queued['web_run_id'],'queued_revocation_identity_changed')
            self.results['live_and_queued_revocation']=proof
            queued.update(status='rejected_before_launch',verdicts=[],cleanup_verified=False)
            mobile=browser.new_context(viewport={'width':390,'height':900},java_script_enabled=False);mobile_page=mobile.new_page()
            self.login(mobile_page,'mobile-no-js')
            for row in [before,after,live]:self.visit(mobile_page,'/app/runs/'+row['web_run_id']+'/','mobile-native-report','mobile-no-js')
            self.results.update(passed=True,browser_passed=True,access_codes='passed',browser_version=browser.version,
                native={'status':'passed','new_native_executions':3,'queued_rejected_before_launch':1,'exact_IDs_preserved':True,
                    'source_corrected_comparison':'fixed','cleanup_observed':True},
                independent_external_client=False,customer_runner_endpoints='disabled')
            self.checkpoint();browser.close()
        return self.results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out);require(os.geteuid()!=0 and out.is_absolute() and out.is_dir() and out.stat().st_uid==os.geteuid() and out.stat().st_mode&0o077==0,'nonroot_private_output_required')
    credentials=json.loads(sys.stdin.buffer.read(32769));journey=NativeJourney('https://'+HOST,out,credentials)
    try:result=journey.run();print(json.dumps({'passed':result['passed'],'native_passed':result['native']['status']=='passed'}))
    except BaseException as error:
        journey.results.update(passed=False,failed_step=journey.step,error_class=type(error).__name__);journey.checkpoint()
        print(json.dumps({'passed':False,'failed_step':journey.step,'error_class':type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
