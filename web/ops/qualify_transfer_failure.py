#!/usr/bin/env python3
"""Interrupt an exact owned SFTP SSH child before any native launch; no mocks."""
import argparse,http.cookiejar,json,os,secrets,signal,subprocess,sys,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Run,Target,BuildRelease,ExecutorSlot
from control.engine import run_path
from resmgrcheck.workflow import inspect_execution

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
   _,body=self.get(path);p=Inputs();p.feed(body);csrf=p.data.get('csrfmiddlewaretoken','')
  request=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(request,timeout=15) as r:return r.geturl(),r.read().decode()

def descendants(parent):
 result=[];todo=[parent]
 while todo:
  p=todo.pop()
  try:children=list(map(int,Path(f'/proc/{p}/task/{p}/children').read_text().split()))
  except OSError:continue
  result+=children;todo+=children
 return result

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);o=p.parse_args();out=Path(o.out).resolve();out.mkdir(parents=True,exist_ok=False)
c=json.loads((settings.PRIVATE_ROOT/'acceptance-account.json').read_text());target=Target.objects.get(project_id=c['project_id']);build=BuildRelease.objects.get(target=target,label='Original actual QNX build')
http=HTTP();http.post('/accounts/login/',{'login':c['email'],'password':c['password']});code=format_hotp_value(hotp_value(c['totp_secret'],int(time.time())//30));http.post('/accounts/2fa/authenticate/',{'code':code})
path='/app/projects/'+c['project_id']+'/runs/new/';data={'target':str(target.pk),'build':str(build.pk),'profile':'sensor','suite':'profile','fixture_mode':'fixed','idempotency_key':secrets.token_urlsafe(24)}
_,body=http.post(path,data);inputs=Inputs();inputs.feed(body);data.update(confirmed='on',confirmation=inputs.data['confirmation'])
url,_=http.post(path,data,csrf=inputs.data['csrfmiddlewaretoken']);identifier=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
with (out/'dispatcher.txt').open('wb') as log:
 worker=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 killed=None;deadline=time.monotonic()+12
 while worker.poll() is None and time.monotonic()<deadline:
  for pid in descendants(worker.pid):
   try:
    fd=os.pidfd_open(pid);cmd=Path(f'/proc/{pid}/cmdline').read_bytes();status=Path(f'/proc/{pid}/status').read_text()
    parent=int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
    parent_cmd=Path(f'/proc/{parent}/cmdline').read_bytes()
    if Path(f'/proc/{pid}').stat().st_uid==os.getuid() and b'ssh\x00' in cmd and b'scp\x00' in parent_cmd and b'/data/resmgrcheck/b-' in parent_cmd:
     signal.pidfd_send_signal(fd,signal.SIGKILL);killed=pid;os.close(fd);break
    os.close(fd)
   except (OSError,ProcessLookupError):continue
  if killed:break
  time.sleep(.002)
 assert killed,'No fault applied without a verified owned SFTP child'
 worker.wait(timeout=30);assert worker.returncode==0
run=Run.objects.get(pk=identifier);request,summary,_=inspect_execution(run_path(run))
assert run.state=='completed' and run.error_code=='prelaunch_infrastructure_error'
assert summary['execution_exit']==2 and all(row['verdict']=='NOT_RUN' for row in summary['cases'])
assert run.process_facts['local_child_exit_observed'] and run.process_facts['no_native_launch_observed']
assert not run.target_cleanup_verified and not list(run_path(run).glob('cases/*/bundle'))
assert not Path(f'/proc/{killed}').exists() and ExecutorSlot.objects.get(name='private-qnx').run_id is None
result={'kind':'real-web-sftp-failure','schema_version':1,'passed':True,'run_id':str(run.pk),'native_run_id':run.native_run_id,
 'fault':'SIGKILL to exact owned local SSH child of the active SFTP readback process; parent SCP/CLI exits observed',
 'canonical_summary':summary,'host_process_facts':run.process_facts,'native_test_launched':False,'native_cleanup_claimed':False,
 'required_cases_not_run':True,'slot_released_without_cleanup_claim':True,'automatic_retry':False,'production':False}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: real SFTP failure -> ERROR2 / required NOT_RUN; exact child exit, no native launch or cleanup claim; no automatic retry.')
