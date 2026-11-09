"""Authenticated target-scoped work. Grant launch once; reconnect never reissues it."""
import base64,binascii,hashlib,math,uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from customer_runner import protocol as wire
from resmgrcheck.contracts import Profile,load,digest
from resmgrcheck.deployment import Deployment
from resmgrcheck.workflow import suite_profiles
from .models import CustomerRunner,Target,Run,RunnerJob,RunnerChunk,ExecutorSlot
from .runners import status,heartbeat
from .security import audit,start_authority,job_principal
from .engine import PolicyError
from .worker import reauthorize
from .jobs import ACTIVE

def capable(target,build,profile,suite,mode):
    wire.require(settings.RUNNER_ENABLED,'runner_unavailable')
    runner=CustomerRunner.objects.select_related('target').get(pk=target.pk)
    wire.require(status(runner)=='connected','runner_not_connected_or_approved')
    wire.require(runner.inventory['attachment']!='external-attach' or suite=='health','external_lifecycle_unsupported')
    selected=Deployment.parse(build.manifest)
    identity=runner.inventory['target_identity']
    for a,b in [('uid','uid'),('processor','architecture'),('machine','machine'),('release','release'),('recipe_id','recipe_id')]:
        wire.require(identity[a]==selected.data[b],'runner_build_target_mismatch')
    path=settings.REPO_ROOT/'profiles'/(profile+('-external' if runner.inventory['attachment']=='external-attach' else '')+'.json')
    expected=Profile.parse(load(path));profiles=suite_profiles(expected,suite)
    wire.require(expected.data['adapter']['id'] in selected.data['candidates'],'build_adapter_unsupported')
    wire.require(('corrected' if mode=='fixed' else mode) in expected.registration.fixture_modes,'fixture_control_unsupported')
    required=set().union(*(set(p.data['capabilities']['required']) for p in profiles))
    caps=runner.inventory['compiled_adapters'].get(expected.data['adapter']['id'],[])
    wire.require(required<=set(caps),'required_capability_unsupported')
    wire.require(build.approved and build.target_id==target.pk,'build_not_approved')
    wire.require(mode in {'fixed','ignore-unblock','retain-waiter','retain-third','duplicate-terminal','drop-job'},'fixture_mode_invalid')
    wire.require(('corrected' if mode=='fixed' else mode) in runner.inventory['allowed_modes'],'runner_mode_not_customer_approved')
    return runner

def payload(run,runner):
    return {'run_id':str(run.pk),'native_run_id':run.native_run_id,'target_id':str(run.target_id),
        'project_id':str(run.project_id),'organization_id':str(run.project.organization_id),
        'inventory_sha256':runner.inventory_sha256,'operation':run.operation,'profile':run.profile,
        'suite':run.suite,'fixture_mode':run.fixture_mode,'build':run.build.manifest,
        'intent_sha256':run.intent_sha256,'original_native_run_id':run.original.native_run_id if run.original_id else None}

def fresh_authority(run):
    cutoff=timezone.now()-timedelta(minutes=15)
    wire.require(run.created_at>cutoff and run.mfa_at>cutoff,'runner_queued_authorization_expired')

def poll(device,body):
    wire.fields(body,'operation inventory')
    result=heartbeat(device,{'operation':'heartbeat','inventory':body['inventory']})
    with transaction.atomic():
        target=Target.objects.select_for_update().get(pk=device.pk)
        runner=CustomerRunner.objects.select_for_update().select_related('target__project').get(pk=device.pk)
        previous=RunnerJob.objects.select_for_update().filter(runner=runner,state__in=['offered','launch-authorized','receiving','received','ingesting','quarantined']).first()
        if previous:
            result.update(job=previous.intent,ticket=str(previous.ticket),job_state=previous.state,
                cancel_requested=previous.run.cancel_requested,launch_allowed=False)
            return result
        if status(runner)!='connected':return result
        run=Run.objects.select_for_update(of=('self',)).select_related('target','project__organization','build','original','actor','access_session__code__organization').filter(target=target,state='queued').order_by('created_at').first()
        if not run:return result
        try:
            reauthorize(run)
            fresh_authority(run)
            wire.require(not run.cancel_requested,'run_cancelled_before_grant')
            capable(target,run.build,run.profile,run.suite,run.fixture_mode)
        except (PolicyError,wire.ProtocolError):
            Run.objects.filter(pk=run.pk).update(state='rejected',error_code='runner_authorization_withheld',finished_at=timezone.now())
            return result
        job=RunnerJob.objects.create(run=run,runner=runner,intent=payload(run,runner))
        Run.objects.filter(pk=run.pk).update(state='claimed',progress='Assigned to exact customer runner; launch not yet authorized.')
        result.update(job=job.intent,ticket=str(job.ticket),job_state=job.state,launch_allowed=False,cancel_requested=False)
        return result

def locked_job(device,body):
    try:identifier=uuid.UUID(body['run_id']);ticket=uuid.UUID(body['ticket'])
    except (TypeError,ValueError,KeyError,AttributeError):raise wire.ProtocolError('runner_job_invalid') from None
    job=RunnerJob.objects.select_for_update(of=('self',)).select_related('run__project__organization','run__target','run__build','run__actor','run__access_session__code__organization','run__original','runner__target').filter(pk=identifier,runner=device,ticket=ticket).first()
    wire.require(job is not None and not job.runner.revoked_at,'runner_job_unavailable')
    return job

def begin(device,body):
    wire.fields(body,'operation run_id ticket intent_sha256')
    with transaction.atomic():
        Target.objects.select_for_update().get(pk=device.pk)
        CustomerRunner.objects.select_for_update().get(pk=device.pk)
        job=locked_job(device,body);run=job.run
        wire.require(body['intent_sha256']==run.intent_sha256,'runner_intent_mismatch')
        if job.state!='offered':return {'launch_allowed':False,'job_state':job.state,'recover_native_run_id':run.native_run_id}
        try:
            with start_authority(run):
                reauthorize(run);fresh_authority(run);capable(run.target,run.build,run.profile,run.suite,run.fixture_mode)
                wire.require(not run.cancel_requested and job.offered_at>timezone.now()-timedelta(seconds=120),'runner_offer_expired_or_cancelled')
                job.state='launch-authorized';job.launch_granted_at=timezone.now();job.save(update_fields=['state','launch_granted_at'])
                Run.objects.filter(pk=run.pk).update(state='starting',started_at=timezone.now(),heartbeat_at=timezone.now(),progress='Single launch grant persisted; interruption requires exact-ID collection, never relaunch.')
                audit(job_principal(run),'runner.launch_granted',run.project.organization,run.pk,native_run_id=run.native_run_id)
        except (PolicyError,wire.ProtocolError):
            job.state='rejected';job.save(update_fields=['state'])
            Run.objects.filter(pk=run.pk).update(state='rejected',finished_at=timezone.now(),error_code='runner_authorization_withheld',process_facts={'remote_launch_grant_issued':False})
            return {'launch_allowed':False,'job_state':'rejected'}
        return {'launch_allowed':True,'run_id':str(run.pk),'native_run_id':run.native_run_id,
            'intent_sha256':run.intent_sha256,'grant_expires_at':int(timezone.now().timestamp())+30}

def chunk(device,body):
    wire.fields(body,'operation run_id ticket sha256 bytes index data')
    wire.hex_value(body['sha256'])
    wire.require(type(body['bytes']) is int and 0<body['bytes']<=wire.MAX_ARCHIVE,'runner_upload_bound')
    count=math.ceil(body['bytes']/wire.CHUNK_SIZE);index=body['index']
    wire.require(type(index) is int and 0<=index<count and type(body['data']) is str and len(body['data'])<=175000,'runner_upload_chunk_invalid')
    try:raw=base64.b64decode(body['data'],validate=True)
    except (ValueError,binascii.Error):raise wire.ProtocolError('runner_upload_encoding_invalid') from None
    wire.require(len(raw)==min(wire.CHUNK_SIZE,body['bytes']-index*wire.CHUNK_SIZE),'runner_upload_chunk_bound')
    with transaction.atomic():
        # One global reservation fence bounds outstanding raw upload storage.
        ExecutorSlot.objects.get_or_create(name='runner-upload')
        ExecutorSlot.objects.select_for_update().get(name='runner-upload')
        job=locked_job(device,body)
        wire.require(job.state in {'launch-authorized','receiving'},'runner_upload_state_invalid')
        if not job.archive_sha256:
            reserved=RunnerJob.objects.exclude(state__in=['completed','rejected']).aggregate(total=Sum('archive_bytes'))['total'] or 0
            wire.require(reserved+body['bytes']<=256*1024**2,'runner_upload_capacity')
            job.archive_sha256=body['sha256'];job.archive_bytes=body['bytes'];job.state='receiving'
            job.save(update_fields=['archive_sha256','archive_bytes','state'])
        wire.require(job.archive_sha256==body['sha256'] and job.archive_bytes==body['bytes'],'runner_upload_identity_changed')
        checksum=hashlib.sha256(raw).hexdigest()
        part,created=RunnerChunk.objects.get_or_create(job=job,index=index,defaults={'data':raw,'sha256':checksum})
        wire.require(created or (part.sha256==checksum and bytes(part.data)==raw),'runner_upload_chunk_changed')
        Run.objects.filter(pk=job.pk).update(state='collecting',heartbeat_at=timezone.now(),progress='Receiving customer-native evidence; verdict withheld until private validation.')
        return {'chunk_stored':index,'sha256':checksum}

def finish(device,body):
    wire.fields(body,'operation run_id ticket')
    with transaction.atomic():
        job=locked_job(device,body)
        if job.state in {'received','ingesting','completed','quarantined'}:return {'job_state':job.state,'native_run_id':job.run.native_run_id}
        wire.require(job.state=='receiving','runner_upload_state_invalid')
        expected=math.ceil(job.archive_bytes/wire.CHUNK_SIZE);digest=hashlib.sha256();total=0;count=0
        for part in RunnerChunk.objects.filter(job=job).order_by('index').iterator(chunk_size=1):
            wire.require(part.index==count,'runner_upload_incomplete');raw=bytes(part.data)
            wire.require(hashlib.sha256(raw).hexdigest()==part.sha256,'runner_upload_integrity_failed')
            digest.update(raw);total+=len(raw);count+=1
        wire.require(count==expected and total==job.archive_bytes and digest.hexdigest()==job.archive_sha256,'runner_upload_incomplete')
        job.state='received';job.save(update_fields=['state'])
        return {'job_state':'received','native_run_id':job.run.native_run_id}

def uncertain(device,body):
    wire.fields(body,'operation run_id ticket')
    with transaction.atomic():
        job=locked_job(device,body)
        if job.state not in {'completed','received','ingesting'}:
            Run.objects.filter(pk=job.pk).update(state='launch_uncertain',error_code='customer_collection_uncertain',progress='Customer connection/native evidence uncertain; preserve exact ID. No relaunch or cleanup claim.')
            Target.objects.filter(pk=device.pk).update(state='quarantined',quarantine_reason='customer_collection_uncertain')
        return {'job_state':job.state,'recover_native_run_id':job.run.native_run_id,'cleanup_verified':False}

def exchange(device,body):
    wire.require(type(body) is dict,'runner_operation_invalid')
    handlers={'poll':poll,'begin':begin,'chunk':chunk,'finish':finish,'uncertain':uncertain}
    wire.require(body.get('operation') in handlers,'runner_operation_invalid')
    return handlers[body['operation']](device,body)
