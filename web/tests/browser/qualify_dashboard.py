#!/usr/bin/env python3
"""Real staging browser checks. Saved QNX data only; no new native test launch."""
import argparse,base64,hashlib,hmac,json,os,struct,subprocess,time
from pathlib import Path
from importlib.metadata import version
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credentials=json.loads((ROOT/'.local/web/private/acceptance-account.json').read_text())
refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
axe=(ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text()
axe_version=json.loads((ROOT/'.local/web/browser/node_modules/axe-core/package.json').read_text())['version']
BASE='http://127.0.0.1:8431'
def totp(secret):
 raw=hmac.new(base64.b32decode(secret),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=raw[-1]&15
 return str((struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
public={'home':'/','sensor-before':'/demo/before/','sensor-after':'/demo/after/','job-playback':'/demo/job/',
        'partial-playback':'/demo/partial/','docs':'/about/docs/','scope':'/about/security/','privacy':'/about/privacy/','login':'/administrator/login/','developer-access':'/access/'}
private={'overview':'/app/','projects':'/app/projects/','targets':'/app/targets/','history':'/app/runs/',
 'project':'/app/projects/'+refs['project_id']+'/', 'target-settings':'/app/projects/'+refs['project_id']+'/targets/',
 'new-run':'/app/projects/'+refs['project_id']+'/runs/new/','fixed-run':'/app/runs/'+refs['fixed']+'/',
 'failed-run':'/app/runs/'+refs['broken']+'/', 'source-replay':'/app/runs/'+refs['replay']+'/',
 'job-run':'/app/runs/'+refs['job']+'/', 'transfer-error':'/app/runs/'+refs['transfer']+'/',
 'compare':'/app/compare/?before='+refs['broken']+'&after='+refs['replay'],
 'account':'/app/account/','team':'/app/organizations/'+refs['organization_id']+'/team/',
 'audit':'/app/organizations/'+refs['organization_id']+'/audit/'}
checks=[];shots=[];accessibility=[]
with sync_playwright() as driver:
 browser=driver.chromium.launch();browser_version=browser.version
 auth=browser.new_context();page=auth.new_page();page.goto(BASE+'/administrator/login/')
 page.locator('input[name=login]').fill(credentials['username']);page.locator('input[name=password]').fill(credentials['password'])
 page.locator('form').filter(has=page.locator('input[name=password]')).get_by_role('button',name='Sign in as administrator',exact=True).click()
 page.wait_for_url('**/administrator/2fa/authenticate/**')
 for attempt in range(3):
  page.locator('input[name=code]').fill(totp(credentials['totp_secret']))
  page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(300)
  if urlsplit(page.url).path=='/app/':break
  assert attempt<2,'MFA authentication did not complete; no credential values logged'
  time.sleep(30-time.time()%30+.1) # Respect server-side one-use TOTP replay prevention.
 page.wait_for_url('**/app/')
 state=auth.storage_state();page.close();auth.close()
 for mode,width,height,javascript in [('desktop',1440,1000,True),('mobile',390,844,True),('desktop-no-js',1280,900,False),('mobile-no-js',390,844,False)]:
  for audience,paths in [('public',public),('authorized',private)]:
   context=browser.new_context(viewport={'width':width,'height':height},java_script_enabled=javascript,storage_state=state if audience=='authorized' else None)
   for name,path in paths.items():
    page=context.new_page();errors=[];external=[]
    page.on('pageerror',lambda error:errors.append(type(error).__name__))
    page.on('request',lambda req:external.append(req.url) if urlsplit(req.url).scheme in {'http','https'} and not req.url.startswith(BASE+'/') else None)
    response=page.goto(BASE+path,wait_until='networkidle');assert response.status==200,(name,mode,response.status)
    assert page.locator('h1').count()==1,(name,mode,'heading count')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(name,mode,'page overflow')
    assert not errors and not external,(name,mode,errors,'unexpected external requests')
    if name=='sensor-before' or name=='failed-run':
     assert 'cancellation_not_completed' in page.locator('main').inner_text()
     assert 'pending_state_not_released' in page.locator('main').inner_text()
    if name=='partial-playback':assert 'no finalized native bundle' in page.locator('main').inner_text()
    if name=='compare':assert 'fixed' in page.locator('main').inner_text()
    if mode in {'desktop','mobile'} and name in {'home','sensor-before','overview','failed-run','compare','targets','developer-access'}:
     shot=out/'screenshots'/(name+'-'+mode+'.png');shot.parent.mkdir(exist_ok=True)
     page.screenshot(path=str(shot));shots.append(str(shot.relative_to(out)))
    if mode=='desktop' and javascript:
     page.evaluate(axe)
     result=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {passes:r.passes.length,violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}}")
     accessibility.append({'document':name,**result})
     assert not [v for v in result['violations'] if v['impact'] in {'critical','serious'}],(name,'accessibility',result['violations'])
    if name in {'sensor-before','failed-run'}:
     detail=page.locator('.case-card details').first;detail.evaluate('e=>{e.open=false;}');detail.locator('summary').focus();page.keyboard.press('Enter')
     assert detail.get_attribute('open') is not None,(name,'native keyboard disclosure')
     if javascript:
      reference=page.locator('a[href^="#event-"]').first;reference.click()
      assert page.locator(page.url.split('#')[1] and '#'+page.url.split('#')[1]).get_attribute('open') is not None
    checks.append({'document':name,'audience':audience,'viewport':[width,height],'javascript':javascript,'http_status':response.status,'no_page_overflow':True,'page_errors':errors,'external_requests':external})
    page.close()
   context.close()
 browser.close()
index={'kind':'web-p4-browser-qualification','schema_version':1,'passed':True,'browser':browser_version,'playwright':version('playwright'),'axe_core':axe_version,
 'checks':checks,'accessibility':accessibility,'screenshots':shots,'native_execution_performed':False,
 'data_scope':'Actual staging user requests/native QNX evidence and explicitly labelled public recorded playback; no seed activity or simulated native execution.',
 'limitations':['Chromium only; not assistive-technology certification','Public production HTTPS and OS isolation not qualified here']}
(out/'qualification.json').write_text(json.dumps(index,indent=2)+'\n')
print('PASS:',len(checks),'real browser views;',len(accessibility),'axe pages; desktop/mobile/no-JS; no external requests or page errors.')
