#!/usr/bin/env python3
"""Real access-code HTTP -> durable worker -> QNX, with before/in-flight revocation.

Raw codes and cookies remain only in memory. No native rebuild or mock service.
"""
import argparse,hashlib,http.cookiejar,json,os,secrets,subprocess,sys,time,uuid,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Run,Target,BuildRelease,AccessCode,AccessSession,Artifact
from control.engine import run_path,registry
from control.storage import verify_inventory,detail_cases
from resmgrcheck.transport import Target as EngineTarget,Transport

class Inputs(HTMLParser):
 def __init__(self):super().__init__();self.data={};self.secret=False;self.raw=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='input' and 'name' in d:self.data[d['name']]=d.get('value','')
  if tag=='pre' and d.get('id')=='new-access-code':self.secret=True
 def handle_endtag(self,tag):
  if tag=='pre':self.secret=False
 def handle_data(self,data):
  if self.secret:self.raw.append(data)
class HTTP:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,path):
  with self.opener.open('http://127.0.0.1:8431'+path,timeout=15) as r:return r.geturl(),r.read().decode()
 def post(self,path,data,csrf=None):
  if csrf is None:
   _,body=self.get(path);p=Inputs();p.feed(body);csrf=p.data['csrfmiddlewaretoken']
  req=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(req,timeout=15) as r:return r.geturl(),r.read().decode()

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credential=json.loads((settings.PRIVATE_ROOT/'acceptance-administrator.json').read_text())
project_id=credential['project_id'];org_id=credential['organization_id']
target=Target.objects.get(project_id=project_id,approved=True,kind='managed-lab');build=BuildRelease.objects.get(target=target,label='Original actual QNX build')
admin=HTTP();admin.post('/administrator/login/',{'login':credential['username'],'password':credential['password']})
for attempt in range(3):
 code=format_hotp_value(hotp_value(credential['totp_secret'],int(time.time())//30));url,_=admin.post('/administrator/2fa/authenticate/',{'code':code})
 if urllib.parse.urlsplit(url).path=='/app/':break
 assert attempt<2,'MFA unavailable';time.sleep(30-time.time()%30+.1)

def issued(description):
 _,body=admin.post('/administrator/organizations/'+org_id+'/codes/',{'description':description,'projects':project_id,'targets':str(target.pk),
     'allow_live':'on','can_download':'on','all_evidence':'on','max_sessions':'1','max_redemptions':'1'})
 p=Inputs();p.feed(body);raw=''.join(p.raw).strip();assert raw.startswith('rmc_')
 identifier=raw.split('_')[1];developer=HTTP();url,_=developer.post('/access/',{'code':raw});assert urllib.parse.urlsplit(url).path=='/app/'
 raw=None;body=None;p=None
 return developer,str(uuid.UUID(hex=identifier))

def queued(developer,profile):
 path='/app/projects/'+project_id+'/runs/new/'
 data={'target':str(target.pk),'build':str(build.pk),'profile':profile,'suite':'profile','fixture_mode':'fixed','idempotency_key':secrets.token_urlsafe(24)}
 _,body=developer.post(path,data);p=Inputs();p.feed(body);data.update(confirmed='on',confirmation=p.data['confirmation'])
 url,_=developer.post(path,data,p.data['csrfmiddlewaretoken']);duplicate,_=developer.post(path,data,p.data['csrfmiddlewaretoken']);assert duplicate==url
 identifier=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
 run=Run.objects.get(pk=identifier);assert run.access_session_id and run.actor_id is None and run.state=='queued'
 return run

def worker(label):
 stream=(out/(label+'-worker.txt')).open('wb')
 process=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
 return process,stream

developer,code_id=issued('Actual code-authorized QNX qualification')
records=[]
for profile in ['sensor','job']:
 run=queued(developer,profile);process,stream=worker(profile);pending=None
 if profile=='job':
  binding=registry(target,build);transport=Transport(EngineTarget.read(binding.alias,binding.config));helper=build.manifest['directory']+'/targetctl'
  deadline=time.monotonic()+30
  while process.poll() is None and time.monotonic()<deadline:
   raw=transport.command(helper,'read-run',run.native_run_id+'-timeout','events.jsonl',exits=(0,2));events=[]
   for line in raw.splitlines():
    try:events.append(json.loads(line))
    except ValueError:break
   timed=[event for event in events if event.get('event')=='deadline' and event.get('data',{}).get('operation')=='timed']
   if timed:
    candidates=[(index,event) for index,event in enumerate(events) if event.get('event')=='pending' and event.get('data',{}).get('client_pid')==timed[-1]['pid']]
    if candidates:
     pending={'frame':candidates[-1][0],'event':candidates[-1][1]};break
   time.sleep(.01)
  assert pending,'No in-flight revocation claim without an observed exact native timed worker pending'
  # CSRF comes from the real management page, never from a GET with side effects.
  _,body=admin.get('/administrator/codes/'+code_id+'/');parsed=Inputs();parsed.feed(body)
  admin.post('/administrator/codes/'+code_id+'/revoke/',{},parsed.data['csrfmiddlewaretoken'])
  url,_=developer.get('/app/');assert urllib.parse.urlsplit(url).path=='/access/'
 process.wait(timeout=640);stream.close();assert process.returncode==0
 run.refresh_from_db();assert run.state=='completed' and run.summary['execution_exit']==0 and run.target_cleanup_verified
 verify_inventory(run);cases=detail_cases(run);assert len(cases)==1 and cases[0]['result']['verdict']=='PASS'
 assert run.process_facts['local_child_exit_observed']
 records.append({'profile':profile,'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'access_session_id':str(run.access_session_id),
   'canonical_verdict':'PASS','bundle_id':cases[0]['manifest']['bundle_id'],'native_builds':cases[0]['plan']['builds'],
   'native_cleanup_verified':True,'local_cli_exit_reaped':True,'duplicate_http_intent_deduped':True,
   'revoked_after_observed_native_pending':bool(pending),'pending_observation':pending})

# Separately reject an actually queued job before any engine child is started.
second,second_code=issued('Revoked queued job qualification');withheld=queued(second,'sensor')
_,body=admin.get('/administrator/codes/'+second_code+'/');p=Inputs();p.feed(body);admin.post('/administrator/codes/'+second_code+'/revoke/',{},p.data['csrfmiddlewaretoken'])
process,stream=worker('revoked-before-start');process.wait(timeout=20);stream.close();assert process.returncode==0
withheld.refresh_from_db();assert withheld.state=='rejected' and withheld.started_at is None and not run_path(withheld).exists()
assert withheld.error_code=='actor_authorization_revoked' and not withheld.target_cleanup_verified
result={'passed':True,'kind':'actual-code-session-qnx-qualification','native_cases':2,'runs':records,
 'revoked_queued_job':{'web_run_id':str(withheld.pk),'native_run_id':withheld.native_run_id,'state':withheld.state,'reason':withheld.error_code,
     'started_at':None,'local_output_directory_exists':False,'native_cleanup_claimed':False,'native_verdict_established':False},
 'raw_codes_saved':False,'cookie_state_saved':False,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'web_source_dirty':bool(subprocess.check_output(['git','status','--porcelain','--','web'],cwd=ROOT)),
 'scope':'Actual code-created browser authority, real private dispatcher, unchanged genuine QNX engine. Native continuation after in-flight code revocation is supervised cleanup/collection authority, never fresh user authorization.'}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: two actual code-authorized QNX cases; observed-pending in-flight revocation preserves bounded collection; queued revoked job rejected before any native launch.')
