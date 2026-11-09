#!/usr/bin/env python3
"""One reviewed operator workflow; never deploys HTTPS or changes authentication."""
import argparse,fcntl,json,os,pwd,re,stat,sys,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as ops
import executor_plan as plan

UNIT='resmgrcheck-executor.service'
DROP_DIR=Path('/etc/systemd/system')/(UNIT+'.d')
DROP=DROP_DIR/'90-resmgrcheck-native-qualification.conf'
CURRENT_STEP='source_validation'
FAILED_SELECTION_DRIVER='ce97df9e7e3671528316063a2bc36250b8d4d788'

def preserve_failed_selection(journal,uid):
    """Adopt only the known pre-bootstrap selector failure, without resetting state."""
    plan.require(set(journal)=={'kind','application','driver_revision','ids','phase','baseline','private_resource_hashes'} and
        journal.get('kind')=='approved-production-qnx-executor-v1' and journal.get('application')==plan.APPLICATION and
        journal.get('ids')==plan.IDS and journal.get('driver_revision')==FAILED_SELECTION_DRIVER and
        journal.get('phase')=='approved_after_actual_runtime_probe','unrecognized_executor_resume_state')
    plan.require(not any(plan.STATE.glob('native-*.intent.json')) and not any((plan.STATE/name).exists() for name in ['native-result.json','native-failure.json','report.json']),
        'native_work_already_recorded_requires_review')
    verify_private(journal,uid)
    proof=json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True))
    plan.require(proof.get('passed') is True and proof.get('kind')=='actual-systemd-executor-probe' and
        proof.get('application')==plan.APPLICATION and proof.get('driver_revision')==FAILED_SELECTION_DRIVER and
        proof.get('database_grants_verified') is True,'retained_executor_runtime_proof_differs')
    failure={'passed':False,'phase':'acceptance','driver_revision':FAILED_SELECTION_DRIVER,
        'failed_check':'exact_approved_native_plan_required','secrets_printed':False}
    path=plan.STATE/('attempt-'+FAILED_SELECTION_DRIVER+'.json')
    expected={'journal':journal,'operator_failure':failure,'runtime_proof':proof}
    if path.exists():plan.require(json.loads(ops.read(path,private=True))==expected,'executor_resume_history_differs')
    else:
        plan.require(json.loads(ops.read(plan.STATE/'operator-failure.json',private=True))==failure,'executor_resume_failure_differs')
        ops.new_file(path,(json.dumps(expected,sort_keys=True,indent=2)+'\n').encode())
    return path

def bind_resume(journal,path,driver):
    # The full original state/failure/proof is already protected before this CAS.
    current=json.loads(ops.read(path,private=True));plan.require(current==journal,'executor_journal_changed_during_resume')
    updated={**journal,'driver_revision':driver,'resumed_from_driver':FAILED_SELECTION_DRIVER,'runtime_proof_driver':FAILED_SELECTION_DRIVER}
    ops.record(path,updated);return updated

def verify_resume_history(journal):
    archive=json.loads(ops.read(plan.STATE/('attempt-'+FAILED_SELECTION_DRIVER+'.json'),private=True))
    previous=archive['journal']
    plan.require(previous.get('driver_revision')==FAILED_SELECTION_DRIVER and previous.get('phase')=='approved_after_actual_runtime_probe' and
        journal.get('runtime_proof_driver')==FAILED_SELECTION_DRIVER and
        all(journal.get(key)==previous.get(key) for key in ['kind','application','ids','baseline','private_resource_hashes']) and
        archive['runtime_proof']==json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True)), 'executor_resume_history_differs')

def step(value):
    global CURRENT_STEP
    CURRENT_STEP=value;print(json.dumps({'step':value,'status':'running'}),flush=True)

def directory(path,uid,mode):
    gid=pwd.getpwuid(uid).pw_gid
    plan.require(not any(p.is_symlink() for p in [path,*path.parents]),'directory_symlink')
    if not path.exists():path.mkdir(mode=mode);os.chown(path,uid,gid);path.chmod(mode);ops.fsync_directory(path.parent)
    info=path.lstat();plan.require(stat.S_ISDIR(info.st_mode) and info.st_uid==uid and info.st_gid==gid and stat.S_IMODE(info.st_mode)==mode,'directory_protection')

def exact_file(path,raw,uid,mode):
    gid=pwd.getpwuid(uid).pw_gid
    if path.exists() or path.is_symlink():
        plan.require(plan.read_owned(path,uid,{mode})==raw and path.lstat().st_gid==gid,'existing_resource_differs')
    else:
        # Publish only a complete file, without replacing an occupied destination.
        # Interrupted unpublished temporaries are retained, never mistaken for config.
        from customer_runner.archive import publish
        temporary=path.parent/('.provision-'+uuid.uuid4().hex)
        ops.new_file(temporary,raw,mode,owner=(uid,gid));publish(temporary,path)

def dropin(tool):
    return ('[Service]\nType=oneshot\nExecStart=\nExecStart='+str(Path('/opt/resmgrcheck/releases')/plan.APPLICATION/'.venv/bin/python')+
        ' -I -B '+str(tool/'executor_probe.py')+'\nRestart=no\nTimeoutStartSec=180\n').encode()

def own_baseline():
    from https_config import site_config,http_config
    plan.require(ops.read(ops.SITE)==site_config(plan.APPLICATION).encode() and ops.read(ops.HTTP)==http_config().encode() and
        ops.ENABLED.is_symlink() and ops.ENABLED.resolve()==ops.SITE,'existing_HTTPS_configuration_differs')
    return {'current':str(Path('/opt/resmgrcheck/current').resolve()),'site':ops.digest(ops.read(ops.SITE)),
        'http':ops.digest(ops.read(ops.HTTP)),'enabled':os.readlink(ops.ENABLED)}

def public_health():
    from https_checks import security
    client=ops.Client()
    for path in ['/','/readyz/']:
        status,headers,body=client.request(path);plan.require(status==200,'public_readiness_failed');security(headers)
        if path=='/readyz/':plan.require(json.loads(body)=={'status':'ready'},'public_readiness_failed')

def helper(phase,driver):
    try:
        raw=ops.command([Path('/opt/resmgrcheck/current/.venv/bin/python'),'-I','-B',ops.HERE/'executor_operator.py',
            '--phase',phase,'--driver-revision',driver],timeout=1500 if phase=='acceptance' else 90,
            progress='native_dashboard_acceptance' if phase=='acceptance' else None)
    except ops.CheckFailed:
        record=plan.STATE/'operator-failure.json'
        if record.exists():
            safe=json.loads(ops.read(record,private=True))
            if safe.get('driver_revision')==driver and safe.get('phase')==phase:print(json.dumps({'executor_operator_failure':safe}),flush=True)
        failure=plan.STATE/'native-failure.json'
        if phase=='acceptance' and failure.exists():
            safe=json.loads(ops.read(failure,private=True))
            if safe.get('driver_revision')==driver:print(json.dumps({'native_acceptance_failure':safe}),flush=True)
        raise
    result=json.loads(raw);plan.require(result.get('passed') is True,'executor_operator_'+phase+'_not_passed');return result

def remove_dropin(expected):
    if DROP.exists() or DROP.is_symlink():
        plan.require(ops.read(DROP)==expected,'qualification_override_changed')
        DROP.unlink();ops.fsync_directory(DROP_DIR)
        if not list(DROP_DIR.iterdir()):DROP_DIR.rmdir()
        ops.command(['systemctl','daemon-reload'])
    plan.require(not ops.command(['systemctl','show','--value','--property=DropInPaths',UNIT]).strip(),'executor_overrides_remain')

def validate_source(driver):
    ops.source_check(plan.APPLICATION,driver)
    plan.require(re.fullmatch('[0-9a-f]{40}',driver),'exact_driver_required')
    sys.path.insert(0,str(ops.SOURCE));plan.manifest_pair(ops.SOURCE)
    target=ops.SOURCE/'.local/web/engine/config/target.local.json'
    plan.require(plan.digest(plan.read_owned(target,ops.SOURCE.stat().st_uid,{0o600}))==plan.INPUT_CONFIG_SHA,'qualified_input_configuration_changed')
    plan.require(plan.digest(plan.read_owned(ops.SOURCE/'.local/qnx-known-hosts',ops.SOURCE.stat().st_uid,{0o600,0o644,0o664}))==plan.KNOWN_HOSTS_SHA,'qualified_host_identity_changed')

def verify_private(journal,uid):
    plan.require(set(journal.get('private_resource_hashes',{}))=={'ssh-key','known-hosts','ssh-config','target.json','registry.json','before-deployment.json','after-deployment.json'},'verified_inventory_differs')
    for name,expected in journal['private_resource_hashes'].items():
        plan.require(plan.digest(plan.read_owned(plan.CONFIG/name,uid,{0o600}))==expected,'verified_private_resource_changed')

def finish(driver,binding,journal,journal_path,baseline,result):
    step('guarded_idle_executor_stop_start_rehearsal');helper('rehearse',driver)
    plan.require(own_baseline()==baseline,'protected_web_state_changed');public_health()
    report={**binding,'passed':True,'native':result,'executor_idle_stop_start':'passed','application_rollback':'not_run',
        'HTTPS_auth_configuration_changed':False,'customer_runner':'disabled','AI':'disabled','independent_UAT':'pending'}
    ops.record(plan.STATE/'report.json',report);journal['phase']='verified';ops.record(journal_path,journal)
    print(json.dumps({'passed':True,'native_passed':True,'report':str(plan.STATE/'report.json'),'application_revision':plan.APPLICATION,
        'native_runs':result['native_runs'],'observations':result['observations'],'cleanup':result['cleanup'],
        'executor_idle_stop_start':'passed','full_application_rollback':'not_run','HTTPS_unchanged':True,'independent_UAT':'pending'}))

def apply(driver):
    ops.require_root();os.umask(0o077);validate_source(driver)
    plan.require(Path('/opt/resmgrcheck/current').resolve()==Path('/opt/resmgrcheck/releases')/plan.APPLICATION,'active_application_differs')
    exec_uid=pwd.getpwnam('resmgr-exec').pw_uid
    directory(plan.STATE,0,0o700);ops.DIAGNOSTIC=plan.STATE/'diagnostic.log'
    fd=os.open(plan.STATE/'lock',os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd);plan.require(info.st_uid==0 and info.st_nlink==1 and stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600,'lock_protection')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        tool=Path('/opt/resmgrcheck/operator-tools')/driver;expected_drop=dropin(tool)
        journal_path=plan.STATE/'state.json'
        binding={'kind':'approved-production-qnx-executor-v1','application':plan.APPLICATION,'driver_revision':driver,'ids':plan.IDS}
        journal=json.loads(ops.read(journal_path,private=True)) if journal_path.exists() else {**binding,'phase':'prepared'}
        known_failed=journal.get('driver_revision')==FAILED_SELECTION_DRIVER and driver!=FAILED_SELECTION_DRIVER
        plan.require(known_failed or all(journal.get(k)==v for k,v in binding.items()),'another_executor_provisioning_recorded')
        baseline=own_baseline();public_health();plan.require(baseline['current'].endswith('/'+plan.APPLICATION),'active_application_differs')
        import recover_https_auth as immutable
        immutable.validate(Path('/opt/resmgrcheck/releases')/plan.APPLICATION,plan.APPLICATION)
        if 'baseline' in journal:plan.require(journal['baseline']==baseline,'protected_web_state_changed')
        if not known_failed:journal['baseline']=baseline;ops.record(journal_path,journal)
        if known_failed:plan.require(not DROP.exists() and not DROP.is_symlink(),'failed_selector_override_unexpected')
        if DROP.exists() or DROP.is_symlink():remove_dropin(expected_drop)
        plan.require(not ops.command(['systemctl','show','--value','--property=DropInPaths',UNIT]).strip(),'executor_overrides_require_review')
        plan.require(ops.read(Path('/etc/systemd/system')/UNIT)==ops.git('show',plan.APPLICATION+':web/ops/production/'+UNIT),'executor_unit_differs')
        engine_git=['git','--no-optional-locks','-c','safe.directory=','-c','safe.directory='+str(plan.ENGINE_ROOT),
            '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',plan.ENGINE_ROOT]
        plan.require(ops.command([*engine_git,'rev-parse','HEAD']).decode().strip()==plan.ENGINE and
            not ops.command([*engine_git,'diff','HEAD','--']).strip(),'pinned_engine_changed')
        plan.require((plan.ENGINE_ROOT/'.local/state').is_symlink() and (plan.ENGINE_ROOT/'.local/state').resolve()==Path('/var/lib/resmgrcheck/engine-state'),'engine_state_binding')
        if known_failed:
            step('verify_completed_executor_provisioning')
            preserve_failed_selection(journal,exec_uid)
            helper('resume-preflight',driver)
            journal=bind_resume(journal,journal_path,driver)
        if journal.get('resumed_from_driver')==FAILED_SELECTION_DRIVER:verify_resume_history(journal)
        if journal.get('phase')=='verified':
            verify_private(journal,exec_uid)
            helper('verify',driver);plan.require(own_baseline()==baseline,'protected_web_state_changed')
            print(json.dumps({'passed':True,'reused_verified_native_acceptance':True,'report':str(plan.STATE/'report.json')}));return
        native_result=plan.STATE/'native-result.json'
        if native_result.exists():
            result=json.loads(ops.read(native_result,private=True))
            plan.require(result.get('passed') is True and result.get('driver_revision')==driver and result.get('application')==plan.APPLICATION,'retained_native_result_differs')
            verify_private(journal,exec_uid);helper('verify',driver)
            finish(driver,binding,journal,journal_path,baseline,result);return
        state=ops.command(['systemctl','show','--value','--property=ActiveState',UNIT]).strip()
        if journal.get('resumed_from_driver')==FAILED_SELECTION_DRIVER:
            step('resume_native_dashboard_acceptance');verify_private(journal,exec_uid);helper('resume-preflight',driver)
            plan.require(state in {b'active',b'inactive',b'failed'},'executor_not_ready_for_acceptance_resume')
            if state!=b'active':ops.command(['systemctl','start',UNIT],timeout=45)
            result=helper('acceptance',driver);plan.require(result.get('native_passed') is True,'native_acceptance_incomplete')
            finish(driver,binding,journal,journal_path,baseline,result);return
        if state==b'active' and journal.get('phase')=='approved_after_actual_runtime_probe':
            helper('idle',driver);ops.command(['systemctl','stop',UNIT],timeout=30);state=b'inactive'
        plan.require(state in {b'inactive',b'failed'},'executor_already_active_requires_review')
        step('validate_dedicated_database_scope');helper('prepare',driver)
        step('install_exact_private_lab_binding')
        directory(plan.CONFIG,exec_uid,0o700)
        operator_uid=ops.SOURCE.stat().st_uid
        key=plan.read_owned(Path('/home/mignon/.ssh/id_ed25519'),operator_uid,{0o600},16384)
        hosts=plan.read_owned(ops.SOURCE/'.local/qnx-known-hosts',operator_uid,{0o600,0o644,0o664})
        resources={'ssh-key':key,'known-hosts':hosts,'ssh-config':plan.ssh_config(),
            'target.json':(json.dumps(plan.target_config(),sort_keys=True,indent=2)+'\n').encode(),
            'registry.json':(json.dumps(plan.registry(),sort_keys=True,indent=2)+'\n').encode()}
        for role,(name,expected) in plan.MANIFESTS.items():
            raw=ops.git('show',driver+':'+name);plan.require(ops.digest(raw)==expected,'manifest_hash_differs');resources[role+'-deployment.json']=raw
        inventory={name:ops.digest(raw) for name,raw in resources.items()}
        if 'private_resource_hashes' in journal:plan.require(journal['private_resource_hashes']==inventory,'private_source_changed_during_resume')
        journal['private_resource_hashes']=inventory;ops.record(journal_path,journal)
        for name,raw in resources.items():exact_file(plan.CONFIG/name,raw,exec_uid,0o600)
        directory(tool.parent,0,0o755);directory(tool,0,0o755)
        for name in ['executor_plan.py','executor_probe.py']:
            exact_file(tool/name,ops.git('show',driver+':web/ops/production/'+name),0,0o644)
        known={name:ops.git('show',driver+':web/ops/production/'+name) for name in ['executor_plan.py','executor_probe.py']}
        for path in tool.iterdir():
            if path.name in known:continue
            plan.require(re.fullmatch(r'[.]provision-[0-9a-f]{32}',path.name) and stat.S_IMODE(path.lstat().st_mode)==0o644 and ops.read(path) in known.values(), 'unknown_operator_tool_resource')
        step('actual_executor_systemd_context_probe');directory(DROP_DIR,0,0o755)
        plan.require(not list(DROP_DIR.iterdir()),'unknown_executor_override')
        ops.new_file(DROP,expected_drop,0o644);ops.command(['systemctl','daemon-reload'])
        started=time.time_ns()
        try:ops.command(['systemctl','start',UNIT],timeout=200,progress='actual_executor_systemd_context_probe')
        finally:remove_dropin(expected_drop)
        probe_path=plan.probe_file(driver)
        plan.require(probe_path.stat().st_mtime_ns>=started,'executor_probe_receipt_stale')
        proof=json.loads(plan.read_owned(probe_path,exec_uid,{0o600}))
        plan.require(proof.get('passed') is True and proof.get('kind')=='actual-systemd-executor-probe' and
            proof.get('application')==plan.APPLICATION and proof.get('driver_revision')==driver,'executor_probe_unproven')
        ops.record(plan.STATE/'runtime-proof.json',proof)
        step('publish_exact_target_and_build_approvals');helper('publish',driver)
        journal['phase']='approved_after_actual_runtime_probe';ops.record(journal_path,journal)
        step('native_dashboard_acceptance')
        ops.command(['systemctl','start',UNIT],timeout=45)
        result=helper('acceptance',driver)
        plan.require(result.get('native_passed') is True,'native_acceptance_incomplete')
        finish(driver,binding,journal,journal_path,baseline,result)
    finally:os.close(fd)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--driver-revision',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:
        if args.apply:apply(args.driver_revision)
        else:
            validate_source(args.driver_revision)
            print(json.dumps({'mode':'read-only fixed lab executor plan','application':plan.APPLICATION,'engine':plan.ENGINE,'ids':plan.IDS,
                'manifest_SHA256':{role:row[1] for role,row in plan.MANIFESTS.items()},'existing_key_reused':True,
                'new_credentials':False,'root_required':True,'native_tests':'3 bounded cases; same-ID loss recovery and live/queued revocation',
                'database_locking':'UPDATE(id) only on user/code, with invoker-role triggers denying every actual executor UPDATE',
                'known_failed_selector_resume':FAILED_SELECTION_DRIVER,'completed_probe_and_approvals_on_resume':'verified and reused without reinstallation',
                'Nginx_auth_web_database_services_changed':False,'temporary_own_executor_probe_override':True,'historical_target_files_deleted':False}))
    except BaseException as error:
        print(json.dumps({'passed':False,'failed_step':CURRENT_STEP,'failed_check':str(error) if isinstance(error,(ValueError,ops.CheckFailed)) and re.fullmatch('[a-z0-9_]{1,100}',str(error)) else type(error).__name__,
            'protected_diagnostics':str(plan.STATE/'diagnostic.log'),'secrets_printed':False}));raise SystemExit(1) from None
