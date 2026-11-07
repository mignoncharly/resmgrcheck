"""Explicit consent and read-only engineering interpretation; no provider calls in HTTP."""
from datetime import timedelta
import hashlib,secrets
from django import forms
from django.core import signing
from django.http import Http404,HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_GET,require_POST
from django.db import transaction
from resmgrcheck.contracts import canonical
from .models import Project,AIAnalysis,SourceSubmission,Run,AIProviderState,AIUsage
from .security import secure_account,project_access,audit,consume_rate
from .execution_views import authorized_run
from .ai_evidence import evidence_pack,source_upload,validate_answer
from .storage import verify_inventory,detail_cases
from .ai_jobs import enqueue_analysis,public_provider
from .ai_provider import reservation
from .engine import PolicyError

class AISettingsForm(forms.Form):
    enabled=forms.BooleanField(required=False,label='Enable optional evidence egress for this project')
    daily_budget_microusd=forms.IntegerField(min_value=0,max_value=1000000,label='Daily project ceiling (millionths of USD)',help_text='0 disables requests. 1000000 = USD1. Reservations count before calls; uncertain calls retain the full reservation. Provider project spend limits should also be configured.')

class AnalysisForm(forms.Form):
    task=forms.ChoiceField(choices=[('explain','Explain the established failure'),('source-review','Review uploaded source against evidence'),('suggest-correction','Suggest an untested source correction'),('before-after','Interpret canonical before/after comparison')])
    case=forms.ChoiceField()
    source=forms.ModelChoiceField(queryset=SourceSubmission.objects.none(),required=False,label='Optional reviewed source excerpt')
    compared=forms.ModelChoiceField(queryset=Run.objects.none(),required=False,label='Optional earlier run to compare')
    key=forms.CharField(widget=forms.HiddenInput,min_length=16,max_length=64)
    confirmation=forms.CharField(widget=forms.HiddenInput,required=False)
    consent=forms.BooleanField(required=False,label='I authorize sending the exact redacted preview to the named provider, understand its data policy/cost ceiling, and have permission to share any included source with project members and that provider.')
    def __init__(self,*args,run,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['case'].choices=[(row['case_id'],row['case_id']) for row in run.summary.get('cases',[])]
        self.fields['source'].queryset=SourceSubmission.objects.filter(project=run.project,erased_at=None,expires_at__gt=timezone.now())
        eligible=Run.objects.filter(project=run.project,state='completed',purged_at=None).exclude(pk=run.pk).exclude(operation='inventory')
        self.fields['compared'].queryset=Run.objects.filter(pk__in=eligible.values('pk')[:100])

class SourceForm(forms.Form):
    label=forms.CharField(max_length=80,label='Source excerpt label')
    file=forms.FileField(label='Original source excerpt (UTF-8, at most12KiB/240 lines)')
    rights=forms.BooleanField(label='I own or am authorized to use this excerpt, and it contains no licensed SDK/runtime code or protected configuration. Only the redacted copy will be retained, visible to authorized project members.')

@secure_account(recent=900)
@require_http_methods(['GET','POST'])
def settings_page(request,project_id):
    project,role=project_access(request.user,project_id,'admin')
    form=AISettingsForm(request.POST or None,initial={'enabled':project.ai_enabled,'daily_budget_microusd':project.ai_daily_budget_microusd})
    if request.method=='POST' and form.is_valid():
        Project.objects.filter(pk=project.pk).update(ai_enabled=form.cleaned_data['enabled'],ai_daily_budget_microusd=form.cleaned_data['daily_budget_microusd'])
        audit(request.user,'ai.project_policy_changed',project.organization,project.pk,enabled=form.cleaned_data['enabled'],daily_budget_microusd=form.cleaned_data['daily_budget_microusd'])
        return redirect('ai_settings',project_id=project.pk)
    state=AIProviderState.objects.filter(name='default').first()
    return render(request,'control/ai_settings.html',{'project':project,'form':form,'provider_state':state,
       'usage':AIUsage.objects.filter(scope='project:'+str(project.pk),day=timezone.now().date()).first()},status=400 if form.errors else 200)

@secure_account(strong=True,recent=900)
@require_http_methods(['GET','POST'])
def request_analysis(request,run_id):
    run,role=authorized_run(request,run_id,'developer')
    form=AnalysisForm(request.POST or None,run=run,initial={'key':secrets.token_urlsafe(24)})
    preview=None;provider=None;estimate=None;notice=None
    try:provider=public_provider()
    except PolicyError as error:notice=str(error)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data
        try:
            payload,citations=evidence_pack(request.user,run,data['case'],data['task'],data['source'],data['compared'])
            digest=hashlib.sha256(canonical({'payload':payload,'citations':citations,'provider':provider.public() if provider else None})).hexdigest()
            binding={'actor':str(request.user.pk),'run':str(run.pk),'digest':digest,'key':data['key']}
            if data['confirmation']:
                if not data['consent']:raise PolicyError('ai_explicit_consent_required')
                if signing.loads(data['confirmation'],salt='ai-consent',max_age=300)!=binding:raise signing.BadSignature
                duplicate=AIAnalysis.objects.filter(actor=request.user,run=run,idempotency_key=data['key']).exists()
                if not duplicate and not consume_rate('ai-request',str(request.user.pk),3,60):raise PolicyError('ai_request_rate_limited')
                analysis,_=enqueue_analysis(request,run,data['task'],payload,citations,data['key'],data['source'],data['compared'])
                return redirect('ai_detail',analysis_id=analysis.pk)
            preview=payload
            if provider:estimate=reservation(payload,provider)[0]
            form.data=form.data.copy();form.data['confirmation']=signing.dumps(binding,salt='ai-consent') if provider else ''
        except signing.BadSignature:form.add_error(None,'Consent preview expired or inputs/provider changed. Review a fresh exact preview.')
        except (PolicyError,ValueError,OSError):form.add_error(None,'Analysis unavailable: evidence, source, provider, consent, cost ceiling or capability did not verify. The deterministic report remains available.')
        if form.errors:
            form.data=form.data.copy();form.data['confirmation']='';form.data['consent']=''
    return render(request,'control/ai_request.html',{'run':run,'form':form,'preview':preview,'provider':provider.public() if provider else None,'estimate':estimate,'notice':notice},status=400 if form.errors else 200)

@secure_account
@require_GET
def detail(request,analysis_id):
    analysis=get_object_or_404(AIAnalysis.objects.select_related('run__project__organization','actor','source','compared_run'),pk=analysis_id)
    project,role=project_access(request.user,analysis.run.project_id)
    findings=[]
    if analysis.state=='completed' and not analysis.erased_at:
        try:
            if hashlib.sha256(canonical(analysis.result)).hexdigest()!=analysis.output_sha256:raise PolicyError('ai_output_identity_changed')
            verify_inventory(analysis.run);detail_cases(analysis.run)
            if analysis.compared_run:verify_inventory(analysis.compared_run);detail_cases(analysis.compared_run)
            validate_answer(analysis.result,analysis.citations,bool(analysis.source_id),analysis.task)
        except (ValueError,OSError,PolicyError):return render(request,'control/message.html',{'title':'AI interpretation withheld','message':'The original evidence or saved interpretation no longer verifies. Preserve its identity and contact the operator; no conclusion is substituted.'},status=409)
        for finding in analysis.result.get('findings',[]):
            findings.append({'statement':finding['statement'],'references':[{'id':key,**analysis.citations[key]} for key in finding['evidence_refs']]})
    return render(request,'control/ai_detail.html',{'analysis':analysis,'findings':findings,'role':role})

@secure_account(strong=True,recent=900)
@require_http_methods(['GET','POST'])
def upload_source(request,project_id):
    project,role=project_access(request.user,project_id,'developer');form=SourceForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        if not consume_rate('source-upload',str(request.user.pk),10,3600):return HttpResponse('Source upload rate limit.',status=429)
        if SourceSubmission.objects.filter(project=project,erased_at=None).count()>=20:form.add_error(None,'Project source excerpt limit reached; wait for retention or ask an administrator to erase an unused excerpt.')
        else:
            try:
                source=source_upload(request.user,project,form.cleaned_data['file'],form.cleaned_data['label'])
                audit(request.user,'ai.source_redacted_uploaded',project.organization,source.pk,original_sha256=source.original_sha256,redacted_sha256=source.redacted_sha256,redactions=source.redactions)
                return redirect('source_detail',source_id=source.pk)
            except PolicyError as error:form.add_error('file',str(error))
    return render(request,'control/upload.html',{'project':project,'form':form,'title':'Review an original source excerpt for optional AI','button_label':'Retain redacted source for review','source_upload':True},status=400 if form.errors else 200)

@secure_account
@require_http_methods(['GET','POST'])
def source_detail(request,source_id):
    source=get_object_or_404(SourceSubmission.objects.select_related('project__organization'),pk=source_id)
    project,role=project_access(request.user,source.project_id)
    if request.method=='POST':
        project_access(request.user,source.project_id,'admin')
        with transaction.atomic():
            source=SourceSubmission.objects.select_for_update().get(pk=source.pk)
            if AIAnalysis.objects.filter(source=source,state__in=['queued','running']).exists():return render(request,'control/message.html',{'title':'Source is in an active analysis','message':'Cancel queued analysis or wait for the bounded provider call before erasing this copy. No process termination or remote data deletion is claimed.'},status=409)
            # Erase derivative source-bearing analysis too. Native artifacts stay intact.
            now=timezone.now()
            SourceSubmission.objects.filter(pk=source.pk,erased_at=None).update(redacted_text='',erased_at=now)
            AIAnalysis.objects.filter(source=source,erased_at=None).update(payload={},citations={},result={},erased_at=now)
            audit(request.user,'ai.source_erased',project.organization,source.pk,derivative_analysis_erased=True,provider_retention_not_changed=True)
        return redirect('source_detail',source_id=source.pk)
    return render(request,'control/source.html',{'source':source,'role':role,'lines':list(enumerate(source.redacted_text.splitlines(),1)) if not source.erased_at else []})

@secure_account(strong=True,recent=900)
@require_POST
def cancel_analysis(request,analysis_id):
    with transaction.atomic():
        analysis=get_object_or_404(AIAnalysis.objects.select_for_update(of=('self',)).select_related('run__project__organization'),pk=analysis_id)
        project,role=project_access(request.user,analysis.run.project_id,'developer')
        if analysis.actor_id!=request.user.pk and role not in {'owner','admin'}:raise Http404
        if analysis.state!='queued':return render(request,'control/message.html',{'title':'Analysis already dispatched or finalized','message':'This action cannot prove an in-flight provider request stopped. Its existing bound and recorded outcome remain authoritative.'},status=409)
        analysis.state='error';analysis.error_code='ai_cancelled_before_provider';analysis.finished_at=timezone.now();analysis.save(update_fields=['state','error_code','finished_at'])
        audit(request.user,'ai.cancelled_before_provider',project.organization,analysis.pk,reservation_retained=True)
    return redirect('ai_detail',analysis_id=analysis.pk)
