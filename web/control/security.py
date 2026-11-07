"""Authorization is repeated at views, storage and delayed execution boundaries."""
from functools import wraps
import hashlib,hmac,time
from datetime import datetime,timedelta,timezone as dt_timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect,render,get_object_or_404
from django.utils import timezone
from django.urls import reverse
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.login import get_authentication_records
from allauth.mfa.models import Authenticator
from .models import AuditEvent,Membership,Project,ProjectMembership,RateBucket,Organization

RANK={'viewer':1,'developer':2,'admin':3,'owner':4}

def audit(actor,action,organization=None,object_id='',**details):
    # Callers supply safe structured facts; never raw requests/source/provider payloads.
    return AuditEvent.objects.create(actor=actor if getattr(actor,'is_authenticated',False) else None,
        organization=organization,action=action,object_id=str(object_id),details=details)

def verified(user):
    return user.is_authenticated and user.is_active and EmailAddress.objects.filter(user=user,email__iexact=user.email,verified=True).exists()

def enrolled(user):
    return user.is_authenticated and Authenticator.objects.filter(user=user,type='totp').exists()

def mfa_authenticated(request,recent=43200):
    records=get_authentication_records(request,request.user)
    return enrolled(request.user) and any(r.get('method')=='mfa' and r.get('at',0)>time.time()-recent for r in records)

def require_mfa(request,recent=43200):
    if not enrolled(request.user):return redirect('mfa_activate_totp')
    if not mfa_authenticated(request,recent):return redirect(reverse('mfa_reauthenticate')+'?next='+request.path)
    return None

def secure_account(view=None,*,strong=False,recent=43200):
    def decorator(function):
        @wraps(function)
        def wrapped(request,*args,**kwargs):
            if not request.user.is_authenticated:return redirect(reverse('account_login')+'?next='+request.path)
            if not verified(request.user):return render(request,'control/message.html',{'title':'Verify your email','message':'Verify your account email before accessing projects.','action_url':reverse('account_email'),'action_text':'Email settings'},status=403)
            privileged=Membership.objects.filter(user=request.user,active=True,organization__active=True,role__in=['owner','admin']).exists() or request.user.is_staff
            if strong or privileged:
                response=require_mfa(request,recent)
                if response:return response
            return function(request,*args,**kwargs)
        return wrapped
    return decorator(view) if view else decorator

def organization_member(user,identifier,minimum='viewer'):
    membership=get_object_or_404(Membership.objects.select_related('organization'),user=user,organization_id=identifier,active=True,organization__active=True)
    if RANK.get(membership.role,0)<RANK[minimum]:raise Http404
    return membership

def project_access(user,identifier,minimum='viewer'):
    project=get_object_or_404(Project.objects.select_related('organization'),pk=identifier,active=True,organization__active=True)
    member=Membership.objects.filter(user=user,organization=project.organization,active=True).first()
    if not member:raise Http404
    if member.role in {'owner','admin'}:role=member.role
    else:
        direct=ProjectMembership.objects.filter(user=user,project=project).first()
        role=direct.role if direct and RANK.get(direct.role,0)<=RANK.get(member.role,0) else 'none'
    if RANK.get(role,0)<RANK[minimum]:raise Http404
    return project,role

def visible_projects(user):
    orgs=Membership.objects.filter(user=user,active=True,organization__active=True)
    admin_ids=orgs.filter(role__in=['owner','admin']).values('organization_id')
    member_ids=orgs.values('organization_id')
    return Project.objects.filter(active=True,organization__active=True).filter(Q(organization_id__in=admin_ids)|Q(organization_id__in=member_ids,projectmembership__user=user)).distinct()

def consume_rate(scope,identity,limit,seconds):
    now=timezone.now();window=int(now.timestamp())//seconds
    key=hmac.new(settings.SECRET_KEY.encode(),f'{scope}:{identity}:{window}'.encode(),hashlib.sha256).hexdigest()
    with transaction.atomic():
        RateBucket.objects.get_or_create(key=key,defaults={'expires_at':now+timedelta(seconds=seconds*2)})
        bucket=RateBucket.objects.select_for_update().get(key=key)
        if bucket.count>=limit:return False
        bucket.count+=1;bucket.save(update_fields=['count'])
    return True
