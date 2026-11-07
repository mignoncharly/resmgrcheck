"""Tenant-bound scheduling, deduplication and immutable engine intent."""
import hashlib,re,uuid
from datetime import datetime,timezone as dt_timezone,timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from allauth.account.internal.flows.login import get_authentication_records
from .models import Run,Target,BuildRelease,ExecutorSlot
from .security import project_access,verified,enrolled,audit,mfa_authenticated
from resmgrcheck.contracts import digest

ACTIVE={'queued','claimed','starting','running','collecting','launch_uncertain'}

class QueueError(Exception):pass


def auth_fingerprint(user):
    return hashlib.sha256((user.password+':'+str(user.session_version)).encode()).hexdigest()


def enqueue(request,project,target,build,*,profile,suite,mode,key,original=None,operation='run'):
    project_access(request.user,project.pk,'developer')
    if not verified(request.user) or not mfa_authenticated(request,900):raise QueueError('recent_verified_mfa_required')
    if target.project_id!=project.pk or not target.approved:raise QueueError('target_not_approved')
    if target.state=='quarantined':raise QueueError('target_quarantined')
    if target.kind=='customer-request' or (target.kind=='external-health' and suite!='health'):raise QueueError('required_capability_unsupported')
    if operation!='inventory' and (not build or build.target_id!=target.pk or not build.approved):raise QueueError('build_not_approved')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}',key):raise QueueError('idempotency_key_invalid')
    if operation not in {'run','replay','inventory'} or profile not in {'sensor','job'} or suite not in {'profile','lifecycle','health'} or mode not in {'fixed','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'}:raise QueueError('execution_selection_invalid')
    if operation=='replay' and (not original or original.project_id!=project.pk or original.state!='completed' or original.purged_at):raise QueueError('original_evidence_unavailable')
    intent={'project':str(project.pk),'target':str(target.pk),'build':str(build.pk) if build else None,'operation':operation,'profile':profile,'suite':suite,'mode':mode,'original':str(original.pk) if original else None}
    fingerprint=digest(intent)
    records=[r['at'] for r in get_authentication_records(request,request.user) if r.get('method')=='mfa']
    if not records or not enrolled(request.user):raise QueueError('mfa_required')
    with transaction.atomic():
        slot,_=ExecutorSlot.objects.get_or_create(name='dispatch')
        ExecutorSlot.objects.select_for_update().get(pk=slot.pk)
        existing=Run.objects.filter(project=project,actor=request.user,idempotency_key=key).first()
        if existing:
            if existing.intent_sha256!=fingerprint:raise QueueError('idempotency_intent_conflict')
            return existing,False
        if Run.objects.filter(state__in=ACTIVE).count()>=settings.MAX_QUEUED_JOBS:raise QueueError('global_queue_full')
        if Run.objects.filter(project__organization=project.organization,state__in=ACTIVE).count()>=10:raise QueueError('organization_queue_full')
        if Run.objects.filter(project=project,state__in=ACTIVE).count()>=5:raise QueueError('project_queue_full')
        identifier=uuid.uuid4()
        run=Run.objects.create(id=identifier,project=project,target=target,build=build,actor=request.user,
            actor_auth_hash=auth_fingerprint(request.user),mfa_at=datetime.fromtimestamp(max(records),dt_timezone.utc),
            native_run_id='w'+identifier.hex[:18],operation=operation,original=original,profile=profile,suite=suite,fixture_mode=mode,
            idempotency_key=key,intent_sha256=fingerprint)
        audit(request.user,'run.queued',project.organization,run.pk,native_run_id=run.native_run_id,operation=operation)
        return run,True
