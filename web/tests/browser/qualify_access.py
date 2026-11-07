#!/usr/bin/env python3
"""Actual administrator MFA and code-browser workflow. Never saves raw codes/cookies."""
import argparse,base64,hashlib,hmac,json,struct,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:8431'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credential=json.loads((ROOT/'.local/web/private/acceptance-administrator.json').read_text())
refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
axe=(ROOT/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text()
def totp():
 value=hmac.new(base64.b32decode(credential['totp_secret']),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=value[-1]&15
 return str((struct.unpack('>I',value[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
views=[];audits=[];screenshots=[]
with sync_playwright() as driver:
 browser=driver.chromium.launch();admin=browser.new_context(viewport={'width':1440,'height':1000});page=admin.new_page()
 page.goto(BASE+'/administrator/login/');page.locator('[name=login]').fill(credential['username']);page.locator('[name=password]').fill(credential['password'])
 page.get_by_role('button',name='Sign in as administrator').click();page.wait_for_url('**/administrator/2fa/authenticate/**')
 for attempt in range(3):
  page.locator('[name=code]').fill(totp());page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(200)
  if urlsplit(page.url).path=='/app/':break
  assert attempt<2,'MFA unavailable; credentials are never logged';time.sleep(30-time.time()%30+.1)
 # Real creation of a separate project for an actual cross-project browser denial.
 page.goto(BASE+'/app/organizations/'+refs['organization_id']+'/projects/new/')
 name='Browser access isolation '+str(int(time.time()));page.locator('[name=name]').fill(name)
 page.locator('form').filter(has=page.locator('[name=name]')).locator('button').click();page.wait_for_url('**/app/projects/*/')
 foreign_path=urlsplit(page.url).path
 # Show raw code once; retain it only in process memory. No screenshot/trace here.
 code_path='/administrator/organizations/'+refs['organization_id']+'/codes/'
 page.goto(BASE+code_path);page.locator('[name=description]').fill('Browser qualification: selected evidence only')
 page.locator('[name=projects]').select_option([refs['project_id']]);page.locator('[name=targets]').select_option([refs['target_id']])
 page.locator('[name=evidence]').select_option([refs['broken'],refs['replay'],refs['job']]);page.locator('[name=can_download]').check()
 page.locator('[name=max_sessions]').fill('2');page.locator('[name=max_redemptions]').fill('3')
 page.get_by_role('button',name='Generate access code').click();raw=page.locator('#new-access-code').inner_text().strip()
 assert raw.startswith('rmc_') and len(raw)==80
 page.get_by_role('link',name='Manage permissions and sessions').click();code_detail=urlsplit(page.url).path
 assert raw not in page.locator('body').inner_text()
 # A fresh GET cannot retrieve the generated value.
 page.goto(BASE+code_path);assert page.locator('#new-access-code').count()==0
 page.goto(BASE+code_detail)
 sessions=[]
 for mode,width,javascript in [('desktop',1440,True),('mobile-no-js',390,False)]:
  context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript);document=context.new_page();external=[]
  document.on('request',lambda request:external.append(request.url) if urlsplit(request.url).scheme in {'http','https'} and not request.url.startswith(BASE+'/') else None)
  document.goto(BASE+'/access/');document.locator('[name=code]').fill(raw);document.get_by_role('button',name='Open permitted workspace').click();document.wait_for_url('**/app/')
  assert document.locator('[name=code]').count()==0
  routes={'overview':'/app/','projects':'/app/projects/','targets':'/app/targets/','history':'/app/runs/',
   'project':'/app/projects/'+refs['project_id']+'/','failed-run':'/app/runs/'+refs['broken']+'/',
   'replay':'/app/runs/'+refs['replay']+'/','job':'/app/runs/'+refs['job']+'/',
   'compare':'/app/compare/?before='+refs['broken']+'&after='+refs['replay'],'session':'/app/session/'}
  for label,route in routes.items():
   response=document.goto(BASE+route,wait_until='networkidle');assert response.status==200,(label,mode,response.status)
   assert document.evaluate('document.documentElement.scrollWidth<=innerWidth'),(label,mode,'overflow')
   assert not external,(label,'external request')
   if label=='session':
    identifier=document.locator('dl dd code').first.inner_text();sessions.append((context,document,identifier))
   if mode=='desktop':
    document.evaluate(axe)
    findings=document.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
    audits.append({'page':label,'violations':findings});assert not [v for v in findings if v['impact'] in {'critical','serious'}],(label,findings)
   if label in {'overview','failed-run','session'}:
    path=out/(mode+'-'+label+'.png');document.screenshot(path=str(path));screenshots.append(path.name)
   views.append({'audience':'access-code','page':label,'width':width,'javascript':javascript,'status':200})
  for label,route in [('foreign-project',foreign_path),('unselected-evidence','/app/runs/'+refs['fixed']+'/'),('admin-management',code_path),('native-launch','/app/projects/'+refs['project_id']+'/runs/new/'),('ai-disabled','/app/runs/'+refs['broken']+'/ai/')]:
   response=document.goto(BASE+route);assert response.status==404,(label,mode,response.status)
   views.append({'audience':'access-code','page':label,'width':width,'javascript':javascript,'status':404})
  document.goto(BASE+'/app/session/')
 # Active-session capacity denial with generic text and no reflected raw code.
 extra=browser.new_context();denied=extra.new_page();denied.goto(BASE+'/access/');denied.locator('[name=code]').fill(raw)
 denied.get_by_role('button',name='Open permitted workspace').click();assert 'Access denied' in denied.locator('main').inner_text()
 assert denied.locator('[name=code]').input_value()=='';extra.close();raw=None
 # Actual session revocation; the other context remains authorized.
 page.goto(BASE+code_detail);first_id=sessions[0][2]
 page.locator('form[action="/administrator/access-sessions/'+first_id+'/revoke/"]').get_by_role('button').click()
 sessions[0][1].goto(BASE+'/app/');assert urlsplit(sessions[0][1].url).path=='/access/'
 assert sessions[1][1].goto(BASE+'/app/').status==200
 page.goto(BASE+code_detail);page.get_by_role('button',name='Revoke this code immediately').click()
 sessions[1][1].goto(BASE+'/app/');assert urlsplit(sessions[1][1].url).path=='/access/'
 # Public routes work without JS; obsolete email/signup endpoints are absent.
 for width,javascript in [(1440,True),(390,False)]:
  context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript);document=context.new_page()
  for route in ['/access/','/administrator/login/','/demo/']:
   assert document.goto(BASE+route).status==200
   assert document.evaluate('document.documentElement.scrollWidth<=innerWidth')
   views.append({'audience':'anonymous','page':route,'width':width,'javascript':javascript,'status':200})
  for route in ['/accounts/signup/','/accounts/password/reset/','/administrator/signup/']:
   assert document.goto(BASE+route).status==404
  context.close()
 browser.close()
result={'passed':True,'kind':'actual-access-model-browser-qualification','browser':browser.version,'views':views,'accessibility':audits,'screenshots':screenshots,
 'administrator_actual_password_totp_login':True,'actual_admin_code_creation_single_display':True,'code_saved_to_disk':False,'cookie_state_saved_to_disk':False,
 'maximum_sessions_denial':True,'single_session_revocation':True,'code_revocation':True,'cross_project_evidence_denial':True,
 'legacy_email_routes_absent':True,'code_detail_path':code_detail,'foreign_project_path':foreign_path,'native_execution_performed':False,'provider_calls':0}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS:',len(views),'actual browser views; real administrator MFA/code creation/redemption/revocation; desktop/no-JS mobile; no code/cookie persistence.')
