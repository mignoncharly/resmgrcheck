#!/usr/bin/env python3
"""Recover one sealed W032 ERROR into separate evidence under the actual executor.

Never overwrites the original sealed graph or launches a native case. The read-only
plan needs no root; --apply validates the exact blocked attempt before any change.
"""
import argparse,fcntl,json,os,pwd,re,stat,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import executor_plan as plan

FAILED='45bde2e4a51dea4830589bab7466700512ee615f'
RUN='274989f6-c306-4581-8f69-3db1ca21997d'
NATIVE='w274989f6c30645818f'
ATTEMPT='beb038e6bb43435888c62e95a95efdb8'
STEP='source_validation'
STATE_ROOT=Path('/var/lib/resmgrcheck/engine-state')
PRIVATE=Path('/var/lib/resmgrcheck/private/executor')
ORIGINAL_HASHES={'request.json':'4fd73f5e50d291da338fd5c57ecdd493484bb5ca0f7d38bb89619e64f526e12d',
    'result.json':'1d1172f966c68dc6b5ceed4829fa4ad2529b8ed3e3d084452b41a244e9486b5a',
    'web-evidence-v2.json':'05c23a19b14432bb3a84bdf8fb8bc644c898065666a7638f806869256df7cb17',
    'cases/timeout/partial-events.jsonl':'4aa399127a4fced78dc0531ce4c2bd2d8579a215666dc21c81e9977715be4b2d'}

def selected_path():return STATE_ROOT/'lab/deployment.json'
def recovery_path(driver):return PRIVATE/('recovered-'+RUN+'-'+driver)
def receipt_path(driver):return PRIVATE/('recovered-'+driver+'.json')

def exact_run(*,released=False):
    from control.models import Run,ExecutorSlot,AuditEvent,AccessCode,AccessSession
    from control.jobs import ACTIVE
    import uuid
    run=Run.objects.select_related('project__organization','target','build','access_session__code__created_by').get(pk=RUN)
    account=run.access_session.code.created_by
    plan.require(str(run.project_id)==plan.IDS['project'] and str(run.target_id)==plan.IDS['target'] and
        str(run.build_id)==plan.IDS['before'] and run.native_run_id==NATIVE and run.operation=='run' and
        run.original_id is None and run.project.active and run.project.organization.active and
        run.target.project_id==run.project_id and run.target.approved and run.target.binding==str(run.target_id) and
        run.build.target_id==run.target_id and run.build.approved and run.build.binding==str(run.build_id) and
        run.profile=='sensor' and run.suite=='profile' and run.fixture_mode=='ignore-unblock' and
        run.state=='blocked' and run.error_code=='cleanup_or_coverage_unestablished' and not run.target_cleanup_verified and
        run.process_facts.get('local_child_exit_observed') is True and run.process_facts.get('local_child_returncode')==2 and
        [r.get('verdict') for r in run.summary.get('cases',[])]==['ERROR'],'exact_blocked_ERROR_required')
    plan.require(not account.is_active and account.username=='accept-'+ATTEMPT[:18] and
        AuditEvent.objects.filter(actor=account,action='https.acceptance.created',details__acceptance_id=str(uuid.UUID(ATTEMPT))).exists() and
        AuditEvent.objects.filter(actor=account,action='https.acceptance.closed',details__acceptance_id=str(uuid.UUID(ATTEMPT))).exists() and
        not AccessCode.objects.filter(created_by=account,revoked_at=None).exists() and
        not AccessSession.objects.filter(code__created_by=account,revoked_at=None).exists(),'original_authority_not_closed')
    plan.require(not Run.objects.filter(state__in=ACTIVE).exists(),'other_native_work_requires_review')
    slot=ExecutorSlot.objects.get(name='private-qnx')
    if released:
        plan.require(slot.run_id is None and slot.token is None and slot.expires_at is None and run.lease_expires is None and
            run.target.state=='available' and not run.target.quarantine_reason and
            AuditEvent.objects.filter(action='production.native_collection.recovered',object_id=RUN).exists(),'released_recovery_state_differs')
    else:
        plan.require(str(slot.run_id)==RUN and slot.token==run.lease_token and slot.expires_at is not None and
            run.target.state=='quarantined' and run.target.quarantine_reason=='cleanup_or_coverage_unestablished','blocked_lease_binding_differs')
    return run

def original_inventory(run):
    from control.engine import run_path
    from control.storage import verify_inventory
    uid=pwd.getpwnam('resmgr-exec').pw_uid;root=run_path(run)
    inventory=verify_inventory(run)
    for name,expected in ORIGINAL_HASHES.items():
        plan.require(plan.digest(plan.read_owned(root/name,uid,{0o640},2*1024**2))==expected,'sealed_original_differs')
    return inventory

def install_selection(manifest):
    """Exact approved controller selection; never bootstrap/upload a native binary."""
    from resmgrcheck.contracts import canonical,loads
    from resmgrcheck.deployment import Deployment
    manifest=Deployment.parse(manifest).data
    uid=os.geteuid();path=selected_path()
    for directory in [STATE_ROOT,path.parent]:
        if not directory.exists():directory.mkdir(mode=0o700)
        info=directory.lstat()
        plan.require(not directory.is_symlink() and info.st_uid==uid and stat.S_ISDIR(info.st_mode) and
            not stat.S_IMODE(info.st_mode)&0o077,'selection_directory_protection')
    if path.exists() or path.is_symlink():
        plan.require(loads(plan.read_owned(path,uid,{0o600}))==manifest,'selected_controller_differs')
        return False
    raw=canonical(manifest)+b'\n'
    temporary=path.parent/('.select-'+uuid.uuid4().hex)
    fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    from customer_runner.archive import publish
    publish(temporary,path)
    return True

def verify_recollection(run,path):
    from control.engine import run_path
    from resmgrcheck.workflow import inspect_execution
    from resmgrcheck.artifacts import inspect_bundle
    from resmgrcheck.contracts import RunStatus,load,canonical
    from resmgrcheck.deployment import native_builds
    original=run_path(run);request,summary,_=inspect_execution(path)
    plan.require(canonical(request.data)==canonical(load(original/'request.json')) and request.data['run_id']==NATIVE and
        len(summary['cases'])==1 and summary['cases'][0]['case_id']=='timeout' and summary['cases'][0]['bundle_id'], 'recovered_request_or_coverage_differs')
    bundle=inspect_bundle(path/'cases/timeout/bundle')
    old=RunStatus.parse(load(original/'cases/timeout/status.json')).data
    partial=plan.read_owned(original/'cases/timeout/partial-events.jsonl',pwd.getpwnam('resmgr-exec').pw_uid,{0o640},2*1024**2)
    plan.require(bundle.plan.data==request.data['cases'][0] and bundle.plan.data['run_id']==NATIVE+'-timeout' and
        bundle.status['supervisor_pid']==old['supervisor_pid'] and bundle.raw.startswith(partial),'same_ID_supervisor_or_partial_differs')
    plan.require(bundle.result.data['verdict']=='FAIL' and bundle.status['cleanup_ok'] and not bundle.status['unresolved'] and
        {'cancellation_not_completed','pending_state_not_released'}<=set(bundle.result.data['reasons']) and
        bundle.plan.data['builds']==native_builds(run.build.manifest,'sensor-v1'),'recovered_native_verdict_or_cleanup_unproven')
    return {'native_run_id':NATIVE,'canonical_verdict':'FAIL','cleanup_verified':True,'same_supervisor':True,
        'partial_evidence_prefix_preserved':True,'bundle_id':bundle.manifest.data['bundle_id'],
        'original_ERROR_retained':True,'original_run_state':'blocked'}

def reserve_recollection(path,request):
    """Publish complete recovery input atomically; retain interrupted temporaries."""
    from resmgrcheck.workflow import initialize,validate_state
    from resmgrcheck.contracts import canonical,load
    if not path.exists() and not path.is_symlink():
        temporary=path.parent/('.recover-init-'+uuid.uuid4().hex)
        initialize(temporary,request)
        from customer_runner.archive import publish
        publish(temporary,path)
    info=path.lstat()
    plan.require(not path.is_symlink() and stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid() and
        not info.st_mode&0o077,'recovery_directory_protection')
    members=list(path.rglob('*'));plan.require(len(members)<=256,'recovery_resource_bound')
    for member in members:
        entry=member.lstat()
        plan.require(not stat.S_ISLNK(entry.st_mode) and entry.st_uid==os.geteuid() and
            (stat.S_ISDIR(entry.st_mode) or stat.S_ISREG(entry.st_mode) and entry.st_nlink==1 and not entry.st_mode&0o111 and entry.st_size<=32*1024**2),
            'recovery_resource_type_or_owner')
    plan.require(canonical(load(path/'request.json'))==canonical(request.data),'recovery_request_differs')
    validate_state(load(path/'state.json'),request)

def release_verified(run,proof,driver):
    from django.db import transaction
    from control.models import Run,ExecutorSlot,Target,AuditEvent
    from control.security import audit
    with transaction.atomic():
        # Shared web enqueue/dispatcher mutexes; no work can enter during release.
        ExecutorSlot.objects.select_for_update().get(name='dispatch')
        slot=ExecutorSlot.objects.select_for_update().get(name='private-qnx')
        Run.objects.select_for_update().get(pk=run.pk);Target.objects.select_for_update().get(pk=run.target_id)
        prior=AuditEvent.objects.filter(action='production.native_collection.recovered',object_id=RUN).first()
        if prior:
            plan.require(prior.details=={**proof,'driver_revision':driver},'recovery_audit_differs');exact_run(released=True);return
        exact_run();original_inventory(run)
        plan.require(proof.get('cleanup_verified') is True and proof.get('native_run_id')==run.native_run_id and
            proof.get('canonical_verdict')=='FAIL' and proof.get('same_supervisor') is True and
            proof.get('partial_evidence_prefix_preserved') is True and proof.get('original_ERROR_retained') is True and
            re.fullmatch('[0-9a-f]{64}',proof.get('bundle_id','')),'cleanup_proof_required')
        slot.run=None;slot.token=None;slot.expires_at=None;slot.save()
        Run.objects.filter(pk=run.pk).update(lease_expires=None)
        Target.objects.filter(pk=run.target_id).update(state='available',quarantine_reason='')
        audit(None,'production.native_collection.recovered',run.project.organization,RUN,**proof,driver_revision=driver)

def worker(driver):
    import executor_probe
    # Reuses ExecStartPre/runtime_check, account, credentials, sandbox and grant tests.
    runtime=executor_probe.probe(require_capacity=False) # Collection creates no QNX files.
    cgroup=Path('/proc/self/cgroup').read_text()
    plan.require(any(line.endswith(':/system.slice/resmgrcheck-executor.service') for line in cgroup.splitlines()),'actual_executor_cgroup_required')
    from control.models import AuditEvent
    released=AuditEvent.objects.filter(action='production.native_collection.recovered',object_id=RUN).exists()
    run=exact_run(released=released);before=original_inventory(run)
    manifest=plan.manifest_pair(Path('/opt/resmgrcheck/current'))['before']
    install_selection(manifest)
    from control.engine import registry,command
    from django.conf import settings
    from resmgrcheck.workflow import inspect_execution,Request
    from resmgrcheck.contracts import load
    from control.engine import run_path
    binding=registry(run.target,run.build);path=recovery_path(driver)
    reserve_recollection(path,Request.parse(load(run_path(run)/'request.json')))
    # A complete retained recollection is revalidated, not repeated after interruption.
    complete=False
    if path.exists():
        info=path.lstat();plan.require(not path.is_symlink() and info.st_uid==os.geteuid() and stat.S_ISDIR(info.st_mode) and not info.st_mode&0o077,'recovery_directory_protection')
        if (path/'result.json').exists():
            _,summary,_=inspect_execution(path);complete=all(row['bundle_id'] for row in summary['cases'])
    if not complete:
        plan.require(not released,'released_recovery_evidence_missing')
        code,_,_=command([settings.ENGINE_PYTHON,'-m','resmgrcheck','collect','--target',binding.alias,'--config',str(binding.config),
            '--run-id',NATIVE,'--out',str(path),'--wait'],binding,lambda:None,timeout=100)
        plan.require(code==1,'native_recollection_not_expected_FAIL')
    proof=verify_recollection(run,path)
    plan.require(original_inventory(run)==before,'original_evidence_changed_during_recovery')
    release_verified(run,proof,driver)
    # Original state/verdict/artifact graph remain ERROR; record separate recovery proof.
    proof={**proof,'passed':True,'driver_revision':driver,'application':plan.APPLICATION,'web_run_id':RUN,
        'kind':'actual-systemd-same-ID-recollection','evidence_directory':str(path),
        'original_inventory_sha256':plan.digest(json.dumps(before,sort_keys=True).encode()),'runtime':runtime}
    from resmgrcheck.artifacts import atomic_write
    receipt=receipt_path(driver)
    if receipt.exists():
        old=json.loads(plan.read_owned(receipt,os.geteuid(),{0o600}))
        plan.require({k:v for k,v in old.items() if k!='runtime'}=={k:v for k,v in proof.items() if k!='runtime'} and
            old.get('runtime',{}).get('kind')=='actual-systemd-executor-probe' and old['runtime'].get('driver_revision')==driver and
            old['runtime'].get('passed') is True,'recollection_receipt_differs')
    else:atomic_write(receipt,(json.dumps(proof,sort_keys=True,indent=2)+'\n').encode())
    return {'passed':True,'same_ID_recollection':True,'original_ERROR_retained':True}

def dropin(tool):
    python=Path('/opt/resmgrcheck/releases')/plan.APPLICATION/'.venv/bin/python'
    return ('[Service]\nType=oneshot\nExecStart=\nExecStart='+str(python)+' -I -B '+str(tool/'recover_executor_collection.py')+
        ' --worker\nRestart=no\nUMask=0077\nTimeoutStartSec=240\n').encode()

def run_in_executor(tool,driver):
    """Only the exact own unit override; restore it on successful/failed collection."""
    import deploy_https as ops
    import provision_executor as provision
    uid=pwd.getpwnam('resmgr-exec').pw_uid
    override=provision.DROP_DIR/'91-resmgrcheck-collection-recovery.conf';expected=dropin(tool)
    if override.exists() or override.is_symlink():plan.require(ops.read(override)==expected,'recovery_override_changed')
    try:
        ops.command(['systemctl','stop',provision.UNIT],timeout=30)
        if not override.exists():ops.new_file(override,expected,0o644)
        else:plan.require(ops.read(override)==expected,'recovery_override_changed')
        ops.command(['systemctl','daemon-reload'])
        ops.command(['systemctl','start',provision.UNIT],timeout=260,progress='same_ID_native_recollection')
        proof=json.loads(plan.read_owned(receipt_path(driver),uid,{0o600}))
        plan.require(proof.get('passed') is True and proof.get('driver_revision')==driver and proof.get('web_run_id')==RUN and
            proof.get('kind')=='actual-systemd-same-ID-recollection' and proof.get('application')==plan.APPLICATION and
            proof.get('canonical_verdict')=='FAIL' and proof.get('evidence_directory')==str(recovery_path(driver)) and
            proof.get('same_supervisor') is True and proof.get('cleanup_verified') is True and proof.get('original_ERROR_retained') is True,
            'actual_recollection_receipt_required')
        ops.record(plan.STATE/('collection-recovery-'+driver+'.json'),proof)
        return proof
    finally:
        if override.exists():
            plan.require(ops.read(override)==expected,'recovery_override_changed');override.unlink();ops.fsync_directory(provision.DROP_DIR)
            if not list(provision.DROP_DIR.iterdir()):provision.DROP_DIR.rmdir()
            ops.command(['systemctl','daemon-reload'])
        ops.command(['systemctl','start',provision.UNIT],timeout=45)

def apply(driver):
    global STEP
    import deploy_https as ops
    import provision_executor as provision
    import acceptance_operator as acceptance
    from django.db import connection,transaction
    from control.models import AuditEvent
    ops.require_root();provision.validate_source(driver);ops.DIAGNOSTIC=plan.STATE/'collection-recovery-diagnostic.log'
    STEP='original_blocked_evidence_preflight'
    journal_path=plan.STATE/'state.json';journal=json.loads(ops.read(journal_path,private=True))
    uid=pwd.getpwnam('resmgr-exec').pw_uid
    provision.verify_private(journal,uid);provision.verify_resume_history(journal);provision.verify_browser_resume_history(journal)
    baseline=provision.own_baseline();provision.public_health()
    plan.require(journal['baseline']==baseline and journal.get('phase') in {'approved_after_actual_runtime_probe','verified'} and
        journal.get('driver_revision') in {FAILED,driver},'unrecognized_collection_recovery_state')
    archive=plan.STATE/('attempt-'+FAILED+'.json')
    linked=journal.get('resumed_from_collection_driver')==FAILED
    expected_keys={'kind','application','driver_revision','ids','phase','baseline','private_resource_hashes',
        'resumed_from_driver','runtime_proof_driver','resumed_from_queue_driver'}
    plan.require(set(journal)==expected_keys|({'resumed_from_collection_driver'} if linked else set()),'collection_journal_fields_differ')
    if not linked:plan.require(not any((plan.STATE/name).exists() for name in ['native-result.json','report.json']),'unexpected_native_result_requires_review')
    if journal.get('phase')=='verified':
        plan.require(linked and journal.get('driver_revision')==driver and archive.exists(),'verified_recovery_binding_differs')
        proof=json.loads(ops.read(plan.STATE/('collection-recovery-'+driver+'.json'),private=True))
        plan.require(proof.get('passed') is True and proof.get('driver_revision')==driver and proof.get('web_run_id')==RUN,'verified_recovery_receipt_missing')
        return
    if archive.exists():
        saved=json.loads(ops.read(archive,private=True));plan.require(saved['journal']['driver_revision']==FAILED,'retained_collection_archive_differs')
    else:
        plan.require(journal['driver_revision']==FAILED,'original_collection_journal_required')
        failure=json.loads(ops.read(plan.STATE/'native-failure.json',private=True))
        plan.require(failure=={'driver_revision':FAILED,'failed_check':'CheckFailed','observer_errors':['ValueError'],'browser_failed_step':'collect-sensor'},'original_collection_failure_differs')
        saved={'journal':journal,'native_failure':failure,'operator_failure':json.loads(ops.read(plan.STATE/'operator-failure.json',private=True)),
            'runtime_proof':json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True))}
        ops.new_file(archive,(json.dumps(saved,sort_keys=True,indent=2)+'\n').encode())
    plan.require(saved.get('runtime_proof')==json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True)) and
        saved.get('native_failure')=={'driver_revision':FAILED,'failed_check':'CheckFailed','observer_errors':['ValueError'],'browser_failed_step':'collect-sensor'} and
        saved.get('operator_failure')=={'passed':False,'phase':'acceptance','driver_revision':FAILED,'failed_check':'command_failed_runuser','secrets_printed':False} and
        all(journal.get(k)==saved['journal'].get(k) for k in ['kind','application','ids','baseline','private_resource_hashes','runtime_proof_driver','resumed_from_driver','resumed_from_queue_driver']),
        'retained_collection_archive_differs')
    with transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY')
        released=AuditEvent.objects.filter(action='production.native_collection.recovered',object_id=RUN).exists()
        run=exact_run(released=released);original_inventory(run)
    # Diagnose the absent recovery selector without accepting unknown existing state.
    path=selected_path();has_selector=path.exists() or path.is_symlink()
    if has_selector:plan.require(json.loads(plan.read_owned(path,uid,{0o600}))==plan.manifest_pair(ops.SOURCE)['before'],'selected_controller_differs')
    diagnosis=plan.STATE/'collection-recovery-diagnosis.json'
    if not diagnosis.exists():
        plan.require(not has_selector and not (plan.ENGINE_ROOT/'build/qnx-x86_64/targetctl').exists(),'missing_controller_selection_not_confirmed')
        ops.record(diagnosis,{'missing_selected_deployment':True,'local_bootstrap_binary_absent':True,'original_driver':FAILED,
            'collection_exit':2,'original_ERROR_retained':True,'same_native_run_id':NATIVE})
    else:plan.require(json.loads(ops.read(diagnosis,private=True))=={'missing_selected_deployment':True,'local_bootstrap_binary_absent':True,
        'original_driver':FAILED,'collection_exit':2,'original_ERROR_retained':True,'same_native_run_id':NATIVE},'recovery_diagnosis_differs')
    print(json.dumps({'step':'missing_recovery_controller_selection','confirmed':True,'SDK_bootstrap_prohibited':True}),flush=True)
    tool=Path('/opt/resmgrcheck/operator-tools')/driver
    override=provision.DROP_DIR/'91-resmgrcheck-collection-recovery.conf';expected=dropin(tool)
    if provision.DROP_DIR.exists():plan.require(all(p==override and ops.read(p)==expected for p in provision.DROP_DIR.iterdir()),'unknown_executor_override')
    loaded=ops.command(['systemctl','show','--value','--property=DropInPaths',provision.UNIT]).decode().split()
    plan.require(loaded==[] or loaded==[str(override)] and override.exists() and ops.read(override)==expected,'unknown_loaded_executor_override')
    plan.require(ops.read(Path('/etc/systemd/system')/provision.UNIT)==ops.git('show',plan.APPLICATION+':web/ops/production/'+provision.UNIT),'executor_unit_differs')
    plan.require((plan.ENGINE_ROOT/'.local/state').is_symlink() and (plan.ENGINE_ROOT/'.local/state').resolve()==STATE_ROOT,'engine_state_binding')
    import recover_https_auth as immutable
    immutable.validate(Path('/opt/resmgrcheck/releases')/plan.APPLICATION,plan.APPLICATION)
    git=['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(plan.ENGINE_ROOT),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',plan.ENGINE_ROOT]
    plan.require(ops.command([*git,'rev-parse','HEAD']).decode().strip()==plan.ENGINE,'engine_revision_differs')
    plan.require(not ops.command([*git,'diff','HEAD','--']).strip(),'engine_source_differs')
    for directory in [tool.parent,tool]:provision.directory(directory,0,0o755)
    for name in ['executor_plan.py','executor_probe.py','recover_executor_collection.py']:
        provision.exact_file(tool/name,ops.git('show',driver+':web/ops/production/'+name),0,0o644)
    plan.require(all(p.name in {'executor_plan.py','executor_probe.py','recover_executor_collection.py'} or
        re.fullmatch('[.]provision-[0-9a-f]{32}',p.name) and stat.S_IMODE(p.lstat().st_mode)==0o644 and ops.read(p) in
        [ops.git('show',driver+':web/ops/production/'+name) for name in ['executor_plan.py','executor_probe.py','recover_executor_collection.py']]
        for p in tool.iterdir()),'unknown_recovery_tool')
    provision.directory(provision.DROP_DIR,0,0o755)
    # Keep the original held lease/quarantine throughout the nonroot recollection.
    STEP='actual_systemd_same_ID_collection';proof=run_in_executor(tool,driver)
    STEP='root_recollection_verification'
    run=exact_run(released=True);original_inventory(run)
    checked=verify_recollection(run,recovery_path(driver))
    plan.require(all(proof.get(key)==value for key,value in checked.items()),'root_recollection_verification_differs')
    plan.require(provision.own_baseline()==baseline,'public_application_changed');provision.public_health()
    current=json.loads(ops.read(journal_path,private=True));plan.require(current==journal,'executor_journal_changed')
    if not linked:ops.record(journal_path,{**journal,'driver_revision':driver,'resumed_from_collection_driver':FAILED})
    print(json.dumps({'same_ID_recollection':'passed','original_ERROR_retained':True,'canonical_recovered_verdict':'FAIL',
        'new_acceptance_batch':'pending','P8':'IN_PROGRESS'}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--driver-revision');parser.add_argument('--apply',action='store_true');parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    try:
        if args.worker:
            driver=Path(__file__).resolve().parent.name;plan.require(re.fullmatch('[0-9a-f]{40}',driver),'immutable_operator_tool_required')
            print(json.dumps(worker(driver)))
        else:
            import provision_executor as provision
            plan.require(args.driver_revision and re.fullmatch('[0-9a-f]{40}',args.driver_revision),'exact_driver_required')
            if args.apply:
                import deploy_https as ops
                ops.require_root();os.umask(0o077)
                python=Path('/opt/resmgrcheck/releases')/plan.APPLICATION/'.venv/bin/python'
                if Path(sys.prefix).resolve()!=python.parent.parent.resolve():os.execv(str(python),[str(python),'-I','-B',str(Path(__file__).resolve()),*sys.argv[1:]])
                import acceptance_operator as acceptance
                acceptance.load_application(plan.APPLICATION)
                lock=os.open(plan.STATE/'collection-recovery.lock',os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600)
                try:
                    info=os.fstat(lock);plan.require(info.st_uid==0 and info.st_nlink==1 and stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600,'recovery_lock_protection')
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);apply(args.driver_revision)
                    # Only after actual same-ID cleanup proof may a reviewed new
                    # acceptance batch run; the original ERROR is never relabeled.
                    STEP='native_dashboard_acceptance';provision.apply(args.driver_revision)
                finally:os.close(lock)
            else:
                provision.validate_source(args.driver_revision)
                print(json.dumps({'read_only_plan':True,'same_native_run_id':NATIVE,'original_ERROR_retained':True,
                    'recovery_native_launch':False,'root_required':True,'recollection_identity':'actual resmgrcheck-executor.service',
                    'evidence':'separate private recovery directory','release_lease_only_after_canonical_cleanup':True,
                    'after_verified_cleanup':'one reviewed dashboard acceptance batch: 3 native cases and a withheld queued revocation case',
                    'Nginx_auth_database_services_changed':False,'P8':'IN_PROGRESS'}))
    except BaseException as error:
        print(json.dumps({'passed':False,'failed_step':provision.CURRENT_STEP if not args.worker and STEP=='native_dashboard_acceptance' else STEP,
            'failed_check':str(error) if (isinstance(error,ValueError) or not args.worker and isinstance(error,provision.ops.CheckFailed)) and re.fullmatch('[a-z0-9_]{1,100}',str(error)) else type(error).__name__,
            'original_ERROR_retained':True,'secrets_printed':False}));raise SystemExit(1) from None
