#!/usr/bin/env python3
"""Read-only diagnosis of the exact W031 sensor collection attempt. No target I/O."""
import json,os,pwd,re,stat,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import executor_plan as plan
import deploy_https as ops

DRIVER='45bde2e4a51dea4830589bab7466700512ee615f'
RUN='274989f6-c306-4581-8f69-3db1ca21997d'
ATTEMPT='beb038e6bb43435888c62e95a95efdb8'
SAFE_ERRORS={'resource_symlink','resource_protection','resource_changed','absolute_path_required',
    'native_cleanup_unproven','canonical_verdict_or_cleanup_differs','evidence_source_build_mismatch',
    'sealed_inventory_missing','artifact_integrity_failed','inventory_graph_mismatch','inventory_artifact_mismatch',
    'inventory_identity_mismatch','native_work_still_active_preserved','dispatch_sentinel_missing_or_occupied',
    'native_evidence_incomplete','cleanup_or_coverage_unestablished','launch_or_collection_uncertain',
    'previous_local_executor_still_owns_lock','prelaunch_infrastructure_error','actor_authorization_revoked'}

def safe_error(error):
    value=str(error)
    return value if value in SAFE_ERRORS else type(error).__name__

def file_metadata(path,root,uid):
    row={'path':str(path.relative_to(root))}
    if not path.exists() and not path.is_symlink():return {**row,'present':False}
    info=path.lstat()
    row.update(present=True,uid=info.st_uid,gid=info.st_gid,mode=oct(stat.S_IMODE(info.st_mode)),
        regular=stat.S_ISREG(info.st_mode),symlink=stat.S_ISLNK(info.st_mode),links=info.st_nlink,bytes=info.st_size)
    try:
        raw=plan.read_owned(path,uid,{0o400,0o440,0o600,0o640},2*1024**2)
        row.update(read_validation='passed',sha256=plan.digest(raw))
    except (OSError,ValueError) as error:row['read_validation']=safe_error(error)
    return row

def recovery_metadata(run,uid):
    """Fixed failed recovery only; inspect retained bytes, never contact the target."""
    import recover_executor_collection as recovery
    driver='75b3c542b1823bc258147bd9175aa7f2acff634d'
    path=recovery.recovery_path(driver)
    result={'driver_revision':driver,'files':[file_metadata(path/name,path,uid) for name in
        ['request.json','state.json','result.json','cases/timeout/status.json',
         'cases/timeout/partial-events.jsonl','cases/timeout/bundle/result.json',
         'cases/timeout/bundle/partial.json','cases/timeout/bundle/bundle.json']]}
    for label,name,field in [('host_error','result.json','host_error'),
                            ('bundle_error','cases/timeout/bundle/partial.json','error_type')]:
        if (path/name).exists():
            value=json.loads(plan.read_owned(path/name,uid,{0o600})).get(field)
            result[label]=value if value in {None,'CalledProcessError','Invalid','PermissionError','TransportError'} else 'other'
    selected=recovery.selected_path()
    result['selection']=file_metadata(selected,selected.parent,uid)
    if result['selection'].get('read_validation')=='passed':
        from resmgrcheck.contracts import loads
        result['selection_matches_approved']=loads(plan.read_owned(selected,uid,{0o600}))==plan.manifest_pair(ops.SOURCE)['before']
    from control.models import AuditEvent
    released=AuditEvent.objects.filter(action='production.native_collection.recovered',object_id=RUN).exists()
    result['recovery_audit_present']=released
    for name,check in [('blocked_or_released_binding',lambda:recovery.exact_run(released=released)),
                       ('original_inventory',lambda:recovery.original_inventory(run)),
                       ('recollection_proof',lambda:recovery.verify_recollection(run,path))]:
        try:check();result[name]='passed'
        except Exception as error:
            allowed={'exact_blocked_ERROR_required','original_authority_not_closed','blocked_lease_binding_differs',
                'released_recovery_state_differs','sealed_original_differs','recovered_request_or_coverage_differs',
                'same_ID_supervisor_or_partial_differs','recovered_native_verdict_or_cleanup_unproven'}
            result[name]=str(error) if str(error) in allowed else safe_error(error)
    return result

def inspect():
    import acceptance_operator as acceptance
    acceptance.load_application(plan.APPLICATION)
    from django.db import connection,transaction
    from control.models import Run,ExecutorSlot,AuditEvent,AccessCode,AccessSession
    from control.engine import run_path
    from control.storage import verify_inventory
    from resmgrcheck.workflow import inspect_execution
    from resmgrcheck.artifacts import inspect_bundle
    import executor_operator as operator
    result={'read_only':True,'target_commands':False,'secrets_printed':False,'active_application':plan.APPLICATION}
    for name in ['state.json','native-failure.json','operator-failure.json']:
        raw=ops.read(plan.STATE/name,private=True)
        value=json.loads(raw)
        result[name]={'sha256':plan.digest(raw),'driver_is_expected':value.get('driver_revision')==DRIVER}
        for key in ['phase','failed_check','browser_failed_step','observer_errors']:
            if key in value:
                item=value[key]
                if isinstance(item,str) and re.fullmatch('[a-zA-Z0-9_-]{1,100}',item):result[name][key]=item
                elif key=='observer_errors' and isinstance(item,list):result[name][key]=[v for v in item if v in {'ValueError','CheckFailed','OSError','KeyError','JSONDecodeError'}]
    with transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY')
        run=Run.objects.select_related('project__organization','build','target','access_session__code__created_by').get(pk=RUN)
        account=run.access_session.code.created_by
        plan.require(str(run.project_id)==plan.IDS['project'] and str(run.target_id)==plan.IDS['target'] and
            str(run.build_id)==plan.IDS['before'] and run.native_run_id=='w274989f6c30645818f' and
            AuditEvent.objects.filter(actor=account,action='https.acceptance.created',details__acceptance_id=str(uuid.UUID(ATTEMPT))).exists(),
            'exact_failed_run_binding_required')
        result['run']={'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'state':run.state,
            'error_code':run.error_code if run.error_code in SAFE_ERRORS else 'other' if run.error_code else '',
            'target_state':run.target.state,'cleanup_verified':run.target_cleanup_verified,'started':run.started_at is not None,
            'finished':run.finished_at is not None,'incidents':len(run.incidents),
            'summary_verdicts':[v.get('verdict') for v in run.summary.get('cases',[]) if v.get('verdict') in {'PASS','FAIL','ERROR','UNSUPPORTED','NOT_RUN'}]}
        result['cleanup']={'account_disabled':not account.is_active,
            'all_codes_revoked':not AccessCode.objects.filter(created_by=account,revoked_at=None).exists(),
            'all_code_sessions_revoked':not AccessSession.objects.filter(code__created_by=account,revoked_at=None).exists()}
        result['executor_slots']=[{'name':row.name,'holds_this_run':str(row.run_id)==RUN,'occupied':row.run_id is not None,
            'lease_expiry_present':row.expires_at is not None} for row in ExecutorSlot.objects.filter(name__in=['dispatch','private-qnx'])]
        result['audit_actions']=list(AuditEvent.objects.filter(object_id=RUN,action__in=['run.queued','run.started','run.uncertain','run.collected','run.rejected']).order_by('created_at').values_list('action',flat=True))
        root=run_path(run);uid=pwd.getpwnam('resmgr-exec').pw_uid
        paths=[root/name for name in ['request.json','state.json','result.json','web-evidence-v2.json','cases/timeout/status.json',
            'cases/timeout/partial-events.jsonl','cases/timeout/bundle/status.json','cases/timeout/bundle/result.json']]
        history=root/'history'
        if history.is_dir() and not history.is_symlink():
            snapshots=sorted(history.iterdir());plan.require(len(snapshots)<=32,'history_bound')
            for snapshot in snapshots:
                plan.require(re.fullmatch('collection-[0-9]{6}',snapshot.name) and not snapshot.is_symlink(),'history_path_invalid')
                paths.extend(snapshot/name for name in ['result.json','state.json','timeout/status.json','timeout/partial-events.jsonl'])
        result['files']=[file_metadata(path,root,uid) for path in paths]
        try:result['recovery']=recovery_metadata(run,uid)
        except Exception as error:result['recovery']={'inspection_failed':safe_error(error)}
        for name,check in [('inventory',lambda:verify_inventory(run)),('execution',lambda:inspect_execution(root)),
            ('expected_FAIL_and_cleanup',lambda:operator.completed(run,'FAIL'))]:
            try:check();result[name]='passed'
            except Exception as error:result[name]=safe_error(error)
        bundle=root/'cases/timeout/bundle'
        if bundle.exists():
            try:
                value=inspect_bundle(bundle)
                result['canonical']={'verdict':value.result.data['verdict'],'cleanup_ok':value.status['cleanup_ok'],
                    'unresolved':value.status['unresolved'],'intentional_defect_reasons_present':
                    {'cancellation_not_completed','pending_state_not_released'}<=set(value.result.data['reasons'])}
            except Exception as error:result['canonical']={'validation':safe_error(error)}
    result['units_active']={name:ops.command(['systemctl','is-active',name]).strip()==b'active' for name in
        ['nginx.service','resmgrcheck-db.service','resmgrcheck-web.service','resmgrcheck-executor.service']}
    try:
        status,_,body=ops.Client().request('/readyz/')
        result['HTTPS_readiness_200']=status==200 and json.loads(body)=={'status':'ready'}
    except Exception:result['HTTPS_readiness_200']=False
    return result

if __name__=='__main__':
    try:
        ops.require_root()
        python=Path('/opt/resmgrcheck/releases')/plan.APPLICATION/'.venv/bin/python'
        if Path(sys.prefix).resolve()!=python.parent.parent.resolve():os.execv(str(python),[str(python),'-I','-B',str(Path(__file__).resolve())])
        print(json.dumps(inspect(),sort_keys=True))
    except Exception as error:
        print(json.dumps({'read_only':True,'inspection_failed':safe_error(error),'secrets_printed':False}));raise SystemExit(1) from None
