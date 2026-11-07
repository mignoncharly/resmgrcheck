"""Private single-consumer AI service. Uncertain provider calls are never retried."""
from datetime import timedelta
import fcntl,hashlib,os,uuid
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.http import Http404
from resmgrcheck.contracts import canonical
from .models import AIAnalysis,AIProviderState,AILease,AIUsage,SourceSubmission
from .security import project_access,verified,enrolled,audit
from .jobs import auth_fingerprint
from .engine import PolicyError
from .storage import verify_inventory,detail_cases
from .ai_provider import configuration,bounded_invoke,reservation,cost,OUTPUT_LIMIT
from .ai_evidence import validate_answer

def refresh_provider():
    try:provider=configuration()
    except PolicyError:
        AIProviderState.objects.update_or_create(name='default',defaults={'policy':{},'available':False,'refreshed_at':timezone.now()});return None
    previous=AIProviderState.objects.filter(name='default').first()
    defaults={'policy':provider.public(),'available':True,'refreshed_at':timezone.now()}
    if previous and previous.policy!=provider.public():defaults['verified_at']=None
    AIProviderState.objects.update_or_create(name='default',defaults=defaults)
    return provider

def claim():
    now=timezone.now()
    with transaction.atomic():
        AILease.objects.get_or_create(name='provider')
        slot=AILease.objects.select_for_update().get(name='provider')
        if slot.analysis_id:
            if slot.expires_at>now:return None
            old=AIAnalysis.objects.select_for_update().get(pk=slot.analysis_id)
            if old.state=='running':
                old.state='uncertain';old.error_code='ai_provider_outcome_uncertain_no_retry';old.finished_at=now;old.save(update_fields=['state','error_code','finished_at'])
                audit(old.actor,'ai.outcome_uncertain',old.run.project.organization,old.pk,reservation_retained=True,retry_performed=False)
            slot.analysis=None;slot.token=None;slot.expires_at=None;slot.save()
        job=AIAnalysis.objects.select_for_update(skip_locked=True).filter(state='queued').order_by('created_at').first()
        if not job:return None
        token=uuid.uuid4();slot.analysis=job;slot.token=token;slot.expires_at=now+timedelta(seconds=60);slot.save()
        job.state='running';job.started_at=now;job.save(update_fields=['state','started_at'])
        return job.pk,token

def execute(identifier,token):
    analysis=AIAnalysis.objects.select_related('run__project__organization','actor','source','compared_run').get(pk=identifier)
    attempted=False;lock=None
    try:
        lock_root=settings.PRIVATE_ROOT/'ai-locks';lock_root.mkdir(mode=0o700,parents=True,exist_ok=True)
        lock=os.open(lock_root/'provider.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise PolicyError('ai_existing_worker_owns_provider') from None
        slot=AILease.objects.get(name='provider')
        if slot.analysis_id!=analysis.pk or slot.token!=token or slot.expires_at<=timezone.now():raise PolicyError('ai_lease_lost')
        provider=configuration()
        if provider.public()!=analysis.pricing:raise PolicyError('ai_provider_policy_changed')
        if not verified(analysis.actor) or not enrolled(analysis.actor) or auth_fingerprint(analysis.actor)!=analysis.actor_auth_hash:raise PolicyError('ai_actor_authorization_revoked')
        project_access(analysis.actor,analysis.run.project_id,'developer')
        project=analysis.run.project
        if not project.ai_enabled or project.ai_daily_budget_microusd==0:raise PolicyError('ai_project_disabled')
        if analysis.created_at<timezone.now()-timedelta(minutes=15) or analysis.mfa_at<timezone.now()-timedelta(minutes=15):raise PolicyError('ai_queued_consent_expired')
        verify_inventory(analysis.run);detail_cases(analysis.run)
        if analysis.compared_run:
            if analysis.compared_run.project_id!=project.pk:raise PolicyError('ai_comparison_tenant_mismatch')
            verify_inventory(analysis.compared_run);detail_cases(analysis.compared_run)
        if analysis.source and (analysis.source.project_id!=project.pk or analysis.source.erased_at or analysis.source.expires_at<=timezone.now()):raise PolicyError('ai_source_tenant_or_expiry')
        digest=hashlib.sha256(canonical({'payload':analysis.payload,'citations':analysis.citations,'policy':analysis.pricing})).hexdigest()
        if digest!=analysis.input_sha256:raise PolicyError('ai_input_identity_changed')
        maximum,input_bound=reservation(analysis.payload,provider)
        if maximum!=analysis.reserved_microusd:raise PolicyError('ai_reservation_identity_changed')
        attempted=True
        result,usage,model,response_id,request_id=bounded_invoke(analysis.payload,provider)
        if usage['input_tokens']>input_bound or usage['output_tokens']>OUTPUT_LIMIT:raise PolicyError('ai_usage_exceeded_reserved_bound')
        result=validate_answer(result,analysis.citations,bool(analysis.source_id),analysis.task);accounted=cost(usage['input_tokens'],usage['output_tokens'],provider)
        if accounted>maximum:raise PolicyError('ai_usage_exceeded_reservation')
        with transaction.atomic():
            slot=AILease.objects.select_for_update().get(name='provider')
            if slot.analysis_id!=analysis.pk or slot.token!=token:raise PolicyError('ai_lease_lost')
            current=AIAnalysis.objects.select_for_update().get(pk=analysis.pk)
            if current.state!='running':raise PolicyError('ai_lease_lost')
            # Reauthorization after the remote call also gates disclosure.
            analysis.actor.refresh_from_db();project.refresh_from_db()
            if not verified(analysis.actor) or auth_fingerprint(analysis.actor)!=analysis.actor_auth_hash or not project.ai_enabled:raise PolicyError('ai_authority_withdrawn_after_call')
            project_access(analysis.actor,project.pk,'developer')
            for scope in ['global','project:'+str(project.pk)]:
                entry=AIUsage.objects.select_for_update().get(scope=scope,day=analysis.created_at.date())
                entry.accounted_microusd-=maximum-accounted;entry.save(update_fields=['accounted_microusd'])
            current.result=result;current.usage=usage;current.accounted_microusd=accounted;current.usage_established=True
            current.output_sha256=hashlib.sha256(canonical(result)).hexdigest()
            current.resolved_model=model;current.provider_response_id=response_id;current.provider_request_id=request_id;current.state='completed';current.finished_at=timezone.now()
            current.save(update_fields=['result','output_sha256','usage','accounted_microusd','usage_established','resolved_model','provider_response_id','provider_request_id','state','finished_at'])
            AIProviderState.objects.filter(name='default').update(verified_at=timezone.now())
            audit(analysis.actor,'ai.completed',project.organization,analysis.pk,provider=provider.name,model=model,input_sha256=digest,accounted_microusd=accounted)
    except (PolicyError,Http404,ValueError,OSError,TypeError,KeyError) as error:
        code=str(error) if isinstance(error,PolicyError) else 'ai_retrieval_or_validation_failed'
        with transaction.atomic():
            slot=AILease.objects.select_for_update().get(name='provider')
            if slot.analysis_id==analysis.pk and slot.token==token:
                AIAnalysis.objects.filter(pk=analysis.pk,state='running').update(state='error',error_code=code,finished_at=timezone.now())
                audit(analysis.actor,'ai.withheld',analysis.run.project.organization,analysis.pk,reason=code,provider_attempted=attempted,reservation_retained=True)
        # Full reservation is conservatively retained on failure, never called a
        # confirmed provider charge. No raw provider exception/body is logged.
    finally:
        with transaction.atomic():
            slot=AILease.objects.select_for_update().get(name='provider')
            if slot.analysis_id==analysis.pk and slot.token==token:slot.analysis=None;slot.token=None;slot.expires_at=None;slot.save()
        if lock is not None:os.close(lock)
