from django import forms
from django.contrib.auth import logout
from django.http import Http404
from django.middleware.csrf import rotate_token
from django.shortcuts import render,redirect,get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods,require_POST
from .models import AccessCode,AccessGrant,AccessSession,Project,Target,Run,AuditEvent
from .security import administrator,organization_member,is_code,audit,visible_projects,visible_targets,visible_runs,secure_account
from .access import create_code,redeem,revoke_code,RedemptionDenied

class RedemptionForm(forms.Form):
    code=forms.CharField(max_length=90,widget=forms.PasswordInput(attrs={'autocomplete':'off'}),label='Administrator-issued access code')

@sensitive_post_parameters('code')
@require_http_methods(['GET','POST'])
def developer_access(request):
    form=RedemptionForm(request.POST or None)
    if request.method=='POST' and request.user.is_authenticated:return render(request,'control/message.html',{'title':'Session already active','message':'Use your existing session or sign out before redeeming another code.'},status=409)
    if request.method=='POST' and form.is_valid():
        try:
            redeem(request,form.cleaned_data['code']);rotate_token(request)
            return redirect('overview')
        except RedemptionDenied:
            audit(None,'access_code.redemption_denied');form.add_error('code','Access denied. Check the code, its validity and available session/redemption capacity with your administrator.')
    return render(request,'control/access.html',{'form':form,'is_account_page':True},status=400 if form.errors else 200)

@require_POST
def sign_out(request):
    if is_code(request.user):
        with transaction.atomic():
            AccessCode.objects.select_for_update().get(pk=request.user.access_session.code_id)
            AccessSession.objects.filter(pk=request.user.pk,revoked_at=None).update(revoked_at=timezone.now())
            audit(request.user,'access_session.signed_out',request.user.access_session.code.organization,request.user.pk)
        request.session.flush()
    else:logout(request)
    return redirect('developer_access')

class CodeForm(forms.Form):
    description=forms.CharField(max_length=160)
    projects=forms.ModelMultipleChoiceField(queryset=Project.objects.none())
    targets=forms.ModelMultipleChoiceField(queryset=Target.objects.none(),required=False)
    evidence=forms.ModelMultipleChoiceField(queryset=Run.objects.none(),required=False,label='Selected existing evidence')
    all_evidence=forms.BooleanField(required=False,label='Allow all evidence in selected projects and targets, including future runs')
    can_download=forms.BooleanField(required=False,label='Allow evidence/report downloads')
    allow_live=forms.BooleanField(required=False,label='Allow live QNX execution on the selected approved targets')
    allow_ai=forms.BooleanField(required=False,label='Allow optional AI, subject to project opt-in, consent and budgets')
    expires_at=forms.DateTimeField(required=False,help_text='Optional UTC expiration, YYYY-MM-DD HH:MM. Empty means until revocation; browser sessions still expire.')
    max_redemptions=forms.IntegerField(required=False,min_value=1,max_value=1000)
    max_sessions=forms.IntegerField(min_value=1,max_value=20,initial=1)
    def clean_description(self):
        import re
        value=self.cleaned_data['description']
        if re.search(r'rmc_[0-9a-f]{32}_[A-Za-z0-9_-]{43}',value):raise forms.ValidationError('Do not place access secrets in descriptions.')
        return value
    def __init__(self,*args,actor,organization,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['projects'].queryset=visible_projects(actor).filter(organization=organization)
        self.fields['targets'].queryset=visible_targets(actor).filter(project__organization=organization)
        self.fields['evidence'].queryset=visible_runs(actor).filter(project__organization=organization)
    def clean(self):
        data=super().clean();projects={p.pk for p in data.get('projects',[])};targets=list(data.get('targets',[]));target_ids={t.pk for t in targets}
        if any(t.project_id not in projects for t in targets):self.add_error('targets','Choose targets within the selected projects.')
        if any(r.project_id not in projects or r.target_id not in target_ids for r in data.get('evidence',[])):self.add_error('evidence','Choose evidence within the selected projects and targets.')
        def approved_execution_target(target):
            if not target.approved:return False
            if target.kind=='managed-lab':return True
            if target.kind=='customer-runner':
                from django.conf import settings
                from .runners import status
                from .models import CustomerRunner
                runner=CustomerRunner.objects.select_related('target').filter(pk=target.pk).first()
                return settings.RUNNER_ENABLED and runner is not None and status(runner) in {'connected','disconnected'}
            return False
        if data.get('allow_live') and (not targets or not all(approved_execution_target(t) for t in targets)):self.add_error('targets','Live codes require explicitly approved managed or enrolled customer targets. Customer requests do not authorize execution.')
        if data.get('expires_at') and data['expires_at']<=timezone.now():self.add_error('expires_at','Choose a future UTC expiration.')
        return data
    def grants(self):
        d=self.cleaned_data
        return [{'project':p,'targets':[t for t in d['targets'] if t.project_id==p.pk],
            'evidence':[r for r in d['evidence'] if r.project_id==p.pk],'all_evidence':d['all_evidence'],
            'can_run':d['allow_live'],'can_ai':d['allow_ai'],'can_download':d['can_download']} for p in d['projects']]

@administrator
@require_http_methods(['GET','POST'])
def codes(request,organization_id):
    member=organization_member(request.user,organization_id,'admin');form=CodeForm(request.POST or None,actor=request.user,organization=member.organization)
    shown=None;created=None
    if request.method=='POST' and form.is_valid():
        d=form.cleaned_data;created,shown=create_code(request.user,member.organization,d['description'],form.grants(),
            expires_at=d['expires_at'],max_redemptions=d['max_redemptions'],max_sessions=d['max_sessions'],allow_live=d['allow_live'],allow_ai=d['allow_ai'])
        form=CodeForm(actor=request.user,organization=member.organization)
    response=render(request,'control/codes.html',{'organization':member.organization,'form':form,'created_code':shown,'created':created,'codes':AccessCode.objects.filter(organization=member.organization).order_by('-created_at')[:100]},status=400 if form.errors else 200)
    response['Cache-Control']='no-store';return response

@administrator
@require_http_methods(['GET','POST'])
def code_detail(request,code_id):
    code=get_object_or_404(AccessCode.objects.select_related('organization'),pk=code_id);organization_member(request.user,code.organization_id,'admin')
    grants=list(code.grants.prefetch_related('targets','evidence'))
    initial={'description':code.description,'projects':[g.project_id for g in grants],
        'targets':[t.pk for g in grants for t in g.targets.all()],'evidence':[r.pk for g in grants for r in g.evidence.all()],
        'all_evidence':any(g.all_evidence for g in grants),'can_download':any(g.can_download for g in grants),
        'allow_live':code.allow_live,'allow_ai':code.allow_ai,'max_sessions':code.max_sessions,'max_redemptions':code.max_redemptions,'expires_at':code.expires_at}
    form=CodeForm(request.POST or None,actor=request.user,organization=code.organization,initial=initial)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            locked=AccessCode.objects.select_for_update().get(pk=code.pk)
            if locked.revoked_at:return render(request,'control/message.html',{'title':'Code revoked','message':'Issue a new code; revocation cannot be undone.'},status=409)
            d=form.cleaned_data
            for key in ['description','expires_at','max_redemptions','max_sessions','allow_live','allow_ai']:setattr(locked,key,d[key])
            locked.policy_version+=1;locked.save()
            code.grants.all().delete()
            for values in form.grants():
                targets=values.pop('targets');evidence=values.pop('evidence');grant=AccessGrant.objects.create(code=locked,**values);grant.targets.set(targets);grant.evidence.set(evidence)
            count=locked.sessions.filter(revoked_at=None).update(revoked_at=timezone.now())
            audit(request.user,'access_code.policy_changed',locked.organization,locked.pk,sessions_revoked=count)
        return redirect('code_detail',code_id=code.pk)
    events=AuditEvent.objects.filter(organization=code.organization).filter(Q(access_code=code)|Q(object_id=str(code.pk)))[:100]
    return render(request,'control/code_detail.html',{'code':code,'form':form,'sessions':code.sessions.order_by('-created_at')[:100],'events':events},status=400 if form.errors else 200)

@administrator
@require_POST
def revoke(request,code_id):
    revoke_code(request.user,code_id);return redirect('code_detail',code_id=code_id)

@administrator
@require_POST
def revoke_session(request,session_id):
    with transaction.atomic():
        identifier=get_object_or_404(AccessSession,pk=session_id).code_id
        AccessCode.objects.select_for_update().get(pk=identifier)
        session=get_object_or_404(AccessSession.objects.select_for_update(of=('self',)).select_related('code__organization'),pk=session_id)
        organization_member(request.user,session.code.organization_id,'admin')
        session.revoked_at=timezone.now();session.save(update_fields=['revoked_at'])
        audit(request.user,'access_session.revoked',session.code.organization,session.pk,code_id=str(session.code_id))
    return redirect('code_detail',code_id=session.code_id)

@secure_account
def session_settings(request):
    return render(request,'control/access_session.html',{'session':request.user.access_session}) if is_code(request.user) else redirect('administrator_settings')
