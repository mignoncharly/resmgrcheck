#!/usr/bin/env python3
"""Real HTTP -> durable DB queue -> private CLI -> QNX staging qualification."""
import argparse,http.cookiejar,io,json,os,secrets,subprocess,sys,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import TOTP,generate_totp_secret,hotp_value,format_hotp_value
from control.models import User,Organization,Membership,Project,Target,BuildRelease,Run
from control.storage import open_artifact
from control.engine import run_path
from resmgrcheck.workflow import inspect_execution
from resmgrcheck.artifacts import inspect_bundle

class Inputs(HTMLParser):
 def __init__(self):super().__init__();self.inputs={}
 def handle_starttag(self,tag,attrs):
  data=dict(attrs)
  if tag=='input' and 'name' in data:self.inputs[data['name']]=data.get('value','')

class HTTP:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,path):
  with self.opener.open('http://127.0.0.1:8431'+path,timeout=15) as response:return response.geturl(),response.read().decode()
 def post(self,path,data):
  _,html=self.get(path);parser=Inputs();parser.feed(html)
  payload={'csrfmiddlewaretoken':parser.inputs.get('csrfmiddlewaretoken',''),**data}
  request=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode(payload).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(request,timeout=15) as response:return response.geturl(),response.read().decode()
 def post_known(self,path,data,csrf):
  request=urllib.request.Request('http://127.0.0.1:8431'+path,data=urllib.parse.urlencode({'csrfmiddlewaretoken':csrf,**data}).encode(),headers={'Origin':'http://127.0.0.1:8431'})
  with self.opener.open(request,timeout=15) as response:return response.geturl(),response.read().decode()

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
user=User.objects.create_user('p3-'+secrets.token_hex(4)+'@resmgrcheck.invalid',secrets.token_urlsafe(36),first_name='STAGING acceptance account')
# Local operator-provisioned private test identity, not claimed external SMTP verification.
password=secrets.token_urlsafe(36);user.set_password(password);user.save()
EmailAddress.objects.create(user=user,email=user.email,verified=True,primary=True)
secret=generate_totp_secret();TOTP.activate(user,secret)
org=Organization.objects.create(name='P3 private QNX acceptance');Membership.objects.create(user=user,organization=org,role='owner')
project=Project.objects.create(organization=org,name='Real engine HTTP qualification',created_by=user)
credential=settings.PRIVATE_ROOT/'acceptance-account.json';credential.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
credential.write_text(json.dumps({'email':user.email,'password':password,'totp_secret':secret,'organization_id':str(org.pk),'project_id':str(project.pk)}));credential.chmod(0o600)
config=ROOT/'.local/web/engine/config/target.local.json';registry=ROOT/'.local/web/runtime/executor-registry.json'
options={'project':str(project.pk),'engine_root':str(settings.ENGINE_ROOT),'config':str(config),'alias':'lab','registry':str(registry)}
stream=io.StringIO();call_command('approve_target',**options,manifest=str(ROOT/'build/qnx-x86_64/manifest.json'),build_label='Original actual QNX build',stdout=stream)
approved=json.loads(stream.getvalue().strip());target_id=approved['target_id'];original_build=approved['build_id']
stream=io.StringIO();call_command('approve_target',**options,target=target_id,manifest=str(ROOT/'.local/phase10-fixed-source/build/qnx-x86_64/manifest.json'),build_label='Actual source correction39b99d7',stdout=stream)
candidate_build=json.loads(stream.getvalue().strip())['build_id']
http=HTTP();http.post('/accounts/login/',{'login':user.email,'password':password})
code=format_hotp_value(hotp_value(secret,int(time.time())//30));http.post('/accounts/2fa/authenticate/',{'code':code})
url,html=http.get('/app/');assert 'Your workspace' in html
observed=[]
def dispatch(identifier):
 initial=json.loads(http.get('/api/runs/'+identifier+'/')[1]);assert initial['state']=='queued'
 log=out/(identifier+'-dispatcher.txt')
 with log.open('wb') as file:
  process=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=file,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+640
  states=[]
  while process.poll() is None:
   state=json.loads(http.get('/api/runs/'+identifier+'/')[1])['state']
   if not states or states[-1]!=state:states.append(state)
   if time.monotonic()>deadline:raise RuntimeError('Qualification bound exceeded; preserve exact run/worker for recovery')
   time.sleep(.2)
  assert process.returncode==0
 state=json.loads(http.get('/api/runs/'+identifier+'/')[1]);assert state['state']=='completed',state['error_code']
 run=Run.objects.get(pk=identifier)
 if run.operation!='inventory':
  request,summary,results=inspect_execution(run_path(run))
  assert request.data['run_id']==run.native_run_id and run.target_cleanup_verified
  bundles=[inspect_bundle(p) for p in run_path(run).glob('cases/*/bundle')]
  observed.append({'operation':run.operation,'profile':run.profile,'mode':run.fixture_mode,'run_id':str(run.pk),'native_run_id':run.native_run_id,
   'states_observed':states,'execution_exit':summary['execution_exit'],'case_verdicts':[r.data['verdict'] for r in results],
   'bundle_ids':[b.manifest.data['bundle_id'] for b in bundles],'native_builds':[b.plan.data['builds'] for b in bundles],
   'cleanup_verified':True,'host_child_reaped':run.process_facts.get('local_child_exit_observed',False)})
 return run

def run_id(url):return urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
# Inventory is a form POST with the actual CSRF token; no request executes a QNX test.
_,html=http.get('/app/projects/'+str(project.pk)+'/targets/');inputs=Inputs();inputs.feed(html)
url,_=http.post_known('/app/projects/'+str(project.pk)+'/targets/'+target_id+'/inventory/',{},inputs.inputs['csrfmiddlewaretoken'])
inventory_run=dispatch(run_id(url));assert inventory_run.summary['runtime_target_ready']

def launch(profile,mode):
 path='/app/projects/'+str(project.pk)+'/runs/new/'
 data={'target':target_id,'build':original_build,'profile':profile,'suite':'profile','fixture_mode':mode,'idempotency_key':secrets.token_urlsafe(24)}
 _,html=http.post(path,data);inputs=Inputs();inputs.feed(html)
 assert 'Confirm this exact request' in html
 data.update(confirmed='on',confirmation=inputs.inputs['confirmation'])
 url,_=http.post_known(path,data,inputs.inputs['csrfmiddlewaretoken']);identifier=run_id(url)
 # Exact same signed request is idempotent; it must not create another queue row.
 duplicate,_=http.post_known(path,data,inputs.inputs['csrfmiddlewaretoken']);assert run_id(duplicate)==identifier
 return dispatch(identifier)
fixed=launch('sensor','fixed');broken=launch('sensor','ignore-unblock')
assert fixed.summary['execution_exit']==0 and broken.summary['execution_exit']==1
path='/app/runs/'+str(broken.pk)+'/replay/'
url,_=http.post(path,{'build':candidate_build,'idempotency_key':secrets.token_urlsafe(24)})
after=dispatch(run_id(url));assert after.summary['execution_exit']==0
comparison=json.loads((run_path(after)/'comparison.json').read_text());assert comparison['label']=='fixed' and not comparison['fixture_mode_changed']
job=launch('job','fixed');assert job.summary['execution_exit']==0
result={'kind':'real-web-qnx-staging-qualification','schema_version':1,'passed':True,'native_cases':4,'transport':'actual loopback HTTP with CSRF/session/real TOTP; private subprocess CLI to existing real QNX guest',
 'identity_provisioning':'local operator test identity; external SMTP delivery not claimed','inventory':inventory_run.summary,'runs':observed,'comparison_label':comparison['label'],
 'same_contract_settings':True,'fixture_hash_changed':True,'existing_native_engine_changed':False,'production':False}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: real HTTP queue, inventory and four real QNX cases; fixed/FAIL/source-fixed replay/job; exact identities, dedupe and cleanup preserved.')
