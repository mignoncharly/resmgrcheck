#!/usr/bin/env python3
"""Download real authorized staging bundles, verify identities/hashes and open offline."""
import argparse,base64,hashlib,hmac,json,os,posixpath,struct,time,zipfile
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:8431'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credentials=json.loads((ROOT/'.local/web/private/acceptance-account.json').read_text());refs=json.loads((ROOT/'.local/web/private/browser-manifest.json').read_text())
def code():
 raw=hmac.new(base64.b32decode(credentials['totp_secret']),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest();offset=raw[-1]&15
 return str((struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  self.links.extend(value for key,value in attrs if key in {'href','src'} and value)
checks=[];views=[];links=0
with sync_playwright() as driver:
 browser=driver.chromium.launch();context=browser.new_context();page=context.new_page()
 page.goto(BASE+'/accounts/login/');page.locator('[name=login]').fill(credentials['email']);page.locator('[name=password]').fill(credentials['password'])
 page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_url('**/accounts/2fa/authenticate/**')
 for attempt in range(3):
  page.locator('[name=code]').fill(code());page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_timeout(200)
  if urlsplit(page.url).path=='/app/':break
  assert attempt<2,'MFA login unavailable';time.sleep(30-time.time()%30+.1)
 for label in ['fixed','broken','replay','job','transfer']:
  page.goto(BASE+'/app/runs/'+refs[label]+'/')
  with page.expect_download() as pending:page.get_by_role('link',name='Download verified offline ZIP').click()
  archive=out/(label+'.zip');pending.value.save_as(str(archive));extract=out/(label+'-extracted')
  with zipfile.ZipFile(archive) as bundle:
   names=bundle.namelist()
   assert len(names)==len(set(names)) and all(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name for name in names)
   index=json.loads(bundle.read('EXPORT.json'));assert index['web_run_id']==refs[label]
   for name,record in index['files'].items():
    raw=bundle.read(name);assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
    assert not raw.startswith(b'\x7fELF')
   for name in names:
    if not name.endswith('.html'):continue
    parser=Links();parser.feed(bundle.read(name).decode())
    for value in parser.links:
     target=urlsplit(value);assert not target.scheme and not target.netloc
     if target.path:assert posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(target.path))) in names
     links+=1
   bundle.extractall(extract)
  checks.append({'label':label,'web_run_id':index['web_run_id'],'native_run_id':index['native_run_id'],'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'verified_files':len(index['files']),
    'preserved_history_files':sum('/history/' in name for name in index['files'])})
  for width,javascript in [(1440,True),(390,False)]:
   view=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=javascript);document=view.new_page();external=[]
   document.on('request',lambda request:external.append(request.url) if urlsplit(request.url).scheme in {'http','https'} else None)
   document.goto((extract/'evidence/report.html').as_uri(),wait_until='networkidle')
   assert document.locator('h1').count()==1 and not external
   assert document.evaluate('document.documentElement.scrollWidth<=innerWidth')
   document.screenshot(path=str(out/(label+'-'+str(width)+'.png')))
   views.append({'label':label,'width':width,'javascript':javascript,'offline':True,'external_requests':external});view.close()
 browser.close()
(out/'qualification.json').write_text(json.dumps({'passed':True,'downloads':checks,'offline_views':views,'local_references_checked':links,'native_execution_performed':False},indent=2)+'\n')
print('PASS:',len(checks),'real HTTP evidence downloads;',len(views),'offline browser views;',links,'local references verified; original hashes retained.')
