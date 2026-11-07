#!/usr/bin/env python3
"""Real consented provider qualification; requires dedicated local configuration.

Only genuine existing QNX evidence and the published original MIT correction.
No new QNX execution, unrelated credentials or mock AI answers.
"""
import argparse,hashlib,http.cookiejar,json,secrets,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'web'),str(ROOT)]
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django
django.setup()
from django.conf import settings
from allauth.mfa.totp.internal.auth import hotp_value,format_hotp_value
from control.models import Run,AIAnalysis,SourceSubmission,Project,Artifact
from control.ai_provider import configuration
from control.ai_worker import refresh_provider
from control.ai_evidence import source_upload
from resmgrcheck.contracts import canonical

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
# Fail before creating requests or calling any provider if configuration is absent.
provider=configuration();refresh_provider()
out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
credential=json.loads((settings.PRIVATE_ROOT/'acceptance-administrator.json').read_text())
refs=json.loads((settings.PRIVATE_ROOT/'browser-manifest.json').read_text())
project=Project.objects.get(pk=credential['project_id']);http=HTTP()
http.post('/administrator/login/',{'login':credential['username'],'password':credential['password']})
for attempt in range(3):
 code=format_hotp_value(hotp_value(credential['totp_secret'],int(time.time())//30))
 try:url,_=http.post('/administrator/2fa/authenticate/',{'code':code})
 except urllib.error.HTTPError as error:
  if error.code!=400:raise
  url='not-authenticated';error.close()
 if urllib.parse.urlsplit(url).path=='/app/':break
 assert attempt<2,'MFA login unavailable';time.sleep(30-time.time()%30+.1)
http.post('/app/projects/'+str(project.pk)+'/ai/settings/',{'enabled':'on','daily_budget_microusd':'200000'})
patch=ROOT/'docs/jury/source-fix.patch';patch_hash=hashlib.sha256(patch.read_bytes()).hexdigest()
source=SourceSubmission.objects.filter(project=project,original_sha256=patch_hash,erased_at=None).first()
if not source:
 from django.core.files.uploadedfile import SimpleUploadedFile
 source=source_upload(project.created_by,project,SimpleUploadedFile('source-fix.patch',patch.read_bytes()),'Published MIT correction for actual provider qualification')
replayed=Run.objects.get(pk=refs['replay'])
tasks=[('explain',refs['broken'],None,None),('source-review',refs['broken'],source,None),
       ('suggest-correction',refs['broken'],source,None),('before-after',refs['replay'],None,str(replayed.original_id))]
observed=[]
for position,(task,identifier,selected_source,compared) in enumerate(tasks):
 if position==3:time.sleep(60) # Respect actor limit, without retrying a provider call.
 refresh_provider()
 run=Run.objects.get(pk=identifier);summary_before=hashlib.sha256(canonical(run.summary)).hexdigest()
 evidence_before=list(Artifact.objects.filter(run=run).order_by('relative_path').values('relative_path','sha256'))
 path='/app/runs/'+identifier+'/ai/'
 data={'task':task,'case':'timeout','source':str(selected_source.pk) if selected_source else '',
       'compared':compared or '','key':secrets.token_urlsafe(24)}
 _,body=http.post(path,data);parsed=Inputs();parsed.feed(body)
 assert parsed.data.get('confirmation'),'No provider request without a signed exact evidence preview'
 data.update(consent='on',confirmation=parsed.data['confirmation'])
 url,_=http.post(path,data,parsed.data['csrfmiddlewaretoken']);analysis_id=urllib.parse.urlsplit(url).path.strip('/').split('/')[-1]
 original,_=http.post(path,data,parsed.data['csrfmiddlewaretoken']);assert original==url,'Duplicate consent must not create another call'
 with (out/(task+'-worker.txt')).open('wb') as stream:
  result=subprocess.run([sys.executable,str(ROOT/'web/ops/staging.py'),'manage.py','dispatch_ai','--once'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=40)
 assert result.returncode==0
 analysis=AIAnalysis.objects.get(pk=analysis_id);run.refresh_from_db()
 assert hashlib.sha256(canonical(run.summary)).hexdigest()==summary_before
 assert evidence_before==list(Artifact.objects.filter(run=run).order_by('relative_path').values('relative_path','sha256'))
 record={'task':task,'analysis_id':str(analysis.pk),'run_id':str(run.pk),'native_run_id':run.native_run_id,'state':analysis.state,'error':analysis.error_code,
   'requested_model':analysis.requested_model,'returned_model':analysis.resolved_model,'provider_response_id':analysis.provider_response_id,
   'input_sha256':analysis.input_sha256,'usage':analysis.usage,'reserved_microusd':analysis.reserved_microusd,'accounted_microusd':analysis.accounted_microusd,
   'usage_established':analysis.usage_established,'native_summary_unchanged':True,'evidence_hashes_unchanged':True,
   'result_sha256':hashlib.sha256(canonical(analysis.result)).hexdigest(),'citations':[ref for finding in analysis.result.get('findings',[]) for ref in finding['evidence_refs']]}
 observed.append(record)
 (out/'qualification.json').write_text(json.dumps({'passed':all(item['state']=='completed' for item in observed),'provider':provider.name,
   'scope':'Actual dedicated provider over real HTTP consent/DB/private child; existing genuine QNX evidence. No new QNX execution.',
   'mock_answers':False,'source_sha256':patch_hash,'analyses':observed},indent=2)+'\n')
 assert analysis.state=='completed','Provider qualification did not complete; preserve reservation/evidence and inspect the safe error code'
 print('Verified real provider task:',task,'; native verdict/evidence unchanged.',flush=True)
