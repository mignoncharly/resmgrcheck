"""Administrators and revocable access sessions; checks repeat at every boundary."""
from functools import wraps
import hashlib,hmac,time
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect,get_object_or_404
from django.utils import timezone
from django.urls import reverse
from allauth.account.internal.flows.login import get_authentication_records
from allauth.mfa.models import Authenticator
from .models import AuditEvent,Membership,Project,ProjectMembership,RateBucket,Organization,AccessSession,AccessGrant,Run,Target,SourceSubmission,AIAnalysis

RANK={'viewer':1,'developer':2,'admin':3,'owner':4}

class AccessPrincipal:
    is_authenticated=True;is_anonymous=False;is_staff=False;is_superuser=False;is_code=True
    email=None
    def __init__(self,session):self.access_session=session;self.pk=session.pk;self.id=session.pk
    @property
    def username(self):return self.access_session.code.description
    @property
    def is_active(self):return session_valid(self.access_session)
    def __str__(self):return self.username

def is_code(user):return bool(getattr(user,'is_code',False))

def session_valid(session):
    now=timezone.now();code=session.code
    return (session.revoked_at is None and code.revoked_at is None and session.policy_version==code.policy_version
        and session.expires_at>now and session.last_access>now-timedelta(minutes=30)
        and (code.expires_at is None or code.expires_at>now) and code.organization.active)

def principal_fields(user):
    return {'actor':None,'access_session':user.access_session} if is_code(user) else {'actor':user,'access_session':None}

def job_principal(record):
    return AccessPrincipal(record.access_session) if record.access_session_id else record.actor

def audit(actor,action,organization=None,object_id='',**details):
    values={'access_session_id':actor.pk,'access_code_id':actor.access_session.code_id} if is_code(actor) else {'actor':actor if getattr(actor,'is_authenticated',False) else None}
    return AuditEvent.objects.create(**values,organization=organization,action=action,object_id=str(object_id),details=details)

def verified(user):
    """Active principal; legacy name is not email verification."""
    if not getattr(user,'is_authenticated',False):return False
    if is_code(user):
        current=AccessSession.objects.select_related('code__organization').filter(pk=user.pk).first()
        if not current:return False
        user.access_session=current
        return session_valid(current)
    return user.is_active and user.is_staff and bool(user.username)

def enrolled(user):return not is_code(user) and getattr(user,'is_authenticated',False) and Authenticator.objects.filter(user=user,type='totp').exists()

def mfa_authenticated(request,recent=43200):
    if is_code(request.user):return verified(request.user)
    records=get_authentication_records(request,request.user)
    return enrolled(request.user) and any(r.get('method')=='mfa' and r.get('at',0)>time.time()-recent for r in records)

def assurance_at(request):
    if is_code(request.user):return timezone.now()
    from datetime import datetime,timezone as tz
    records=[r['at'] for r in get_authentication_records(request,request.user) if r.get('method')=='mfa']
    if not records:raise Http404
    return datetime.fromtimestamp(max(records),tz.utc)

def require_mfa(request,recent=43200):
    if is_code(request.user):return None if verified(request.user) else redirect('developer_access')
    if not enrolled(request.user):return redirect('mfa_activate_totp')
    if not mfa_authenticated(request,recent):return redirect(reverse('mfa_reauthenticate')+'?next='+request.path)
    return None

def secure_account(view=None,*,strong=False,recent=43200):
    def decorator(function):
        @wraps(function)
        def wrapped(request,*args,**kwargs):
            if not verified(request.user):return redirect('developer_access')
            if not is_code(request.user):
                response=require_mfa(request,recent)
                if response:return response
            return function(request,*args,**kwargs)
        return wrapped
    return decorator(view) if view else decorator

def administrator(view=None,*,recent=900):
    def decorate(function):
        @secure_account(recent=recent)
        @wraps(function)
        def wrapped(request,*args,**kwargs):
            if is_code(request.user):raise Http404
            return function(request,*args,**kwargs)
        return wrapped
    return decorate(view) if view else decorate

def organization_member(user,identifier,minimum='viewer'):
    if is_code(user) or not verified(user):raise Http404
    if user.is_superuser:return Membership(organization=get_object_or_404(Organization,pk=identifier,active=True),user=user,role='owner')
    membership=get_object_or_404(Membership.objects.select_related('organization'),user=user,organization_id=identifier,active=True,organization__active=True)
    if RANK.get(membership.role,0)<RANK[minimum]:raise Http404
    return membership

def grant_for(user,project_id):
    if not is_code(user) or not verified(user):raise Http404
    return get_object_or_404(AccessGrant.objects.select_related('code','project__organization'),code=user.access_session.code,project_id=project_id,project__active=True,project__organization__active=True)

def project_access(user,identifier,minimum='viewer'):
    project=get_object_or_404(Project.objects.select_related('organization'),pk=identifier,active=True,organization__active=True)
    if is_code(user):
        grant=grant_for(user,identifier)
        role='developer' if grant.can_run and grant.code.allow_live or grant.can_ai and grant.code.allow_ai else 'viewer'
        if minimum in {'admin','owner'} or RANK[role]<RANK[minimum]:raise Http404
        return project,role
    member=organization_member(user,project.organization_id)
    if member.role in {'owner','admin'}:role=member.role
    else:
        direct=ProjectMembership.objects.filter(user=user,project=project).first()
        role=direct.role if direct and RANK.get(direct.role,0)<=RANK.get(member.role,0) else 'none'
    if RANK.get(role,0)<RANK[minimum]:raise Http404
    return project,role

def permission(user,project_id,action,target=None,run=None):
    project,role=project_access(user,project_id,'viewer' if action in {'view','download'} else 'developer')
    if not is_code(user):return project,role
    grant=grant_for(user,project_id)
    if action in {'run','inventory','replay','cancel'} and not (grant.can_run and grant.code.allow_live):raise Http404
    if action in {'ai','source'} and not (grant.can_ai and grant.code.allow_ai):raise Http404
    if action=='download' and not grant.can_download:raise Http404
    if target is not None and not grant.targets.filter(pk=target.pk).exists():raise Http404
    if run is not None and not visible_runs(user).filter(pk=run.pk).exists():raise Http404
    return project,role

def visible_projects(user):
    if is_code(user):
        if not verified(user):return Project.objects.none()
        return Project.objects.filter(active=True,organization__active=True,accessgrant__code_id=user.access_session.code_id).distinct()
    if not verified(user):return Project.objects.none()
    if user.is_superuser:return Project.objects.filter(active=True,organization__active=True)
    orgs=Membership.objects.filter(user=user,active=True,organization__active=True)
    return Project.objects.filter(active=True,organization__active=True).filter(Q(organization_id__in=orgs.filter(role__in=['owner','admin']).values('organization_id'))|Q(organization_id__in=orgs.values('organization_id'),projectmembership__user=user)).distinct()

def visible_targets(user):
    targets=Target.objects.filter(project__in=visible_projects(user))
    if is_code(user):targets=targets.filter(accessgrant__code_id=user.access_session.code_id)
    return targets.distinct()

def visible_runs(user):
    runs=Run.objects.filter(project__in=visible_projects(user))
    if not is_code(user):return runs
    code_id=user.access_session.code_id
    return runs.filter(Q(project__accessgrant__code_id=code_id,project__accessgrant__all_evidence=True)|Q(accessgrant__code_id=code_id)|Q(access_session__code_id=code_id)).filter(target__in=visible_targets(user)).distinct()

def visible_sources(user,project_id):
    project_access(user,project_id)
    sources=SourceSubmission.objects.filter(project_id=project_id)
    return sources.filter(access_session__code_id=user.access_session.code_id) if is_code(user) else sources

def visible_analyses(user):
    analyses=AIAnalysis.objects.filter(run__in=visible_runs(user))
    return analyses.filter(access_session__code_id=user.access_session.code_id).filter(Q(compared_run__isnull=True)|Q(compared_run__in=visible_runs(user))) if is_code(user) else analyses

def consume_rate(scope,identity,limit,seconds):
    now=timezone.now();window=int(now.timestamp())//seconds
    key=hmac.new(settings.SECRET_KEY.encode(),f'{scope}:{identity}:{window}'.encode(),hashlib.sha256).hexdigest()
    with transaction.atomic():
        RateBucket.objects.get_or_create(key=key,defaults={'expires_at':now+timedelta(seconds=seconds*2)})
        bucket=RateBucket.objects.select_for_update().get(key=key)
        if bucket.count>=limit:return False
        bucket.count+=1;bucket.save(update_fields=['count'])
    return True

def start_authority(record,action='run'):
    """Serialize code revocation with the exact local child creation, not its operation."""
    from contextlib import contextmanager
    from .models import AccessCode
    @contextmanager
    def guard():
        with transaction.atomic():
            actor=job_principal(record)
            if is_code(actor):AccessCode.objects.select_for_update().get(pk=actor.access_session.code_id)
            elif actor is not None:
                from .models import User
                actor=User.objects.select_for_update(no_key=True).get(pk=actor.pk)
            from .engine import PolicyError
            from .jobs import auth_fingerprint
            try:
                if not verified(actor) or auth_fingerprint(actor)!=record.actor_auth_hash:raise Http404
                if not is_code(actor) and not enrolled(actor):raise Http404
                execution=getattr(record,'run',record)
                permission(actor,execution.project_id,action,target=execution.target,run=execution if action=='ai' else execution.original if execution.original_id else None)
            except Http404:raise PolicyError('authorization_revoked_before_child') from None
            yield
    return guard()
