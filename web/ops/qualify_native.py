#!/usr/bin/env python3
"""Real current access-code workflow: fixed/broken/source-candidate replay/job."""
import argparse,hashlib,json,os,secrets,subprocess,sys,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from control.models import Project,Target,BuildRelease,Run
from control.engine import run_path
from control.storage import detail_cases,verify_inventory
from resmgrcheck.contracts import canonical
from http_support import administrator_client,issued_session,Inputs
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
admin,credential=administrator_client();project=Project.objects.get(pk=credential['project_id'])
target=Target.objects.get(project=project,approved=True,kind='managed-lab')
original=BuildRelease.objects.get(target=target,label='Original actual QNX build');candidate=BuildRelease.objects.get(target=target,label='Actual source correction39b99d7')
client,code_id=issued_session(admin,project,target,'Current fixed/broken/source-replay qualification',live=True)
observed=[]
def dispatch(url):
 identifier=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1];run=Run.objects.get(pk=identifier)
 assert run.actor_id is None and run.access_session_id and run.state=='queued'
 with (out/(identifier+'-worker.txt')).open('wb') as stream:
  worker=subprocess.Popen([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch','--once'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);worker.wait(timeout=640)
 assert worker.returncode==0;run.refresh_from_db();assert run.state=='completed' and run.target_cleanup_verified
 verify_inventory(run);cases=detail_cases(run)
 observed.append({'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'operation':run.operation,'profile':run.profile,'mode':run.fixture_mode,
  'execution_exit':run.summary['execution_exit'],'case_verdicts':[case['result']['verdict'] for case in cases],
  'bundle_ids':[case['manifest']['bundle_id'] for case in cases],'builds':[case['plan']['builds'] for case in cases],
  'native_cleanup_verified':True,'local_cli_exit_reaped':run.process_facts['local_child_exit_observed'],'inventory_version':verify_inventory(run)['schema_version']})
 return run

def launch(profile,mode):
 path='/app/projects/'+str(project.pk)+'/runs/new/'
 data={'target':str(target.pk),'build':str(original.pk),'profile':profile,'suite':'profile','fixture_mode':mode,'idempotency_key':secrets.token_urlsafe(24)}
 _,body=client.post(path,data);parsed=Inputs();parsed.feed(body);data.update(confirmed='on',confirmation=parsed.data['confirmation'])
 url,_=client.post(path,data,parsed.data['csrfmiddlewaretoken']);duplicate,_=client.post(path,data,parsed.data['csrfmiddlewaretoken']);assert duplicate==url
 return dispatch(url)
fixed=launch('sensor','fixed');broken=launch('sensor','ignore-unblock')
assert fixed.summary['execution_exit']==0 and broken.summary['execution_exit']==1
path='/app/runs/'+str(broken.pk)+'/replay/'
url,_=client.post(path,{'build':str(candidate.pk),'idempotency_key':secrets.token_urlsafe(24)})
after=dispatch(url);assert after.summary['execution_exit']==0
comparison=json.loads((run_path(after)/'comparison.json').read_text());assert comparison['label']=='fixed' and not comparison['fixture_mode_changed']
job=launch('job','fixed');assert job.summary['execution_exit']==0
admin.post('/administrator/codes/'+code_id+'/revoke/',{})
assert urllib.parse.urlsplit(client.get('/app/')[0]).path=='/access/'
result={'passed':True,'kind':'current-code-authorized-native-workflow','native_cases':4,'code_id':code_id,'raw_code_persisted':False,'cookie_state_persisted':False,
 'scope':'Actual administrator password/TOTP, admin-issued code, developer cookie/CSRF, durable queue and unchanged real QNX engine. Existing original and corrected binaries reused.',
 'runs':observed,'comparison_label':comparison['label'],'fixture_mode_changed':comparison['fixture_mode_changed'],
 'web_source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'web_source_dirty':bool(subprocess.check_output(['git','status','--porcelain','--','web'],cwd=ROOT))}
(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: four actual code-authorized QNX cases; fixed PASS, planted FAIL, same-setting source-candidate replay PASS/fixed, job PASS. No raw code/cookie saved.')
