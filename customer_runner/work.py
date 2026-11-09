"""Durable one-launch journal. Lost connection permits collection, never a restart."""
import base64,hashlib,os,re,secrets,time,uuid
from pathlib import Path
from . import protocol as wire
from .client import create,protected
from .agent import command,route_fingerprint,storage
from .archive import pack

def validate(configuration,inventory,job):
    wire.fields(job,'run_id native_run_id target_id project_id organization_id inventory_sha256 operation profile suite fixture_mode build intent_sha256 original_native_run_id')
    wire.require(str(uuid.UUID(job['run_id']))==job['run_id'],'job_id_invalid')
    from resmgrcheck.workflow import run_id
    from resmgrcheck.contracts import load,Profile
    from resmgrcheck.deployment import Deployment
    from resmgrcheck.build_identity import source_hash
    from resmgrcheck.registrations import PROFILES
    run_id(job['native_run_id']);wire.hex_value(job['intent_sha256'])
    for name in ['target_id','project_id','organization_id']:wire.require(job[name]==configuration[name],'job_tenant_mismatch')
    wire.require(job['inventory_sha256']==wire.fingerprint(inventory) and inventory['route_sha256']==route_fingerprint(configuration),'job_route_changed')
    wire.require(source_hash(Path(configuration['engine_root']))==inventory['engine_sha256'],'job_engine_source_changed')
    wire.require(job['operation'] in {'run','replay'} and job['profile'] in PROFILES and job['suite'] in {'profile','lifecycle','health'},'job_operation_invalid')
    wire.require(configuration['attachment']!='external-attach' or job['suite']=='health','external_lifecycle_unsupported')
    wire.require(configuration['attachment']!='external-attach' or job['fixture_mode']=='fixed','external_fixture_controls_unsupported')
    mode='corrected' if job['fixture_mode']=='fixed' else job['fixture_mode']
    wire.require(mode in configuration['allowed_modes'],'job_fixture_mode_not_locally_approved')
    selected=Deployment.parse(job['build']);identity=selected.data['deployment_id']
    wire.require(identity in configuration['manifests'] and Deployment.parse(load(configuration['manifests'][identity])).data==selected.data,'job_build_not_locally_approved')
    for a,b in [('uid','uid'),('processor','architecture'),('machine','machine'),('release','release'),('recipe_id','recipe_id')]:
        wire.require(inventory['target_identity'][a]==selected.data[b],'job_build_incompatible')
    profile=Path(configuration['engine_root'])/'profiles'/(job['profile']+('-external' if configuration['attachment']=='external-attach' else '')+'.json')
    Profile.parse(load(profile))
    return profile,configuration['manifests'][identity]

def run_once(client,configuration,state,inventory):
    result=client.exchange({'operation':'poll','inventory':inventory})
    if not result.get('job'):return {'state':result['state'],'job':'none','native_test_executed':False}
    job=result['job'];profile,manifest=validate(configuration,inventory,job);identifier=job['run_id']
    directory=Path(state)/('job-'+identifier);directory.mkdir(mode=0o700,exist_ok=True)
    wire.require(not directory.is_symlink() and directory.stat().st_uid==os.geteuid() and directory.stat().st_mode&0o077==0,'job_journal_ownership_invalid')
    receipt=directory/'intent.json';record={'job':job,'ticket':result['ticket']}
    if not receipt.exists():create(receipt,wire.canonical(record))
    wire.require(wire.parse(protected(receipt,wire.MAX_MESSAGE))==record,'job_intent_changed')
    common={'run_id':identifier,'ticket':result['ticket']}
    if result['job_state'] in {'received','ingesting','completed','quarantined','rejected'}:
        return {'state':result['job_state'],'run_id':identifier,'native_run_id':job['native_run_id']}
    launch=directory/'launch-intent';executed=False
    target=['--target',configuration['alias'],'--config',configuration['target_config']]
    def beat():
        try:client.exchange({'operation':'heartbeat','inventory':inventory})
        except wire.ProtocolError:pass # Network loss never signals/restarts an external service.
    output=directory/'execution'
    upload_record=directory/'upload.json'
    try:
        if upload_record.exists():
            upload=wire.parse(protected(upload_record))
            wire.fields(upload,'file sha256 bytes execution')
            wire.require(re.fullmatch(r'upload-[0-9a-f]{16}\.tar',upload['file']) is not None,'job_cached_upload_invalid')
            archive=directory/upload['file']
            wire.require(not archive.is_symlink() and archive.is_file() and archive.stat().st_nlink==1,'job_cached_upload_invalid')
            with archive.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
            size=archive.stat().st_size
            wire.require(size==upload['bytes'] and checksum==upload['sha256'],'job_cached_upload_changed')
        elif not launch.exists() and result['job_state']=='offered':
            storage(configuration,job['suite'])
            # Durable intent precedes the remote grant. Any uncertainty after this
            # point forces collection of the exact ID, even if launch never happened.
            create(launch,wire.canonical({'native_run_id':job['native_run_id'],'intent_sha256':job['intent_sha256']}))
            permit=client.exchange({'operation':'begin',**common,'intent_sha256':job['intent_sha256']})
            if not permit['launch_allowed']:return {'state':permit['job_state'],'native_run_id':job['native_run_id'],'native_test_executed':False}
            wire.require(permit['run_id']==identifier and permit['native_run_id']==job['native_run_id'] and permit['intent_sha256']==job['intent_sha256']
                and type(permit['grant_expires_at']) is int and time.time()<permit['grant_expires_at']<=time.time()+31,'job_grant_expired_or_mismatched')
            # Recheck local route and build immediately before fixed argv creation.
            validate(configuration,inventory,job)
            args=[*target,'--candidate-manifest',manifest,'--out',str(output),'--run-id',job['native_run_id']]
            if job['operation']=='replay':
                wire.require(job['original_native_run_id'] is not None,'job_original_missing')
                originals=[]
                for previous in Path(state).glob('job-*/intent.json'):
                    saved=wire.parse(protected(previous,wire.MAX_MESSAGE))
                    if saved['job']['native_run_id']==job['original_native_run_id']:
                        uploaded=wire.parse(protected(previous.parent/'upload.json'))
                        location=uploaded['execution']
                        wire.require(location=='execution' or re.fullmatch('collection-[0-9a-f]{16}',location),'job_original_path_invalid')
                        originals.append(previous.parent/location/'replay.json')
                wire.require(len(originals)==1,'job_original_not_locally_available')
                args=['replay',str(originals[0]),*args]
            else:args=['run',*args,'--profile',str(profile),'--suite',job['suite'],'--fixture-mode',job['fixture_mode']]
            command(configuration,args,heartbeat=beat);executed=True
        else:
            # Fresh output retains any earlier partial collection. CLI collect
            # records same-ID histories and cannot invoke the run/replay path.
            output=directory/('collection-'+secrets.token_hex(8))
            command(configuration,['collect',*target,'--run-id',job['native_run_id'],'--out',str(output),'--wait'],heartbeat=beat)
        if not upload_record.exists():
            archive=directory/('upload-'+secrets.token_hex(8)+'.tar');pack(output,archive)
            size=archive.stat().st_size
            with archive.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
            create(upload_record,wire.canonical({'file':archive.name,'sha256':checksum,'bytes':size,'execution':output.name}))
        with archive.open('rb') as stream:
            index=0
            while raw:=stream.read(wire.CHUNK_SIZE):
                ack=directory/('upload-ack-'+str(index).zfill(4))
                checksum_part=hashlib.sha256(raw).hexdigest()
                if ack.exists():
                    wire.require(protected(ack,64).decode('ascii')==checksum_part,'job_upload_journal_changed')
                    index+=1;continue
                answer=client.exchange({'operation':'chunk',**common,'sha256':checksum,'bytes':size,'index':index,'data':base64.b64encode(raw).decode('ascii')})
                wire.require(answer['chunk_stored']==index and answer['sha256']==checksum_part,'job_upload_acknowledgement_invalid')
                create(ack,checksum_part.encode('ascii'));index+=1
        finished=client.exchange({'operation':'finish',**common})
        return {'state':finished['job_state'],'run_id':identifier,'native_run_id':job['native_run_id'],'native_launch_path_executed':executed,'verdict':'withheld_pending_private_validation'}
    except (wire.ProtocolError,OSError,ValueError):
        try:client.exchange({'operation':'uncertain',**common})
        except wire.ProtocolError:pass
        raise wire.ProtocolError('job_connection_or_collection_uncertain_same_id_only') from None
