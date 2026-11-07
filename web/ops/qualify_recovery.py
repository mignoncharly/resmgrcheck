#!/usr/bin/env python3
"""Pause one exact owned collection SSH child; prove real QNX run-ID recovery."""
import argparse,http.cookiejar,json,os,signal,subprocess,sys,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from django.utils import timezone
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Run,Target,BuildRelease,ExecutorSlot
from control.engine import registry,run_path
from resmgrcheck.transport import Target as EngineTarget,Transport
from resmgrcheck.artifacts import inspect_bundle,sha256

class Inputs(HTMLParser):
 def __init__(self):super().__init__();self.data={}
 def handle_starttag(self,t,a):
  d=dict(a)
  if t=='input' and 'name' in d:self.data[d['name']]=d.get('value','')
class HTTP:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,path):
  with self.opener.open('http://127.0.0.1:8431'+path,timeout=15) as r:return r.geturl(),r.read().decode()
 def post(self,path,data,csrf=None):
  if csrf is None:
   _,body=self.get(path);parser=Inputs();parser.feed(body);csrf=parser.data.get('csrfmiddlewaretoken','')
  req=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(req,timeout=15) as r:return r.geturl(),r.read().decode()

def descendants(parent):
 result=[];queue=[parent]
 while queue:
  pid=queue.pop()
  try:children=[int(v) for v in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
  except OSError:continue
  result.extend(children);queue.extend(children)
 return result

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credential=json.loads((settings.PRIVATE_ROOT/'acceptance-account.json').read_text())
project_id=credential['project_id'];target=Target.objects.get(project_id=project_id)
build=BuildRelease.objects.filter(target=target,label='Original actual QNX build').get()
http=HTTP();http.post('/accounts/login/',{'login':credential['email'],'password':credential['password']})
code=format_hotp_value(hotp_value(credential['totp_secret'],int(time.time())//30));http.post('/accounts/2fa/authenticate/',{'code':code})
import secrets
path='/app/projects/'+project_id+'/runs/new/'
data={'target':str(target.pk),'build':str(build.pk),'profile':'sensor','suite':'profile','fixture_mode':'ignore-unblock','idempotency_key':secrets.token_urlsafe(24)}
_,body=http.post(path,data);inputs=Inputs();inputs.feed(body)
data.update(confirmed='on',confirmation=inputs.data['confirmation'])
url,_=http.post(path,data,csrf=inputs.data['csrfmiddlewaretoken']);identifier=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
run=Run.objects.get(pk=identifier);binding=registry(target,build)
transport=Transport(EngineTarget.read(binding.alias,binding.config));helper=build.manifest['directory']+'/targetctl'
case_id=run.native_run_id+'-timeout'
log=(out/'first-dispatcher.txt').open('wb')
worker=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
seen_pending=None;before_supervisor=None;paused=None;deadline=time.monotonic()+20
while worker.poll() is None and time.monotonic()<deadline:
 raw=transport.command(helper,'read-run',case_id,'events.jsonl',exits=(0,2))
 events=[]
 for line in raw.splitlines():
  try:events.append(json.loads(line))
  except ValueError:break
 timed=[(i,e) for i,e in enumerate(events) if e.get('event')=='deadline' and e.get('data',{}).get('operation')=='timed']
 if timed:
  candidates=[(i,e) for i,e in enumerate(events) if e.get('event')=='pending' and e.get('data',{}).get('client_pid')==timed[-1][1]['pid']]
  if candidates:seen_pending={'event_ref':candidates[-1][0],'event':candidates[-1][1]}
 if seen_pending:
  status=transport.command(helper,'read-run',case_id,'status.json',exits=(0,2))
  if status:before_supervisor=json.loads(status)['supervisor_pid']
  for child in descendants(worker.pid):
   try:
    fd=os.pidfd_open(child);cmd=Path(f'/proc/{child}/cmdline').read_bytes()
    if Path(f'/proc/{child}').stat().st_uid==os.getuid() and b'ssh\x00' in cmd and b'read-run' in cmd and case_id.encode() in cmd:
     signal.pidfd_send_signal(fd,signal.SIGSTOP);paused=child;os.close(fd);break
    os.close(fd)
   except (OSError,ProcessLookupError):continue
  if paused:break
 time.sleep(.01)
assert seen_pending and paused and before_supervisor,'No fault injected without actual pending and exact owned SSH identity'
worker.wait(timeout=25);log.close();assert worker.returncode==0
run.refresh_from_db();assert run.state=='launch_uncertain';assert not run.target_cleanup_verified
initial_summary=run.summary;initial_id=run.native_run_id
partial=run_path(run)/'cases/timeout/partial-events.jsonl'
assert partial.is_file() and partial.stat().st_size>0
partial_hash=sha256(partial.read_bytes())
assert run.process_facts['local_child_exit_observed'] and run.process_facts['local_child_returncode']==2
commands=json.loads((run_path(run)/'diagnostics/commands.json').read_text())
assert any(row.get('error')=='TransportError' and row.get('exit')==-9 for row in commands)
# The original engine killed and reaped its own exact stopped SSH child at its bound.
assert not Path(f'/proc/{paused}').exists()
slot=ExecutorSlot.objects.get(name='private-qnx');remaining=max(0,(slot.expires_at-timezone.now()).total_seconds())
assert remaining<=31
end=time.monotonic()+remaining+.2
while time.monotonic()<end:time.sleep(min(.2,end-time.monotonic()))
with (out/'recovery-dispatcher.txt').open('wb') as file:
 subprocess.run([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=file,stderr=subprocess.STDOUT,check=True,timeout=60)
run.refresh_from_db();assert run.state=='completed' and run.native_run_id==initial_id and run.target_cleanup_verified
bundle=inspect_bundle(run_path(run)/'cases/timeout/bundle')
assert bundle.status['supervisor_pid']==before_supervisor
assert bundle.result.data['verdict']=='FAIL'
assert {'cancellation_not_completed','pending_state_not_released'}<=set(bundle.result.data['reasons'])
assert any(sha256(p.read_bytes())==partial_hash for p in run_path(run).rglob('*') if p.is_file()),'Initial partial bytes lost'
assert run.incidents and ExecutorSlot.objects.get(name='private-qnx').run_id is None
result={'kind':'real-qnx-web-recovery','schema_version':1,'passed':True,'run_id':str(run.pk),'native_run_id':run.native_run_id,
 'fault':'SIGSTOP to exact owned local collection SSH child after actual native timed pending; engine timeout kills/reaps it',
 'pending':seen_pending,'local_transport_timeout_and_reap_observed':True,'initial_state':'launch_uncertain','initial_summary':initial_summary,
 'initial_partial_sha256':partial_hash,'initial_partial_bytes_preserved':True,'automatic_relaunch':False,'recovery_operation':'collect same run ID after real lease expiry',
 'same_supervisor_pid':before_supervisor,'final_bundle_id':bundle.manifest.data['bundle_id'],'final_verdict':bundle.result.data['verdict'],
 'final_reasons':bundle.result.data['reasons'],'final_cleanup_ok':bundle.status['cleanup_ok'],'incidents_retained':run.incidents,'production':False}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: actual pending, bounded SSH timeout/reap, partial ERROR evidence, same-ID/same-supervisor recovery, preserved FAIL reasons and cleanup; no relaunch.')
