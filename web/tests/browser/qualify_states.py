#!/usr/bin/env python3
"""Exercise real queued/cancel intent, unsupported onboarding and form-error UI."""
import argparse,base64,hashlib,hmac,json,os,struct,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:8431'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--existing-run');args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credentials=json.loads((ROOT/'.local/web/private/acceptance-account.json').read_text())
refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
def code():
 raw=hmac.new(base64.b32decode(credentials['totp_secret']),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=raw[-1]&15
 return str((struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
checks=[]
with sync_playwright() as driver:
 browser=driver.chromium.launch();context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page()
 page.goto(BASE+'/administrator/login/');page.locator('[name=login]').fill(credentials['username']);page.locator('[name=password]').fill(credentials['password'])
 page.get_by_role('button',name='Sign in as administrator',exact=True).click();page.wait_for_url('**/administrator/2fa/authenticate/**')
 for attempt in range(3):
  page.locator('[name=code]').fill(code());page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(200)
  if urlsplit(page.url).path=='/app/':break
  assert attempt<2,'MFA login unavailable';time.sleep(30-time.time()%30+.1)
 target_path='/app/projects/'+refs['project_id']+'/targets/'
 if args.existing_run:page.goto(BASE+'/app/runs/'+args.existing_run+'/')
 else:
  page.goto(BASE+target_path)
  page.get_by_role('button',name='Queue private inventory').first.click();page.wait_for_url('**/app/runs/*/')
 run_id=urlsplit(page.url).path.strip('/').split('/')[-1]
 for width,javascript in [(390,True),(1440,True),(390,False),(1280,False)]:
  view=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript,storage_state=context.storage_state())
  document=view.new_page();document.goto(page.url,wait_until='networkidle')
  assert document.locator('[data-job-state]').inner_text()=='queued'
  assert document.locator('[data-progress]').get_attribute('aria-live')=='polite'
  assert 'Inventory is not a service verdict' in document.locator('main').inner_text()
  assert document.evaluate('document.documentElement.scrollWidth<=innerWidth')
  document.screenshot(path=str(out/('queued-'+str(width)+'-'+str(javascript)+'.png')))
  checks.append({'state':'queued','width':width,'javascript':javascript,'native_verdict_established':False});view.close()
 page.get_by_role('button',name='Request cancellation').click();page.wait_for_url('**/app/runs/*/')
 assert 'Requested: Yes' in page.locator('main').inner_text()
 # A web cancel records intent. A separate dispatcher observes it before any CLI launch.
 page.goto(BASE+target_path);page.locator('form').filter(has=page.locator('[name=name]')).locator('[name=name]').fill('Browser qualification: dedicated runner requested')
 page.get_by_role('button',name='Request target onboarding').click();page.wait_for_url('**/targets/')
 assert 'UNSUPPORTED until dedicated runner approval' in page.locator('main').inner_text()
 page.goto(BASE+'/app/projects/'+refs['project_id']+'/runs/new/')
 page.locator('[name=idempotency_key]').evaluate("e=>e.value='invalid'")
 page.locator('form').filter(has=page.locator('[name=idempotency_key]')).evaluate('e=>e.noValidate=true')
 page.locator('form').filter(has=page.locator('[name=idempotency_key]')).locator('button').click()
 assert page.locator('.errorlist').count()>0
 page.screenshot(path=str(out/'field-errors-mobile.png'))
 browser.close()
(out/'qualification.json').write_text(json.dumps({'passed':True,'queued_job_id':run_id,'checks':checks,
 'actual_form_errors':True,'actual_unsupported_target_request':True,'cancel_intent_observed':True,
 'native_execution_performed':False,'dispatcher_cancel_outcome':'pending separate check'},indent=2)+'\n')
print('PASS: four queued browser views, actual cancel intent, unsupported onboarding and field errors; no native launch.')
