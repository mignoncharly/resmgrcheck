from django import forms
from django.http import Http404
from django.shortcuts import render,redirect
from django.views.decorators.http import require_http_methods,require_POST
from .models import Organization,Run
from .security import secure_account,organization_member,audit
from .execution_views import authorized_run

class RetentionForm(forms.Form):
    retention_days=forms.IntegerField(min_value=7,max_value=3650,label='Evidence retention (days)',help_text='Completed local evidence becomes eligible after this period. Holds, unresolved cleanup and active replay dependencies prevent removal. Metadata/hashes/audit remain; QNX histories are not removed by this policy.')

@secure_account(recent=900)
@require_http_methods(['GET','POST'])
def settings_page(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    form=RetentionForm(request.POST or None,initial={'retention_days':member.organization.retention_days})
    if request.method=='POST' and form.is_valid():
        Organization.objects.filter(pk=member.organization_id).update(retention_days=form.cleaned_data['retention_days'])
        audit(request.user,'retention.policy_changed',member.organization,member.organization_id,retention_days=form.cleaned_data['retention_days'])
        return redirect('retention',organization_id=organization_id)
    return render(request,'control/retention.html',{'organization':member.organization,'form':form},status=400 if form.errors else 200)

@secure_account(recent=900)
@require_POST
def hold(request,run_id):
    run,role=authorized_run(request,run_id,'admin')
    if request.POST.get('hold') not in {'0','1'}:raise Http404
    if run.purged_at:return render(request,'control/message.html',{'title':'Evidence already expired','message':'A hold cannot restore expired evidence.'},status=409)
    enabled=request.POST['hold']=='1'
    if Run.objects.filter(pk=run.pk,purged_at=None).update(retention_hold=enabled)!=1:return render(request,'control/message.html',{'title':'Evidence already expired','message':'A hold cannot restore expired evidence.'},status=409)
    audit(request.user,'retention.hold_changed',run.project.organization,run.pk,enabled=enabled)
    return redirect('run_detail',run_id=run.pk)
