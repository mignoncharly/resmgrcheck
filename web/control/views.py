from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

@require_GET
def health(request):return JsonResponse({'status':'alive'})

@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:cursor.execute('SELECT 1');cursor.fetchone()
    except Exception:return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ready'})

@require_GET
def home(request):return render(request,'control/home.html')

from datetime import timedelta
import hashlib,secrets
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.http import Http404,HttpResponse
from django.shortcuts import redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from allauth.account.models import EmailAddress
from allauth.usersessions.models import UserSession
from .forms import OrganizationForm,ProjectForm,InvitationForm,MemberForm,ProjectMemberForm,PasswordConfirmation
from .models import User,Organization,Membership,Project,ProjectMembership,Invitation,AccountDeletion,AuditEvent
from .security import secure_account,organization_member,project_access,visible_projects,audit,RANK,verified,require_mfa

@secure_account
@require_GET
def overview(request):
    organizations=Membership.objects.filter(user=request.user,active=True,organization__active=True).select_related('organization')
    return render(request,'control/overview.html',{'memberships':organizations,'projects':visible_projects(request.user)})

@secure_account(strong=True)
def organization_create(request):
    form=OrganizationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            organization=form.save();Membership.objects.create(organization=organization,user=request.user,role='owner')
            audit(request.user,'organization.created',organization,organization.pk)
        return redirect('team',organization_id=organization.pk)
    return render(request,'control/form.html',{'title':'Create organization','form':form})

@secure_account
def project_create(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    form=ProjectForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if Project.objects.filter(organization=member.organization,name=form.cleaned_data['name']).exists():form.add_error('name','A project with this name already exists.')
        else:
            with transaction.atomic():
                project=form.save(commit=False);project.organization=member.organization;project.created_by=request.user;project.save()
                audit(request.user,'project.created',project.organization,project.pk)
            return redirect('project',project_id=project.pk)
    return render(request,'control/form.html',{'title':'Create project','form':form})

@secure_account
@require_GET
def project_detail(request,project_id):
    project,role=project_access(request.user,project_id)
    return render(request,'control/project.html',{'project':project,'role':role})

@secure_account
@require_GET
def project_api(request,project_id):
    project,role=project_access(request.user,project_id)
    return JsonResponse({'id':str(project.pk),'organization_id':str(project.organization_id),'name':project.name,'role':role})

@secure_account
def team(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    return render(request,'control/team.html',{'organization':member.organization,'memberships':Membership.objects.filter(organization=member.organization).select_related('user'),'invitation_form':InvitationForm(),'actor_role':member.role})

@secure_account(recent=900)
@require_POST
def invite(request,organization_id):
    member=organization_member(request.user,organization_id,'admin');form=InvitationForm(request.POST)
    if not form.is_valid():return render(request,'control/form.html',{'title':'Invite team member','form':form},status=400)
    role=form.cleaned_data['role']
    if member.role!='owner' and role in {'owner','admin'}:raise Http404
    token=secrets.token_urlsafe(32)
    invitation=Invitation.objects.create(organization=member.organization,email=form.cleaned_data['email'].lower(),role=role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),invited_by=request.user,expires_at=timezone.now()+timedelta(days=2))
    link=request.build_absolute_uri(reverse('accept_invitation',args=[token]))
    try:send_mail('ResMgrCheck team invitation','Sign in with your verified email to review and accept this invitation: '+link,settings.DEFAULT_FROM_EMAIL,[invitation.email],fail_silently=False)
    except Exception:
        audit(request.user,'invitation.delivery_error',member.organization,invitation.pk)
        return render(request,'control/message.html',{'title':'Invitation delivery unavailable','message':'The invitation was saved, but email delivery failed. Contact the operator; no account was marked verified.'},status=503)
    audit(request.user,'invitation.created',member.organization,invitation.pk,role=role)
    messages.success(request,'Invitation sent. It expires after two days.');return redirect('team',organization_id=organization_id)

@secure_account
def accept_invitation(request,token):
    if not 40<=len(token)<=60:raise Http404
    identifier=hashlib.sha256(token.encode()).hexdigest()
    with transaction.atomic():
        invitation=get_object_or_404(Invitation.objects.select_for_update().select_related('organization'),token_hash=identifier,accepted_at=None,expires_at__gt=timezone.now(),organization__active=True,email__iexact=request.user.email)
        if request.method=='POST':
            if invitation.role in {'owner','admin'}:
                response=require_mfa(request,900)
                if response:return response
            if Membership.objects.filter(user=request.user,organization=invitation.organization,active=True).exists():
                return render(request,'control/message.html',{'title':'Already a member','message':'Existing privileges must be changed by the organization owner.'},status=400)
            Membership.objects.update_or_create(user=request.user,organization=invitation.organization,defaults={'role':invitation.role,'active':True})
            invitation.accepted_at=timezone.now();invitation.save(update_fields=['accepted_at'])
            audit(request.user,'invitation.accepted',invitation.organization,invitation.pk,role=invitation.role)
            return redirect('overview')
    return render(request,'control/confirm.html',{'title':'Accept team invitation','message':f'Join {invitation.organization.name} as {invitation.role}?','button':'Accept invitation'})

@secure_account(recent=900)
@require_POST
def member_update(request,organization_id,user_id):
    actor=organization_member(request.user,organization_id,'admin');form=MemberForm(request.POST)
    if not form.is_valid():return HttpResponse('Invalid membership fields.',status=400)
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=actor.organization_id)
        target=get_object_or_404(Membership,organization=actor.organization,user_id=user_id)
        new_role=form.cleaned_data['role'];active=form.cleaned_data['active']
        if actor.role!='owner' and (target.role in {'owner','admin'} or new_role in {'owner','admin'}):raise Http404
        if target.role=='owner' and (not active or new_role!='owner'):
            if not Membership.objects.filter(organization=actor.organization,active=True,role='owner').exclude(pk=target.pk).exists():
                return HttpResponse('Keep at least one active owner. Transfer ownership first.',status=409)
        target.role=new_role;target.active=active;target.save(update_fields=['role','active'])
        # Membership is rechecked on every request/job. An organization administrator
        # cannot revoke this user's unrelated organizations or global sessions.
        audit(request.user,'membership.changed',actor.organization,user_id,role=new_role,active=active)
    return redirect('team',organization_id=organization_id)

@secure_account
@require_POST
def project_member(request,project_id):
    project,role=project_access(request.user,project_id,'admin');form=ProjectMemberForm(request.POST)
    if not form.is_valid():return HttpResponse('Invalid project membership fields.',status=400)
    target=get_object_or_404(Membership,organization=project.organization,user_id=form.cleaned_data['user_id'],active=True)
    if RANK[form.cleaned_data['role']]>RANK[target.role]:return HttpResponse('Project role cannot exceed organization role.',status=400)
    ProjectMembership.objects.update_or_create(project=project,user=target.user,defaults={'role':form.cleaned_data['role']})
    audit(request.user,'project.membership_changed',project.organization,project.pk,user_id=str(target.user_id),role=form.cleaned_data['role'])
    return redirect('project',project_id=project_id)

@secure_account
def account_settings(request):
    return render(request,'control/account.html',{'sessions_form':PasswordConfirmation(auto_id='sessions_%s'),'deletion_form':PasswordConfirmation(auto_id='deletion_%s')})

@secure_account
@require_POST
def logout_all(request):
    form=PasswordConfirmation(request.POST)
    if not form.is_valid() or not request.user.check_password(form.cleaned_data['password']):return HttpResponse('Password confirmation failed.',status=400)
    user=request.user
    User.objects.filter(pk=user.pk).update(session_version=F('session_version')+1)
    for session in UserSession.objects.filter(user=user):session.end()
    audit(user,'account.sessions_revoked');logout(request)
    return redirect('account_login')

@secure_account
@require_GET
def account_export(request):
    audit(request.user,'account.exported')
    response=JsonResponse({'email':request.user.email,'user_id':str(request.user.pk),'memberships':list(Membership.objects.filter(user=request.user).values('organization_id','role','active'))})
    response['Content-Disposition']='attachment; filename="resmgrcheck-account.json"';return response

@secure_account
@require_POST
def account_delete(request):
    form=PasswordConfirmation(request.POST)
    if not form.is_valid() or not request.user.check_password(form.cleaned_data['password']):return HttpResponse('Password confirmation failed.',status=400)
    with transaction.atomic():
        owned=Membership.objects.filter(user=request.user,active=True,role='owner',organization__active=True)
        for membership in owned:
            Organization.objects.select_for_update().get(pk=membership.organization_id)
            if not Membership.objects.filter(organization=membership.organization,active=True,role='owner').exclude(user=request.user).exists():return HttpResponse('Transfer sole organization ownership before deleting your account.',status=409)
        AccountDeletion.objects.get_or_create(user=request.user,defaults={'due_at':timezone.now()+timedelta(days=30)})
        user=request.user;user.is_active=False;user.save(update_fields=['is_active'])
        Membership.objects.filter(user=user).update(active=False)
        for session in UserSession.objects.filter(user=user):session.end()
        audit(user,'account.deletion_requested');logout(request)
    return render(request,'control/message.html',{'title':'Account disabled','message':'Sessions and memberships are revoked. Personal-data deletion is scheduled after the 30-day retention window; retained organization evidence follows its separate policy.'})

@secure_account
@require_GET
def audit_log(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    return render(request,'control/audit.html',{'organization':member.organization,'events':AuditEvent.objects.filter(organization=member.organization)[:200]})
