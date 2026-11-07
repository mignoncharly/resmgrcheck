from django.db import connection,transaction
from django.db.models import F
from django.http import JsonResponse,HttpResponse,Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_GET,require_POST,require_http_methods
from django.contrib.auth import logout
from allauth.usersessions.models import UserSession
from .models import User,Organization,Membership,Project,ProjectMembership,AuditEvent
from .forms import OrganizationForm,ProjectForm,MemberForm,ProjectMemberForm,PasswordConfirmation
from .security import administrator,secure_account,organization_member,project_access,audit,RANK

@require_GET
def health(request):return JsonResponse({'status':'alive'})
@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:cursor.execute('SELECT 1');cursor.fetchone()
    except Exception:return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ready'})

@administrator
@require_http_methods(['GET','POST'])
def organization_create(request):
    form=OrganizationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            organization=form.save();Membership.objects.create(organization=organization,user=request.user,role='owner')
            audit(request.user,'organization.created',organization,organization.pk)
        return redirect('team',organization_id=organization.pk)
    return render(request,'control/form.html',{'title':'Create organization','form':form})

@administrator
@require_http_methods(['GET','POST'])
def project_create(request,organization_id):
    member=organization_member(request.user,organization_id,'admin');form=ProjectForm(request.POST or None)
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
def project_api(request,project_id):
    project,role=project_access(request.user,project_id)
    return JsonResponse({'id':str(project.pk),'organization_id':str(project.organization_id),'name':project.name,'role':role})

@administrator
@require_GET
def team(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    return render(request,'control/team.html',{'organization':member.organization,'memberships':Membership.objects.filter(organization=member.organization,user__is_staff=True).select_related('user'),'actor_role':member.role})

@administrator
@require_POST
def member_update(request,organization_id,user_id):
    actor=organization_member(request.user,organization_id,'admin');form=MemberForm(request.POST)
    if not form.is_valid():return HttpResponse('Invalid membership fields.',status=400)
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=actor.organization_id)
        target=get_object_or_404(Membership,organization=actor.organization,user_id=user_id,user__is_staff=True)
        new_role=form.cleaned_data['role'];active=form.cleaned_data['active']
        if actor.role!='owner' and (target.role in {'owner','admin'} or new_role in {'owner','admin'}):raise Http404
        if target.role=='owner' and (not active or new_role!='owner'):
            if not Membership.objects.filter(organization=actor.organization,active=True,role='owner',user__is_active=True,user__is_staff=True).exclude(pk=target.pk).exists():return HttpResponse('Keep an active administrator owner.',status=409)
        target.role=new_role;target.active=active;target.save(update_fields=['role','active'])
        audit(request.user,'administrator.membership_changed',actor.organization,user_id,role=new_role,active=active)
    return redirect('team',organization_id=organization_id)

@administrator
@require_POST
def project_member(request,project_id):
    project,role=project_access(request.user,project_id,'admin');form=ProjectMemberForm(request.POST)
    if not form.is_valid():return HttpResponse('Invalid administrator project fields.',status=400)
    target=get_object_or_404(Membership,organization=project.organization,user_id=form.cleaned_data['user_id'],active=True,user__is_staff=True)
    if RANK[form.cleaned_data['role']]>RANK[target.role]:return HttpResponse('Project role cannot exceed organization role.',status=400)
    ProjectMembership.objects.update_or_create(project=project,user=target.user,defaults={'role':form.cleaned_data['role']})
    audit(request.user,'project.administrator_changed',project.organization,project.pk,user_id=str(target.user_id),role=form.cleaned_data['role'])
    return redirect('project',project_id=project_id)

@administrator
@require_GET
def account_settings(request):
    return render(request,'control/account.html',{'sessions_form':PasswordConfirmation(),'sessions':UserSession.objects.filter(user=request.user).order_by('-created_at')[:30]})

@administrator
@require_GET
def administrator_sessions(request):
    # No legacy allauth email/manage template and no session keys in rendered HTML.
    sessions=UserSession.objects.filter(user=request.user).order_by('-created_at')[:100]
    return render(request,'control/administrator_sessions.html',{'sessions':sessions,'sessions_form':PasswordConfirmation()})

@administrator
@require_POST
def logout_all(request):
    form=PasswordConfirmation(request.POST)
    if not form.is_valid() or not request.user.check_password(form.cleaned_data['password']):return HttpResponse('Password confirmation failed.',status=400)
    user=request.user;User.objects.filter(pk=user.pk).update(session_version=F('session_version')+1)
    for session in UserSession.objects.filter(user=user):session.end()
    audit(user,'administrator.sessions_revoked');logout(request);return redirect('account_login')

@administrator
@require_GET
def audit_log(request,organization_id):
    member=organization_member(request.user,organization_id,'admin')
    return render(request,'control/audit.html',{'organization':member.organization,'events':AuditEvent.objects.filter(organization=member.organization)[:100]})
