"""HTTP control plane: validates/enqueues only. Never executes a QNX operation."""
import secrets
from django.core import signing
from django.http import Http404,HttpResponse,JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST,require_http_methods
from .models import Target,BuildRelease,Run
from .forms import TargetRequestForm,RunForm,BuildImportForm
from .security import secure_account,project_access,audit
from .jobs import enqueue,QueueError


def intent(data,request,project):
    return {'actor':str(request.user.pk),'project':str(project.pk),**{key:str(data[key].pk) if key in {'target','build'} else data[key] for key in ['target','build','profile','suite','fixture_mode','idempotency_key']}}

@secure_account
@require_GET
def targets(request,project_id):
    project,role=project_access(request.user,project_id)
    return render(request,'control/targets.html',{'project':project,'targets':Target.objects.filter(project=project),'role':role,'form':TargetRequestForm()})

@secure_account(strong=True,recent=900)
@require_POST
def target_request(request,project_id):
    project,role=project_access(request.user,project_id,'admin');form=TargetRequestForm(request.POST)
    if form.is_valid():
        target=form.save(commit=False);target.project=project;target.kind='customer-request';target.state='unsupported';target.save()
        audit(request.user,'target.onboarding_requested',project.organization,target.pk)
        return redirect('targets',project_id=project_id)
    return render(request,'control/form.html',{'title':'Request dedicated target onboarding','form':form},status=400)

@secure_account(strong=True,recent=900)
@require_POST
def inventory(request,project_id,target_id):
    project,role=project_access(request.user,project_id,'developer')
    target=get_object_or_404(Target,pk=target_id,project=project)
    try:run,_=enqueue(request,project,target,None,profile='sensor',suite='profile',mode='fixed',key=secrets.token_urlsafe(24),operation='inventory')
    except QueueError as error:return render(request,'control/message.html',{'title':'Inventory not queued','message':str(error)},status=409)
    return redirect('run_detail',run_id=run.pk)

@secure_account(strong=True,recent=900)
@require_http_methods(['GET','POST'])
def new_run(request,project_id):
    project,role=project_access(request.user,project_id,'developer')
    form=RunForm(request.POST or None,project=project,initial={'idempotency_key':secrets.token_urlsafe(24),'profile':'sensor','suite':'profile','fixture_mode':'fixed'})
    preview=None
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data;payload=intent(data,request,project)
        if data['confirmed']:
            try:
                saved=signing.loads(data['confirmation'],salt='run-confirmation',max_age=300)
                if saved!=payload:raise signing.BadSignature
                run,_=enqueue(request,project,data['target'],data['build'],profile=data['profile'],suite=data['suite'],mode=data['fixture_mode'],key=data['idempotency_key'])
                return redirect('run_detail',run_id=run.pk)
            except signing.BadSignature:form.add_error(None,'Confirmation expired or changed. Preview the exact request again.')
            except QueueError as error:form.add_error(None,str(error))
        else:
            preview=payload;form.fields['confirmation'].initial=signing.dumps(payload,salt='run-confirmation');form.data=form.data.copy();form.data['confirmation']=form.fields['confirmation'].initial;form.data['confirmed']='on'
    return render(request,'control/new_run.html',{'project':project,'form':form,'preview':preview},status=400 if form.errors else 200)


def authorized_run(request,identifier,minimum='viewer'):
    run=get_object_or_404(Run.objects.select_related('project__organization','target','build','actor','original'),pk=identifier)
    project,role=project_access(request.user,run.project_id,minimum)
    return run,role

@secure_account
@require_GET
def run_detail(request,run_id):
    run,role=authorized_run(request,run_id)
    return render(request,'control/run.html',{'run':run,'role':role})

@secure_account
@require_GET
def run_status(request,run_id):
    run,role=authorized_run(request,run_id)
    return JsonResponse({'id':str(run.pk),'native_run_id':run.native_run_id,'state':run.state,'progress':run.progress,'error_code':run.error_code,
        'cancel_requested':run.cancel_requested,'summary':run.summary,'incidents':run.incidents,'cleanup_verified':run.target_cleanup_verified})

@secure_account(strong=True,recent=900)
@require_POST
def cancel(request,run_id):
    run,role=authorized_run(request,run_id,'developer')
    if run.actor_id!=request.user.pk and role not in {'owner','admin'}:raise Http404
    Run.objects.filter(pk=run.pk).update(cancel_requested=True)
    audit(request.user,'run.cancel_requested',run.project.organization,run.pk,previous_state=run.state)
    return redirect('run_detail',run_id=run_id)

@secure_account(strong=True,recent=900)
@require_http_methods(['GET','POST'])
def replay_run(request,run_id):
    original,role=authorized_run(request,run_id,'developer')
    candidates=BuildRelease.objects.filter(target=original.target,approved=True)
    if request.method=='POST':
        build=get_object_or_404(candidates,pk=request.POST.get('build'))
        key=request.POST.get('idempotency_key','')
        try:
            run,_=enqueue(request,original.project,original.target,build,profile=original.profile,suite=original.suite,mode=original.fixture_mode,key=key,original=original,operation='replay')
            return redirect('run_detail',run_id=run.pk)
        except QueueError as error:return render(request,'control/message.html',{'title':'Replay not queued','message':str(error)},status=409)
    return render(request,'control/replay.html',{'original':original,'builds':candidates,'idempotency_key':secrets.token_urlsafe(24)})

@secure_account(strong=True,recent=900)
@require_http_methods(['GET','POST'])
def import_build(request,project_id,target_id):
    project,role=project_access(request.user,project_id,'developer');target=get_object_or_404(Target,pk=target_id,project=project)
    form=BuildImportForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        build=BuildRelease.objects.create(target=target,label=form.cleaned_data['label'],manifest=form.cleaned_data['manifest'])
        audit(request.user,'build.approval_requested',project.organization,build.pk)
        return redirect('targets',project_id=project_id)
    return render(request,'control/upload.html',{'title':'Import candidate manifest for operator approval','form':form},status=400 if form.errors else 200)
