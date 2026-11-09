"""One private bounded executor; durable lease expiry never authorizes relaunch."""
from datetime import timedelta
import fcntl,hashlib,json,os,uuid
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from .models import Run,Target,ExecutorSlot,Artifact
from .security import project_access,verified,enrolled,audit,is_code,job_principal,permission,start_authority
from .jobs import ACTIVE,auth_fingerprint
from .engine import registry,run_path,fixed_argv,command,storage_available,PolicyError,EngineUncertain
from .storage import seal
from resmgrcheck.contracts import load
from resmgrcheck.workflow import inspect_execution,validate_state

LEASE_SECONDS=30


def reauthorize(run,recovery=False):
    actor=job_principal(run)
    if not recovery:
        if not verified(actor) or (settings.ADMIN_MFA_REQUIRED and not is_code(actor) and not enrolled(actor)) or auth_fingerprint(actor)!=run.actor_auth_hash:raise PolicyError('actor_authorization_revoked')
        try:permission(actor,run.project_id,'run',target=run.target,run=run.original if run.original_id else None)
        except Http404:raise PolicyError('project_authorization_revoked')
    if run.target.project_id!=run.project_id:raise PolicyError('target_tenant_mismatch')
    if not run.target.approved:raise PolicyError('target_not_approved')
    if run.target.kind=='customer-request':raise PolicyError('external_runner_unavailable')
    if run.target.kind=='external-health' and run.suite!='health':raise PolicyError('external_lifecycle_unsupported')
    if run.operation!='inventory' and (not run.build or not run.build.approved or run.build.target_id!=run.target_id):raise PolicyError('build_not_approved')
    if run.original_id and (run.original.project_id!=run.project_id or run.original.purged_at):raise PolicyError('replay_tenant_or_evidence_mismatch')


def claim():
    now=timezone.now()
    with transaction.atomic():
        ExecutorSlot.objects.get_or_create(name='private-qnx')
        slot=ExecutorSlot.objects.select_for_update().get(name='private-qnx')
        if slot.run_id:
            if slot.expires_at and slot.expires_at>now:return None
            candidate=Run.objects.select_for_update().get(pk=slot.run_id)
            if candidate.state not in ACTIVE:return None # quarantine needs explicit resolution
            recovery=True
        else:
            candidate=Run.objects.select_for_update(skip_locked=True).filter(state='queued').exclude(target__kind='customer-runner').order_by('created_at').first()
            if not candidate:return None
            recovery=False
        token=uuid.uuid4();slot.run=candidate;slot.token=token;slot.expires_at=now+timedelta(seconds=LEASE_SECONDS);slot.save()
        candidate.lease_token=token;candidate.lease_expires=slot.expires_at
        if not recovery:candidate.state='claimed'
        candidate.save(update_fields=['lease_token','lease_expires','state'])
        return candidate.pk,token,recovery


def heartbeat(run_id,token):
    now=timezone.now();expiry=now+timedelta(seconds=LEASE_SECONDS)
    with transaction.atomic():
        slot=ExecutorSlot.objects.select_for_update().get(name='private-qnx')
        if slot.run_id!=run_id or slot.token!=token:raise EngineUncertain('executor_lease_lost')
        slot.expires_at=expiry;slot.save(update_fields=['expires_at'])
        Run.objects.filter(pk=run_id,lease_token=token).update(heartbeat_at=now,lease_expires=expiry)


def transition(run,token,state,**fields):
    if not Run.objects.filter(pk=run.pk,lease_token=token).update(state=state,**fields):raise EngineUncertain('executor_lease_lost')
    run.state=state


def release(run,token):
    with transaction.atomic():
        slot=ExecutorSlot.objects.select_for_update().get(name='private-qnx')
        if slot.run_id==run.pk and slot.token==token:
            slot.run=None;slot.token=None;slot.expires_at=None;slot.save()
        Run.objects.filter(pk=run.pk,lease_token=token).update(lease_expires=None)


def finish(run,token,summary,cleanup,no_launch=False):
    state='completed' if cleanup or no_launch else 'blocked'
    transition(run,token,state,summary=summary,target_cleanup_verified=cleanup,finished_at=timezone.now(),error_code='prelaunch_infrastructure_error' if no_launch else '' if cleanup else 'cleanup_or_coverage_unestablished',progress='Transfer/preflight failed before a native launch; required cases NOT_RUN.' if no_launch else 'Evidence collected; original deterministic outcomes preserved.')
    if cleanup or no_launch:
        Target.objects.filter(pk=run.target_id).update(state='available' if cleanup else 'unavailable',quarantine_reason='')
        release(run,token)
    else:Target.objects.filter(pk=run.target_id).update(state='quarantined',quarantine_reason='cleanup_or_coverage_unestablished')
    audit(job_principal(run),'run.collected',run.project.organization,run.pk,cleanup_verified=cleanup,execution_exit=summary['execution_exit'])


def execute_claim(identifier,token,recovery):
    run=Run.objects.select_related('actor','access_session__code__organization','project__organization','target__project','build','original__project').get(pk=identifier)
    settings.PRIVATE_ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock_root=settings.PRIVATE_ROOT/'locks';lock_root.mkdir(exist_ok=True,mode=0o700)
    descriptor=os.open(lock_root/(str(run.pk)+'.lock'),os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
    started=recovery and run.operation!='inventory'
    try:
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            # A paused old local worker still owns this artifact operation. Do not race it.
            transition(run,token,'launch_uncertain',error_code='previous_local_executor_still_owns_lock');return
        # Service-owned recovery may collect its existing run after user revocation.
        # It cannot launch, and all target/tenant/build approvals are still checked.
        reauthorize(run,recovery=recovery);binding=registry(run.target,run.build)
        output=run_path(run);output.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
        beat=lambda:heartbeat(run.pk,token)
        if recovery and run.operation=='inventory':
            transition(run,token,'rejected',error_code='inventory_interrupted',finished_at=timezone.now(),progress='Read-only inventory interrupted; no native test was launched.')
            release(run,token);return
        if recovery:
            # Durable launch intent exists: status and collect only. Never run/replay again.
            transition(run,token,'collecting',progress='Recovering exact existing native run; no relaunch.')
            argv=[settings.ENGINE_PYTHON,'-m','resmgrcheck','collect','--target',binding.alias,'--config',str(binding.config),'--run-id',run.native_run_id,'--out',str(output),'--wait']
            code,raw,facts=command(argv,binding,beat,timeout=settings.ENGINE_EXECUTION_TIMEOUT)
            summary,cleanup=seal(run);Run.objects.filter(pk=run.pk).update(process_facts=facts);finish(run,token,summary,cleanup);return
        if run.target.state=='quarantined':raise PolicyError('target_quarantined')
        if run.cancel_requested:
            transition(run,token,'cancelled',error_code='cancelled_before_launch',finished_at=timezone.now(),progress='Cancelled before native launch; NOT_RUN.');release(run,token);return
        if run.created_at<timezone.now()-timedelta(minutes=15) or run.mfa_at<timezone.now()-timedelta(minutes=15):raise PolicyError('queued_authorization_expired')
        free=storage_available(binding,120 if run.suite=='lifecycle' else 32,start_guard=start_authority(run))
        if run.operation=='inventory':output.mkdir(exist_ok=False,mode=0o750)
        argv=fixed_argv(run,binding,output)
        transition(run,token,'starting',started_at=timezone.now(),progress='Launch intent persisted; awaiting native evidence.')
        started=True # Persisted before child creation: a crash now remains uncertain.
        code,raw,facts=command(argv,binding,beat,timeout=settings.ENGINE_EXECUTION_TIMEOUT,start_guard=start_authority(run),
            on_started=lambda pid:transition(run,token,'running',progress='Private CLI executing; native verdict is not yet established.'))
        Run.objects.filter(pk=run.pk).update(process_facts=facts)
        if run.operation=='inventory':
            info=load(output/'inventory.json')
            # Preserve whole doctor classification; distinguish runtime target checks from SDK readiness.
            runtime={row['id']:row['state'] for row in info['checks']}
            ready=all(runtime.get(name)=='PASS' for name in ['target_reachable','target_compatibility','ssh_command_path','transfer','target_capabilities'])
            caps=next((r['detail']['compiled_adapter_capabilities'] for r in info['checks'] if r['id']=='target_capabilities' and isinstance(r['detail'],dict)),{})
            Target.objects.filter(pk=run.target_id).update(state='available' if ready else 'unavailable',inventory={'doctor_exit':code,'checks':runtime,'compiled_adapters':caps,'service_instance':'unknown'},last_seen=timezone.now())
            transition(run,token,'completed',summary={'doctor_exit':code,'runtime_target_ready':ready,'checks':runtime,'cleanup_scope':'not_applicable_inventory'},target_cleanup_verified=False,finished_at=timezone.now(),progress='Inventory complete; private instance capabilities remain unknown.')
            release(run,token);return
        transition(run,token,'collecting',progress='Validating original engine bundles and collection state.')
        request,summary,_=inspect_execution(output)
        state=validate_state(load(output/'state.json'),request)
        no_launch=(code in {2,130} and all(value=='not-requested' for value in state['cases'].values())
                   and all(row['verdict']=='NOT_RUN' for row in summary['cases']))
        uncollected=any(not row['bundle_id'] for row in summary['cases'])
        if uncollected and not no_launch:
            incidents=list(run.incidents);incidents.append({'code':'transport_or_engine_error','cli_exit':code,'service_conclusion':'withheld_pending_collection'})
            transition(run,token,'launch_uncertain',summary=summary,incidents=incidents,error_code='native_evidence_incomplete',progress='Partial evidence preserved; collect this same native ID after lease expiry. No relaunch.')
            Target.objects.filter(pk=run.target_id).update(state='quarantined',quarantine_reason='native_evidence_incomplete')
            return
        summary,cleanup=seal(run)
        if code in {2,130}:
            incidents=list(run.incidents);incidents.append({'code':'transport_or_engine_error','cli_exit':code})
            Run.objects.filter(pk=run.pk).update(incidents=incidents)
        if no_launch:
            facts={**facts,'no_native_launch_observed':True,'basis':'normal CLI exit and bound finalized state before any native launch intent'}
            Run.objects.filter(pk=run.pk).update(process_facts=facts)
        finish(run,token,summary,cleanup,no_launch=no_launch)
    except (PolicyError,Http404) as error:
        code=str(error) if isinstance(error,PolicyError) else 'authorization_denied'
        if code=='authorization_revoked_before_child':
            started=False
            Run.objects.filter(pk=run.pk,lease_token=token).update(process_facts={'local_child_not_created':True,'native_launch_not_attempted':True})
        transition(run,token,'blocked' if started else 'rejected',error_code=code,finished_at=timezone.now(),progress='Execution withheld; no passing conclusion.')
        if started:Target.objects.filter(pk=run.target_id).update(state='quarantined',quarantine_reason=code)
        else:release(run,token)
        audit(job_principal(run),'run.rejected',run.project.organization,run.pk,reason=code)
    except Exception as error:
        if not Run.objects.filter(pk=run.pk,lease_token=token).exists():
            audit(None,'executor.stale_lease_released',run.project.organization,run.pk)
            return # A superseded worker cannot overwrite its successor's state.
        if run.operation=='inventory':
            transition(run,token,'rejected',error_code='inventory_error',finished_at=timezone.now(),progress='Read-only inventory unavailable; no native test was launched.')
            Target.objects.filter(pk=run.target_id).update(state='unavailable')
            release(run,token);return
        # Never expose exception/provider/SSH text in browser or logs.
        incidents=list(Run.objects.get(pk=run.pk).incidents);incidents.append({'code':'launch_or_collection_uncertain','error_class':type(error).__name__})
        transition(run,token,'launch_uncertain',incidents=incidents,error_code='launch_or_collection_uncertain',progress='Native launch/cleanup is uncertain; recovery will collect this same run ID.')
        Target.objects.filter(pk=run.target_id).update(state='quarantined',quarantine_reason='launch_or_collection_uncertain')
        audit(job_principal(run),'run.uncertain',run.project.organization,run.pk,error_class=type(error).__name__)
    finally:os.close(descriptor)
