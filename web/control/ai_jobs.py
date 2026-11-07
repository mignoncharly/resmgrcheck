"""Consent-bound durable AI jobs and conservative cost reservation, independent of QNX."""
from datetime import timedelta,datetime,timezone as dt_timezone
import hashlib,uuid,re
from django.db import transaction
from django.utils import timezone
from allauth.account.internal.flows.login import get_authentication_records
from resmgrcheck.contracts import canonical
from .models import AIAnalysis,AIProviderState,AIUsage,AILease,Project,Run
from .security import project_access,verified,mfa_authenticated,audit,permission,principal_fields,assurance_at
from .jobs import auth_fingerprint
from .engine import PolicyError
from .ai_provider import Provider,reservation

def public_provider():
    state=AIProviderState.objects.filter(name='default',available=True,refreshed_at__gte=timezone.now()-timedelta(minutes=2)).first()
    if not state:raise PolicyError('ai_provider_disabled_or_worker_unavailable')
    p=state.policy
    try:return Provider(p['provider'],p['model'],'',p['input_microusd_per_million'],p['output_microusd_per_million'],p['global_daily_microusd'],p['request_cap_microusd'],p['reviewed_at'])
    except (KeyError,TypeError):raise PolicyError('ai_policy_unavailable') from None

def enqueue_analysis(request,run,task,payload,citations,key,source=None,compared=None):
    permission(request.user,run.project_id,'ai',target=run.target,run=run)
    if not verified(request.user) or not mfa_authenticated(request,900):raise PolicyError('ai_recent_mfa_required')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}',key):raise PolicyError('ai_idempotency_key_invalid')
    provider=public_provider();maximum,_=reservation(payload,provider)
    digest=hashlib.sha256(canonical({'payload':payload,'citations':citations,'policy':provider.public()})).hexdigest()
    authorized_at=assurance_at(request)
    with transaction.atomic():
        AILease.objects.get_or_create(name='scheduling')
        AILease.objects.select_for_update().get(name='scheduling')
        current=Run.objects.select_for_update().get(pk=run.pk)
        if current.purged_at or current.state not in {'completed','blocked'}:raise PolicyError('ai_native_evidence_unavailable')
        project=Project.objects.select_for_update().get(pk=run.project_id)
        if not project.ai_enabled or project.ai_daily_budget_microusd<=0:raise PolicyError('ai_project_disabled_or_zero_budget')
        existing=AIAnalysis.objects.filter(**principal_fields(request.user),run=run,idempotency_key=key).first()
        if existing:
            if existing.input_sha256!=digest:raise PolicyError('ai_idempotency_intent_conflict')
            return existing,False
        if AIAnalysis.objects.filter(state__in=['queued','running']).count()>=10:raise PolicyError('ai_queue_full')
        day=timezone.now().date()
        for scope,limit,count in [('global',provider.global_daily,100),('project:'+str(project.pk),project.ai_daily_budget_microusd,20)]:
            AIUsage.objects.get_or_create(scope=scope,day=day)
            usage=AIUsage.objects.select_for_update().get(scope=scope,day=day)
            if usage.accounted_microusd+maximum>limit or usage.requests>=count:raise PolicyError('ai_daily_budget_or_request_limit')
            usage.accounted_microusd+=maximum;usage.requests+=1;usage.save(update_fields=['accounted_microusd','requests'])
        analysis=AIAnalysis.objects.create(run=run,**principal_fields(request.user),source=source,compared_run=compared,actor_auth_hash=auth_fingerprint(request.user),
            mfa_at=authorized_at,idempotency_key=key,task=task,input_sha256=digest,payload=payload,citations=citations,
            provider=provider.name,requested_model=provider.model,pricing=provider.public(),reserved_microusd=maximum,accounted_microusd=maximum)
        audit(request.user,'ai.consent_and_reservation',run.project.organization,analysis.pk,input_sha256=digest,task=task,
            provider=provider.name,model=provider.model,reserved_microusd=maximum,source_included=bool(source),comparison_included=bool(compared),consent_version=analysis.consent_version)
        return analysis,True
