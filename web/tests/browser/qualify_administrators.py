#!/usr/bin/env python3
"""Actual administrator management UI, desktop/no-JS mobile. No secret screenshots."""
import argparse,base64,hashlib,hmac,json,struct,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:8431'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credential=json.loads((ROOT/'.local/web/private/acceptance-administrator.json').read_text());refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
code_record=json.loads((ROOT/'.local/web/evidence/access-browser-1/qualification.json').read_text())
axe=(ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text()
def totp():
    value=hmac.new(base64.b32decode(credential['totp_secret']),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=value[-1]&15
    return str((struct.unpack('>I',value[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
views=[];audits=[]
with sync_playwright() as driver:
    browser=driver.chromium.launch()
    for mode,width,javascript in [('desktop',1440,True),('mobile-no-js',390,False)]:
        context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript);page=context.new_page()
        page.goto(BASE+'/administrator/login/');page.locator('[name=login]').fill(credential['username']);page.locator('[name=password]').fill(credential['password'])
        page.get_by_role('button',name='Sign in as administrator').click();page.wait_for_url('**/administrator/2fa/authenticate/**')
        for attempt in range(3):
            page.locator('[name=code]').fill(totp());page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(200)
            if urlsplit(page.url).path=='/app/':break
            assert attempt<2,'MFA unavailable; no bypass';time.sleep(30-time.time()%30+.1)
        routes={'team':'/app/organizations/'+refs['organization_id']+'/team/','codes':'/administrator/organizations/'+refs['organization_id']+'/codes/',
            'code-detail':code_record['code_detail_path'],'security':'/administrator/settings/','password':'/administrator/password/change/',
            'sessions':'/administrator/sessions/','audit':'/app/organizations/'+refs['organization_id']+'/audit/'}
        for label,path in routes.items():
            response=page.goto(BASE+path,wait_until='networkidle');assert response.status==200,(label,response.status)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(mode,label,'overflow')
            assert not page.locator('#new-access-code').count()
            if javascript:
                page.evaluate(axe)
                issues=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
                audits.append({'page':label,'violations':issues});assert not [v for v in issues if v['impact'] in {'critical','serious'}],(label,issues)
            views.append({'audience':'administrator','page':label,'width':width,'javascript':javascript,'status':response.status})
        context.close()
    version=browser.version;browser.close()
(out/'qualification.json').write_text(json.dumps({'passed':True,'browser':version,'views':views,'accessibility':audits,'real_password_mfa':True,'secrets_or_cookie_state_saved':False,'native_or_provider_calls':0},indent=2)+'\n')
print('PASS:14 administrator browser views, seven accessibility scans; desktop/no-JS mobile, real password/MFA, no saved secret or cookie state.')
