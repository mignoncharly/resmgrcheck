"""Private executor evidence ingestion; HTTP has no filesystem write authority here."""
from datetime import timedelta
import fcntl,hashlib,os,secrets,stat,uuid,shutil
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from customer_runner import protocol as wire
from customer_runner.archive import unpack,publish
from resmgrcheck.contracts import Profile,load,digest
from resmgrcheck.workflow import inspect_execution,suite_profiles,validate_state
from .models import RunnerJob,RunnerChunk,Run,Target
from .engine import run_path,PolicyError
from .storage import seal,verify_inventory
from .security import audit

def validate(path,job):
    request,summary,_=inspect_execution(path);run=job.run
    validate_state(load(path/'state.json'),request)
    wire.require(request.data['run_id']==run.native_run_id and request.data['deployment']==run.build.manifest==job.intent['build'] and
        request.data['target_identity']==job.runner.inventory['target_identity'],'runner_evidence_identity_mismatch')
    mode='corrected' if run.fixture_mode=='fixed' else run.fixture_mode
    wire.require(request.data['mode']==mode,'runner_evidence_mode_mismatch')
    external=job.runner.inventory['attachment']=='external-attach'
    profile=Profile.parse(load(settings.REPO_ROOT/'profiles'/(run.profile+('-external' if external else '')+'.json')))
    expected=suite_profiles(profile,run.suite)
    wire.require([p.data for p in expected]==[case['profile'] for case in request.data['cases']],'runner_evidence_contract_changed')
    if run.operation=='replay':
        original,_,_=inspect_execution(run_path(run.original))
        wire.require(request.data['origin'] and request.data['origin']['request_sha256']==digest(original.data) and
            not request.data['origin']['mode_changed'],'runner_replay_identity_mismatch')
    else:wire.require(request.data['origin'] is None and request.data['suite']==run.suite,'runner_evidence_operation_mismatch')
    return summary

def claim():
    now=timezone.now()
    with transaction.atomic():
        job=(RunnerJob.objects.select_for_update(skip_locked=True)
            .filter(Q(state='received')|Q(state='ingesting',ingest_lease__lt=now)).order_by('offered_at').first())
        if not job:return None
        job.state='ingesting';job.ingest_token=uuid.uuid4();job.ingest_lease=now+timedelta(minutes=5)
        job.save(update_fields=['state','ingest_token','ingest_lease']);return job.pk,job.ingest_token

def execute(identifier,token):
    if settings.ENVIRONMENT=='production' and settings.SERVICE_ROLE!='executor':raise PolicyError('private_executor_role_required')
    job=RunnerJob.objects.select_related('run__project__organization','run__target','run__build','run__original','runner').get(pk=identifier,ingest_token=token)
    private=settings.PRIVATE_ROOT;private.mkdir(parents=True,exist_ok=True,mode=0o700)
    locks=private/'locks';locks.mkdir(exist_ok=True,mode=0o700)
    fd=os.open(locks/(str(identifier)+'.runner.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd);wire.require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1,'runner_ingest_lock_invalid')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        wire.require(shutil.disk_usage(private).free>=1024**3+4*job.archive_bytes,'runner_ingest_disk_reserve')
        wire.require(len(list(private.glob('runner-stage-'+str(identifier)+'-*')))<3,'runner_ingest_attempt_limit')
        # Private stages are retained on interruption/failure; never delete/adopt
        # unknown files. A retry assembles a fresh stage from authenticated chunks.
        stage=private/('runner-stage-'+str(identifier)+'-'+secrets.token_hex(8));stage.mkdir(mode=0o700)
        archive=stage/'evidence.tar';digest=hashlib.sha256();total=0;index=0
        descriptor=os.open(archive,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'wb') as out:
            for part in RunnerChunk.objects.filter(job=job).order_by('index').iterator(chunk_size=1):
                raw=bytes(part.data);wire.require(part.index==index and hashlib.sha256(raw).hexdigest()==part.sha256,'runner_ingest_chunk_changed')
                digest.update(raw);out.write(raw);total+=len(raw);index+=1
                wire.require(total<=wire.MAX_ARCHIVE,'runner_evidence_bound')
            out.flush();os.fsync(out.fileno())
        wire.require(total==job.archive_bytes and digest.hexdigest()==job.archive_sha256,'runner_ingest_archive_changed')
        tree=stage/'verified';unpack(archive,tree);validate(tree,job)
        output=run_path(job.run);output.parent.mkdir(parents=True,exist_ok=True,mode=0o750)
        # State/receipt is private executor custody, outside HTTP-writable paths.
        receipt=private/('runner-publication-'+str(identifier)+'.json')
        record={'run_id':str(identifier),'native_run_id':job.run.native_run_id,'archive_sha256':job.archive_sha256,'intent_sha256':job.run.intent_sha256}
        from customer_runner.client import create,protected
        existing_receipt=receipt.exists()
        if output.exists() or output.is_symlink():wire.require(existing_receipt,'runner_evidence_destination_occupied')
        if not existing_receipt:create(receipt,wire.canonical(record))
        wire.require(wire.parse(protected(receipt))==record,'runner_ingest_receipt_changed')
        if output.exists() or output.is_symlink():
            wire.require(output.is_dir() and not output.is_symlink(),'runner_evidence_destination_occupied')
            expected_files={member.relative_to(tree).as_posix() for member in tree.rglob('*') if member.is_file()}
            generated={'report.html','web-evidence-v2.json','comparison.json','comparison-view/report.html','comparison-view/comparison.json'}
            wire.require(all(not member.is_symlink() and (not member.is_file() or member.relative_to(output).as_posix() in expected_files|generated)
                for member in output.rglob('*')),'runner_evidence_destination_occupied')
            # A completed exact publication can be retried; every received member
            # must still match. Unknown/partial releases are never overwritten.
            for member in tree.rglob('*'):
                if member.is_file():
                    existing=output/member.relative_to(tree)
                    wire.require(not any(p.is_symlink() for p in [existing,*existing.parents]) and existing.is_file() and
                        existing.stat().st_nlink==1 and hashlib.sha256(existing.read_bytes()).digest()==hashlib.sha256(member.read_bytes()).digest(),'runner_evidence_destination_occupied')
            validate(output,job)
        else:publish(tree,output)
        # Serialize stale-lease protection with sealed graph/result publication.
        with transaction.atomic():
            current=RunnerJob.objects.select_for_update().get(pk=identifier)
            wire.require(current.ingest_token==token,'runner_ingest_lease_lost')
            summary,cleanup=seal(job.run);verify_inventory(job.run)
            current.state='completed' if cleanup else 'quarantined';current.ingest_lease=None;current.save(update_fields=['state','ingest_lease'])
            Run.objects.filter(pk=identifier).update(state='completed' if cleanup else 'blocked',summary=summary,
                target_cleanup_verified=cleanup,finished_at=timezone.now(),error_code='' if cleanup else 'customer_native_cleanup_unproven',
                process_facts={'execution_plane':'customer-owned outbound runner','runner_public_key_sha256':wire.fingerprint(job.runner.public_key),'archive_sha256':job.archive_sha256},
                progress='Customer-native evidence validated by the original evaluator; outcomes preserved.')
            if cleanup:
                Target.objects.filter(pk=job.runner_id,approved=True,customerrunner__revoked_at__isnull=True,
                    customerrunner__quarantined=False,quarantine_reason__in=['','customer_collection_uncertain','customer_native_cleanup_unproven']).update(state='connected',quarantine_reason='')
            else:Target.objects.filter(pk=job.runner_id).update(state='quarantined',quarantine_reason='customer_native_cleanup_unproven')
            audit(None,'runner.evidence_collected',job.run.project.organization,identifier,cleanup_verified=cleanup,archive_sha256=job.archive_sha256)
            if cleanup:RunnerChunk.objects.filter(job=job).delete()
        # Only this invocation's freshly created verified stage, after successful
        # durable publication. Failed/interrupted attempts remain for review.
        try:shutil.rmtree(stage)
        except OSError:audit(None,'runner.stage_cleanup_pending',job.run.project.organization,identifier)
        return True
    except Exception as error:
        # Never publish remote exception text, row values, credentials or paths.
        if RunnerJob.objects.filter(pk=identifier,ingest_token=token).update(state='quarantined',ingest_lease=None):
            Run.objects.filter(pk=identifier).update(state='blocked',error_code='customer_evidence_invalid_or_uncertain',target_cleanup_verified=False)
            Target.objects.filter(pk=job.runner_id).update(state='quarantined',quarantine_reason='customer_evidence_invalid_or_uncertain')
            audit(None,'runner.ingest_withheld',job.run.project.organization,identifier,error_class=type(error).__name__)
        return False
    finally:os.close(fd)

def ingest_one():
    job=claim()
    if job:execute(*job)
    return bool(job)
