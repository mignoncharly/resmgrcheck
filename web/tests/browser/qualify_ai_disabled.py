#!/usr/bin/env python3
"""Real HTTP/browser AI-disabled flow; genuine QNX evidence, original MIT patch, no provider call."""
import argparse,base64,hashlib,hmac,json,struct,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:8431'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credentials=json.loads((ROOT/'.local/web/private/acceptance-account.json').read_text());refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
def code():
 raw=hmac.new(base64.b32decode(credentials['totp_secret']),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=raw[-1]&15
 return str((struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
checks=[];accessibility=[];axe=(ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text()
with sync_playwright() as driver:
 browser=driver.chromium.launch();context=browser.new_context(viewport={'width':390,'height':900});page=context.new_page()
 page.goto(BASE+'/administrator/login/');page.locator('[name=login]').fill(credentials['username']);page.locator('[name=password]').fill(credentials['password'])
 page.get_by_role('button',name='Sign in as administrator',exact=True).click();page.wait_for_url('**/administrator/2fa/authenticate/**')
 for attempt in range(3):
  page.locator('[name=code]').fill(code());page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(200)
  if urlsplit(page.url).path=='/app/':break
  assert attempt<2,'MFA login unavailable';time.sleep(30-time.time()%30+.1)
 page.goto(BASE+'/app/projects/'+refs['project_id']+'/ai/settings/')
 assert 'Provider unavailable or disabled' in page.locator('main').inner_text()
 assert not page.locator('[name=enabled]').is_checked()
 # Upload only the project's already published, reviewed MIT source correction.
 page.goto(BASE+'/app/projects/'+refs['project_id']+'/ai/source/');page.locator('[name=label]').fill('Recorded MIT sensor handler correction (private qualification)')
 patch=ROOT/'docs/jury/source-fix.patch';page.locator('[name=file]').set_input_files(str(patch));page.locator('[name=rights]').check()
 page.locator('form').filter(has=page.locator('[name=file]')).get_by_role('button',name='Retain redacted source for review',exact=True).click();page.wait_for_url('**/app/source/*/')
 source_id=urlsplit(page.url).path.strip('/').split('/')[-1]
 assert 'Uploading did not send it to a provider' in page.locator('main').inner_text()
 page.goto(BASE+'/app/runs/'+refs['broken']+'/ai/');page.locator('[name=task]').select_option('source-review');page.locator('[name=source]').select_option(source_id)
 page.get_by_role('button',name='Preview selected evidence').click()
 assert 'Exact redacted provider payload' in page.locator('main').inner_text()
 assert 'AI unavailable / not configured' in page.locator('main').inner_text()
 assert not page.locator('[name=confirmation]').input_value()
 path=urlsplit(page.url).path
 for width,javascript in [(1440,True),(390,True),(1280,False),(390,False)]:
  view=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript,storage_state=context.storage_state());document=view.new_page();external=[]
  document.on('request',lambda request:external.append(request.url) if urlsplit(request.url).scheme in {'http','https'} and not request.url.startswith(BASE+'/') else None)
  for label,route in [('ai-request',path),('source','/app/source/'+source_id+'/'),('ai-settings','/app/projects/'+refs['project_id']+'/ai/settings/'),('native','/app/runs/'+refs['broken']+'/')]:
   response=document.goto(BASE+route,wait_until='networkidle');assert response.status==200
   assert document.evaluate('document.documentElement.scrollWidth<=innerWidth') and not external
   if width==1440 and javascript:
    document.evaluate(axe)
    result=document.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
    accessibility.append({'page':label,'violations':result})
    assert not [violation for violation in result if violation['impact'] in {'critical','serious'}],(label,result)
   checks.append({'page':label,'width':width,'javascript':javascript,'external_requests':list(external),'status':200})
   if label=='ai-request':document.screenshot(path=str(out/(label+'-'+str(width)+'-'+str(javascript)+'.png')))
  view.close()
 browser.close()
(out/'qualification.json').write_text(json.dumps({'passed':True,'checks':checks,'accessibility':accessibility,'provider_calls':0,'provider_verification':'NOT_RUN: no dedicated credential configured',
 'native_execution_performed':False,'source_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'source_id':source_id,
 'source_scope':'Already published original MIT correction patch; no SDK/source binary or private config uploaded','preview_only':True},indent=2)+'\n')
print('PASS:',len(checks),'real browser views; original source upload/preview; AI disabled; deterministic report available; no provider/QNX call.')
