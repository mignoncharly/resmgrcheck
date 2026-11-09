"""Tenant-bound scheduling, deduplication and immutable engine intent."""
import hashlib,re,uuid
from datetime import datetime,timezone as dt_timezone,timedelta
from django.conf import settings
from django.core.exceptions import ValidationError,ObjectDoesNotExist
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from allauth.account.internal.flows.login import get_authentication_records
from .models import Run,Target,BuildRelease,ExecutorSlot
from .security import project_access,verified,enrolled,audit,mfa_authenticated,is_code,principal_fields,permission,assurance_at
from resmgrcheck.contracts import digest

ACTIVE={'queued','claimed','starting','running','collecting','launch_uncertain'}

class QueueError(Exception):pass


def auth_fingerprint(user):
    if is_code(user):
        session=user.access_session
        return hashlib.sha256((str(session.pk)+':'+str(session.code_id)+':'+str(session.policy_version)+':'+session.browser_key_hash).encode()).hexdigest()
    return hashlib.sha256((user.password+':'+str(user.session_version)).encode()).hexdigest()


def enqueue(request,project,target,build,*,profile,suite,mode,key,original=None,operation='run'):
    permission(request.user,project.pk,'inventory' if operation=='inventory' else 'replay' if operation=='replay' else 'run',target=target,run=original)
    if not verified(request.user) or not mfa_authenticated(request,900):raise QueueError('recent_verified_mfa_required')
    if target.project_id!=project.pk or not target.approved:raise QueueError('target_not_approved')
    if target.state=='quarantined':raise QueueError('target_quarantined')
    if target.kind=='customer-request' or (target.kind=='external-health' and suite!='health'):raise QueueError('required_capability_unsupported')
    if operation!='inventory' and (not build or build.target_id!=target.pk or not build.approved):raise QueueError('build_not_approved')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}',key):raise QueueError('idempotency_key_invalid')
    if operation not in {'run','replay','inventory'} or profile not in {'sensor','job'} or suite not in {'profile','lifecycle','health'} or mode not in {'fixed','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'}:raise QueueError('execution_selection_invalid')
    if operation=='replay' and (not original or original.project_id!=project.pk or original.state!='completed' or original.purged_at):raise QueueError('original_evidence_unavailable')
    if target.kind=='customer-runner':
        if operation=='inventory':raise QueueError('customer_inventory_uses_signed_heartbeat')
        from .runner_jobs import capable
        from customer_runner.protocol import ProtocolError
        try:capable(target,build,profile,suite,mode)
        except (ProtocolError,ValueError,OSError,ObjectDoesNotExist):raise QueueError('customer_runner_capability_or_approval_unavailable') from None
    intent={'project':str(project.pk),'target':str(target.pk),'build':str(build.pk) if build else None,'operation':operation,'profile':profile,'suite':suite,'mode':mode,'original':str(original.pk) if original else None}
    fingerprint=digest(intent)
    authorized_at=assurance_at(request)
    with transaction.atomic():
        slot,_=ExecutorSlot.objects.get_or_create(name='dispatch')
        ExecutorSlot.objects.select_for_update().get(pk=slot.pk)
        existing=Run.objects.filter(project=project,**principal_fields(request.user),idempotency_key=key).first()
        if existing:
            if existing.intent_sha256!=fingerprint:raise QueueError('idempotency_intent_conflict')
            return existing,False
        if target.kind=='customer-runner':
            from .models import CustomerRunner
            Target.objects.select_for_update().get(pk=target.pk)
            runner=CustomerRunner.objects.select_for_update().get(pk=target.pk)
            try:capable(target,build,profile,suite,mode)
            except (ProtocolError,ValueError,OSError):raise QueueError('customer_runner_capability_or_approval_unavailable') from None
            if Run.objects.filter(target=target,state__in=ACTIVE).count()>=2:raise QueueError('target_queue_full')
            if Run.objects.filter(target=target,created_at__gte=timezone.now().replace(hour=0,minute=0,second=0,microsecond=0)).count()>=runner.daily_limit:raise QueueError('target_daily_quota')
        if original:
            saved=Run.objects.select_for_update().get(pk=original.pk)
            if saved.purged_at or saved.project_id!=project.pk or saved.state!='completed':raise QueueError('original_evidence_unavailable')
        if Run.objects.filter(state__in=ACTIVE).count()>=settings.MAX_QUEUED_JOBS:raise QueueError('global_queue_full')
        if Run.objects.filter(project__organization=project.organization,state__in=ACTIVE).count()>=10:raise QueueError('organization_queue_full')
        if Run.objects.filter(project=project,state__in=ACTIVE).count()>=5:raise QueueError('project_queue_full')
        identifier=uuid.uuid4()
        run=Run.objects.create(id=identifier,project=project,target=target,build=build,**principal_fields(request.user),
            actor_auth_hash=auth_fingerprint(request.user),mfa_at=authorized_at,
            native_run_id='w'+identifier.hex[:18],operation=operation,original=original,profile=profile,suite=suite,fixture_mode=mode,
            idempotency_key=key,intent_sha256=fingerprint)
        audit(request.user,'run.queued',project.organization,run.pk,native_run_id=run.native_run_id,operation=operation)
        return run,True
