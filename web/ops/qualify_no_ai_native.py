#!/usr/bin/env python3
"""Actual two-service HTTP/QNX smoke after evidence/AI integration, with AI disabled."""
import argparse,http.cookiejar,json,os,secrets,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Run,Target,BuildRelease,AIAnalysis,AIProviderState
from control.engine import run_path
from control.storage import verify_inventory,detail_cases

class Inputs(HTMLParser):
 def __init__(self):super().__init__();self.data={}
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='input' and 'name' in d:self.data[d['name']]=d.get('value','')
class HTTP:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,path):
  with self.opener.open('http://127.0.0.1:8431'+path,timeout=15) as response:return response.geturl(),response.read().decode()
 def post(self,path,data,csrf=None):
  if csrf is None:
   _,body=self.get(path);parsed=Inputs();parsed.feed(body);csrf=parsed.data['csrfmiddlewaretoken']
  request=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(request,timeout=15) as response:return response.geturl(),response.read().decode()

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
assert not AIProviderState.objects.filter(available=True).exists(),'This qualifier requires the actual disabled-provider state'
initial_analyses=AIAnalysis.objects.count()
credential=json.loads((settings.PRIVATE_ROOT/'acceptance-account.json').read_text())
target=Target.objects.get(project_id=credential['project_id'],approved=True,kind='managed-lab')
build=BuildRelease.objects.get(target=target,label='Original actual QNX build')
http=HTTP();http.post('/accounts/login/',{'login':credential['email'],'password':credential['password']})
for attempt in range(3):
 code=format_hotp_value(hotp_value(credential['totp_secret'],int(time.time())//30))
 try:url,_=http.post('/accounts/2fa/authenticate/',{'code':code})
 except urllib.error.HTTPError as error:
  if error.code!=400:raise
  url='not-authenticated';error.close()
 if urllib.parse.urlsplit(url).path=='/app/':break
 assert attempt<2,'MFA login unavailable';time.sleep(30-time.time()%30+.1)
records=[]
for profile in ['sensor','job']:
 path='/app/projects/'+credential['project_id']+'/runs/new/'
 data={'target':str(target.pk),'build':str(build.pk),'profile':profile,'suite':'profile','fixture_mode':'fixed','idempotency_key':secrets.token_urlsafe(24)}
 _,body=http.post(path,data);parsed=Inputs();parsed.feed(body);data.update(confirmed='on',confirmation=parsed.data['confirmation'])
 url,_=http.post(path,data,parsed.data['csrfmiddlewaretoken']);identifier=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
 duplicate,_=http.post(path,data,parsed.data['csrfmiddlewaretoken']);assert duplicate==url
 run=Run.objects.get(pk=identifier);assert run.state=='queued'
 with (out/(profile+'-worker.txt')).open('wb') as stream:
  worker=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  worker.wait(timeout=640)
 assert worker.returncode==0
 run.refresh_from_db();assert run.state=='completed' and run.summary['execution_exit']==0 and run.target_cleanup_verified
 verify_inventory(run);cases=detail_cases(run);assert len(cases)==1 and cases[0]['result']['verdict']=='PASS'
 assert run.process_facts['local_child_exit_observed']
 record={'profile':profile,'native_run_id':run.native_run_id,'web_run_id':str(run.pk),'verdict':'PASS','case_id':'timeout',
   'source_builds':cases[0]['plan']['builds'],'bundle_id':cases[0]['manifest']['bundle_id'],'native_cleanup_verified':True,
   'local_cli_exit_and_reap_observed':True,'inventory_version':verify_inventory(run)['schema_version'],'http_duplicate_deduped':True}
 records.append(record)
 (out/'qualification.json').write_text(json.dumps({'passed':True,'provider_disabled':True,'actual_native_cases':len(records),'runs':records,
    'scope':'Actual HTTP/CSRF/password/TOTP queue to existing QNX engine; native binaries reused; AI unavailable. Not a new full release matrix.'},indent=2)+'\n')
 print('Actual QNX smoke:',profile,'PASS; native cleanup, local CLI reap and v2 evidence verified.',flush=True)
assert AIAnalysis.objects.count()==initial_analyses
