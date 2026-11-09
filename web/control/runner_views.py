"""Machine-only signed endpoint; administrator browser mutations remain CSRF protected."""
from django.conf import settings
from django.http import Http404,JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
from customer_runner import protocol as wire
from . import runners
from .forms import TargetRequestForm
from .models import CustomerRunner
from .security import administrator,project_access,consume_rate

@csrf_exempt
@require_POST
def machine(request,operation):
    if not settings.RUNNER_ENABLED:raise Http404
    try:
        wire.require(not request.COOKIES and not request.META.get('HTTP_AUTHORIZATION'),'runner_machine_only')
        wire.require(request.content_type=='application/json' and not request.META.get('HTTP_CONTENT_ENCODING'),'runner_content_type_invalid')
        wire.require(consume_rate('runner-ip',request.META.get('REMOTE_ADDR',''),600,60),'runner_rate_limited')
        value=wire.parse(request.body)
        if operation=='enroll':result=runners.enroll(value)
        elif operation=='exchange':
            runner,payload=runners.authenticate(value);body=payload['body']
            wire.require(type(body) is dict,'runner_operation_invalid')
            if body.get('operation')=='heartbeat':answer=runners.heartbeat(runner,body)
            else:
                from .runner_jobs import exchange
                answer=exchange(runner,body)
            result=runners.response(payload,answer)
        else:raise wire.ProtocolError('runner_operation_invalid')
        reply=JsonResponse(result);reply['Cache-Control']='no-store';return reply
    except (wire.ProtocolError,ValueError,TypeError,KeyError,AttributeError):
        return JsonResponse({'error':'runner_request_rejected'},status=400)

@administrator
@require_POST
def issue(request,project_id):
    project,_=project_access(request.user,project_id,'admin');form=TargetRequestForm(request.POST)
    if not settings.RUNNER_ENABLED:return render(request,'control/message.html',{'title':'Runner enrollment unavailable','message':'Customer-runner activation awaits its reviewed deployment gate.'},status=409)
    if not form.is_valid():return render(request,'control/form.html',{'title':'Enroll customer runner','form':form},status=400)
    try:target,token=runners.issue(request.user,project,form.cleaned_data['name'])
    except wire.ProtocolError:return render(request,'control/message.html',{'title':'Enrollment unavailable','message':'Runner enrollment limit or configuration prevents issuance.'},status=409)
    reply=render(request,'control/runner_enrollment.html',{'project':project,'target':target,'token':token,'server_key':wire.public(settings.RUNNER_SIGNING_KEY)})
    reply['Cache-Control']='no-store';return reply

@administrator
@require_GET
def detail(request,project_id,target_id):
    project,_=project_access(request.user,project_id,'admin')
    runner=get_object_or_404(CustomerRunner.objects.select_related('target'),target_id=target_id,target__project=project)
    return render(request,'control/runner.html',{'project':project,'runner':runner,'runner_state':runners.status(runner)})

@administrator
@require_POST
def approval(request,project_id,target_id):
    project,_=project_access(request.user,project_id,'admin')
    runner=get_object_or_404(CustomerRunner.objects.select_related('target'),target_id=target_id,target__project=project)
    try:runners.approve(request.user,runner.target,request.POST.get('inventory_sha256',''))
    except wire.ProtocolError:return render(request,'control/message.html',{'title':'Approval withheld','message':'Runner identity or capability inventory changed or is incompatible.'},status=409)
    return redirect('runner_detail',project_id=project.pk,target_id=target_id)

@administrator
@require_POST
def revocation(request,project_id,target_id):
    project,_=project_access(request.user,project_id,'admin')
    runner=get_object_or_404(CustomerRunner.objects.select_related('target'),target_id=target_id,target__project=project)
    runners.revoke(request.user,runner.target)
    return redirect('runner_detail',project_id=project.pk,target_id=target_id)

@administrator
@require_POST
def approve_build(request,project_id,target_id,build_id):
    from .models import BuildRelease
    from resmgrcheck.deployment import Deployment
    from django.db import transaction
    from .security import audit
    project,_=project_access(request.user,project_id,'admin')
    with transaction.atomic():
        runner=get_object_or_404(CustomerRunner.objects.select_for_update().select_related('target'),target_id=target_id,target__project=project)
        build=get_object_or_404(BuildRelease.objects.select_for_update(),pk=build_id,target_id=target_id)
        if runners.status(runner)!='connected':return JsonResponse({'error':'runner_not_approved_or_connected'},status=409)
        try:
            selected=Deployment.parse(build.manifest)
            wire.require(request.POST.get('deployment_id')==selected.data['deployment_id'],'runner_build_changed')
            for a,b in [('uid','uid'),('processor','architecture'),('machine','machine'),('release','release'),('recipe_id','recipe_id')]:
                wire.require(runner.inventory['target_identity'][a]==selected.data[b],'runner_build_incompatible')
        except (ValueError,KeyError):return JsonResponse({'error':'runner_build_incompatible'},status=409)
        build.approved=True;build.binding=str(build.pk);build.save(update_fields=['approved','binding'])
        audit(request.user,'runner.build_approved',project.organization,target_id,build_id=str(build.pk),deployment_id=selected.data['deployment_id'])
    return redirect('targets',project_id=project.pk)
