#!/usr/bin/env python3
"""Root coordinator for one exact approved lab; native dispatcher remains nonroot."""
import argparse,json,os,pwd,re,shlex,signal,sys,threading,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import executor_plan as plan
import deploy_https as ops
import acceptance_operator as acceptance

def idle():
    from control.models import Run,ExecutorSlot
    from control.jobs import ACTIVE
    plan.require(not Run.objects.filter(state__in=ACTIVE).exists() and not ExecutorSlot.objects.filter(run__isnull=False).exists(),'existing_work_requires_reconciliation')

def prepare():
    from django.db import transaction,connection
    from django.db.migrations.executor import MigrationExecutor
    from control.models import User,Organization,Project,Target,BuildRelease,AuditEvent
    from control.security import audit
    idle();pair=plan.manifest_pair(ops.SOURCE)
    plan.require(not MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes()),'unexpected_migrations')
    from executor_locking import install
    locking=install(connection)
    if not AuditEvent.objects.filter(action='production.executor.lock_guard_installed',object_id='resmgr_exec').exists():
        audit(None,'production.executor.lock_guard_installed',object_id='resmgr_exec',lock_only=locking)
    with transaction.atomic():
        existing=AuditEvent.objects.filter(action='production.executor.prepared',object_id=plan.IDS['target']).first()
        if existing:
            plan.require(existing.details=={'application':plan.APPLICATION,'engine':plan.ENGINE,'ids':plan.IDS},'approval_history_differs')
            check_bindings(pair,allow_unapproved=True);return
        from django.db.models import Q
        plan.require(not User.objects.filter(pk=plan.IDS['custodian']).exists() and not Organization.objects.filter(pk=plan.IDS['organization']).exists() and
            not Project.objects.filter(pk=plan.IDS['project']).exists() and not Target.objects.filter(pk=plan.IDS['target']).exists() and
            not BuildRelease.objects.filter(pk__in=[plan.IDS['before'],plan.IDS['after']]).exists(),'approval_identifier_occupied')
        owner=User.objects.create_user('production-lab-custodian',None,id=plan.IDS['custodian'],is_active=False)
        org=Organization.objects.create(id=plan.IDS['organization'],name='Operator-approved ResMgrCheck lab')
        project=Project.objects.create(id=plan.IDS['project'],organization=org,name='Qualified QNX 8 lab',created_by=owner)
        target=Target.objects.create(id=plan.IDS['target'],project=project,name='Approved existing QNX 8 lab',kind='managed-lab')
        for role in pair:BuildRelease.objects.create(id=plan.IDS[role],target=target,label='Before defect source' if role=='before' else 'After corrected source',manifest=pair[role])
        audit(None,'production.executor.prepared',org,target.pk,application=plan.APPLICATION,engine=plan.ENGINE,ids=plan.IDS)

def check_bindings(pair=None,allow_unapproved=False):
    from control.models import User,Organization,Project,Target,BuildRelease,AuditEvent
    pair=pair or plan.manifest_pair(ops.SOURCE)
    owner=User.objects.get(pk=plan.IDS['custodian']);plan.require(not owner.is_active and not owner.has_usable_password() and not owner.is_superuser,'custodian_identity_changed')
    org=Organization.objects.get(pk=plan.IDS['organization']);project=Project.objects.get(pk=plan.IDS['project'])
    plan.require(org.active and project.active and project.organization_id==org.pk and str(project.created_by_id)==plan.IDS['custodian'] and not project.ai_enabled,'approved_project_changed')
    target=Target.objects.get(pk=plan.IDS['target'])
    plan.require(target.project_id==project.pk and target.kind=='managed-lab' and target.state!='quarantined','approved_target_changed')
    published=AuditEvent.objects.filter(action='production.executor.approved',object_id=str(target.pk)).exists()
    plan.require((allow_unapproved and not published and not target.approved and target.binding=='') or (target.approved and target.binding==str(target.pk)),'target_approval_changed')
    for role in pair:
        build=BuildRelease.objects.get(pk=plan.IDS[role]);plan.require(build.target_id==target.pk and build.manifest==pair[role] and
            ((allow_unapproved and not published and not build.approved and build.binding=='') or (build.approved and build.binding==str(build.pk))),'approved_build_changed')
    return target

def approved_plan():
    """Validate fixed executor custody from the root coordinator, without treating
    root as the executor UID or changing the worker's ownership policy.
    """
    from django.db import connection
    from executor_locking import install
    idle();target=check_bindings();install(connection,check_only=True)
    plan.require(target.state=='available','approved_target_not_available')
    account=pwd.getpwnam('resmgr-exec');uid=account.pw_uid
    expected=plan.registry()
    plan.require(json.loads(plan.read_owned(plan.CONFIG/'registry.json',uid,{0o600}))==expected,'approved_registry_binding_differs')
    plan.require(json.loads(plan.read_owned(plan.CONFIG/'target.json',uid,{0o600}))==plan.target_config(),'approved_target_configuration_differs')
    plan.require(plan.read_owned(plan.CONFIG/'ssh-config',uid,{0o600})==plan.ssh_config(),'approved_ssh_configuration_differs')
    plan.require(plan.digest(plan.read_owned(plan.CONFIG/'known-hosts',uid,{0o600}))==plan.KNOWN_HOSTS_SHA,'approved_host_identity_differs')
    pair=plan.manifest_pair(ops.SOURCE)
    for role,(_,expected_hash) in plan.MANIFESTS.items():
        path=plan.CONFIG/(role+'-deployment.json');raw=plan.read_owned(path,uid,{0o600})
        plan.require(plan.digest(raw)==expected_hash and json.loads(raw)==pair[role],'approved_manifest_identity_differs')
    for name in ['registry.json','target.json','ssh-config','known-hosts','before-deployment.json','after-deployment.json']:
        plan.require((plan.CONFIG/name).lstat().st_gid==account.pw_gid,'approved_resource_group_differs')
    journal=json.loads(ops.read(plan.STATE/'state.json',private=True))
    proof=json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True))
    plan.require(journal.get('kind')=='approved-production-qnx-executor-v1' and journal.get('application')==plan.APPLICATION and journal.get('ids')==plan.IDS and
        proof.get('passed') is True and proof.get('kind')=='actual-systemd-executor-probe' and proof.get('application')==plan.APPLICATION and
        proof.get('driver_revision')==journal.get('runtime_proof_driver',journal.get('driver_revision')) and
        all(proof.get('deployments',{}).get(role,{}).get('deployment_id')==pair[role]['deployment_id'] for role in pair),'approved_runtime_proof_differs')
    return {'status':'approved-existing-route','target_id':plan.IDS['target'],'project_id':plan.IDS['project'],
        'organization_id':plan.IDS['organization'],'before_build':plan.IDS['before'],'after_build':plan.IDS['after']}

def publish(driver):
    from django.db import transaction
    from django.utils import timezone
    from control.models import Target,BuildRelease,AuditEvent
    from control.security import audit
    proof=json.loads(ops.read(plan.STATE/'runtime-proof.json',private=True))
    pair=plan.manifest_pair(ops.SOURCE)
    from resmgrcheck.contracts import Profile,load
    plan.require(proof.get('passed') is True and proof.get('kind')=='actual-systemd-executor-probe' and
        proof.get('application')==plan.APPLICATION and proof.get('driver_revision')==driver and
        proof.get('database_grants_verified') is True and set(proof.get('deployments',{}))=={'before','after'} and
        all(proof['deployments'][role]['deployment_id']==pair[role]['deployment_id'] and proof['deployments'][role]['verified_files']==5 for role in pair),'runtime_probe_required')
    caps=proof.get('compiled_adapters',{})
    plan.require(set(caps)=={'sensor-v1','job-v1'} and all(set(Profile.parse(load(ops.SOURCE/'profiles'/(name+'.json'))).data['capabilities']['required'])<=set(caps[name+'-v1']) for name in ['sensor','job']),'required_capabilities_missing')
    with transaction.atomic():
        idle();target=check_bindings(allow_unapproved=True)
        Target.objects.select_for_update().get(pk=target.pk)
        if AuditEvent.objects.filter(action='production.executor.approved',object_id=str(target.pk)).exists():return
        target.approved=True;target.binding=str(target.pk);target.state='available';target.last_seen=timezone.now()
        target.inventory={'compiled_adapters':proof['compiled_adapters'],'observed_under':'actual resmgrcheck-executor.service',
            'deployments':proof['deployments'],'service_instance':'unknown until actual lifecycle run','SDK':'not exposed to executor'}
        target.save(update_fields=['approved','binding','state','last_seen','inventory'])
        for role in ['before','after']:BuildRelease.objects.filter(pk=plan.IDS[role]).update(approved=True,binding=plan.IDS[role])
        audit(None,'production.executor.approved',target.project.organization,target.pk,application=plan.APPLICATION,engine=plan.ENGINE,
            observed_runtime=True,deployments=proof['deployments'])

def descendants(parent):
    found=[];queue=[parent]
    while queue:
        pid=queue.pop()
        try:children=[int(value) for value in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
        except OSError:continue
        found.extend(children);queue.extend(children)
        plan.require(len(found)<=128,'executor_process_bound')
    return found

def collection_identity(uid,argv,cgroup,case_id,helper):
    try:
        words=shlex.split(os.fsdecode(argv[-2] if argv[-1]==b'' else argv[-1]))
        expected_uid=pwd.getpwnam('resmgr-exec').pw_uid
        index=argv.index(b'-F')
        return (uid==expected_uid and re.fullmatch(r'w[0-9a-f]{18}-timeout',case_id) is not None and
            any(line.endswith(':/system.slice/resmgrcheck-executor.service') for line in cgroup.splitlines()) and
            Path(os.fsdecode(argv[0])).name=='ssh' and argv[index+1]==os.fsencode(plan.CONFIG/'ssh-config') and
            b'resmgrcheck-lab' in argv and len(words)==4 and words==[helper,'read-run',case_id,words[3]] and
            words[3] in {'events.jsonl','status.json','recovery.jsonl','stderr.log'})
    except (ValueError,IndexError,TypeError):return False

def pause_collection(case_id,helper=None):
    main=int(ops.command(['systemctl','show','--value','--property=MainPID','resmgrcheck-executor.service']))
    for pid in descendants(main):
        fd=None
        try:
            fd=os.pidfd_open(pid);root=Path('/proc')/str(pid);argv=root.joinpath('cmdline').read_bytes().split(b'\0')
            group=root.joinpath('cgroup').read_text()
            if collection_identity(root.stat().st_uid,argv,group,case_id,helper):
                signal.pidfd_send_signal(fd,signal.SIGSTOP);return fd,pid
        except (OSError,ProcessLookupError):pass
        if fd is not None:os.close(fd)
    return None,None

def resume(fd):
    if fd is not None:
        try:signal.pidfd_send_signal(fd,signal.SIGCONT)
        except ProcessLookupError:pass
        finally:os.close(fd)

def target_read(run,name):
    # Fixed read-only observer under executor UID; never root SSH or a browser path.
    import shlex
    directory=run.build.manifest['directory'];plan.require(re.fullmatch('/data/resmgrcheck/b-[0-9a-f]{48}',directory),'native_directory_invalid')
    command=' '.join(shlex.quote(v) for v in [directory+'/targetctl','read-run',run.native_run_id+'-timeout',name])
    # read-run exit2 means not yet present. Do not log raw command/output/SSH detail.
    import subprocess
    result=subprocess.run(['/usr/sbin/runuser','-u','resmgr-exec','--','ssh','-F',str(plan.CONFIG/'ssh-config'),
        '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','resmgrcheck-lab',command],
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ops.ENV,timeout=8)
    plan.require(result.returncode in {0,2} and len(result.stdout)<=2*1024**2,'native_observer_unavailable')
    return result.stdout

def timed_pending(run):
    events=[]
    for raw in target_read(run,'events.jsonl').splitlines():
        try:events.append(json.loads(raw))
        except ValueError:break
    timed=[e for e in events if e.get('event')=='deadline' and e.get('data',{}).get('operation')=='timed']
    if not timed:return None
    found=[e for e in events if e.get('event')=='pending' and e.get('data',{}).get('client_pid')==timed[-1]['pid']]
    return found[-1] if found else None

def qualified_run(identifier,credentials):
    from control.models import Run
    plan.require(str(uuid.UUID(identifier))==identifier,'run_identity_invalid')
    run=Run.objects.select_related('build','access_session__code','project__organization').get(pk=identifier)
    plan.require(str(run.project_id)==plan.IDS['project'] and str(run.target_id)==plan.IDS['target'] and
        run.native_run_id=='w'+run.pk.hex[:18] and run.access_session_id and
        str(run.access_session.code.created_by_id)==credentials['account_id'] and str(run.build_id) in {plan.IDS['before'],plan.IDS['after']},'run_not_owned_by_acceptance')
    return run

def completed(run,expected):
    from control.storage import verify_inventory
    from resmgrcheck.artifacts import inspect_bundle
    from control.engine import run_path
    run.refresh_from_db();plan.require(run.state=='completed' and run.target_cleanup_verified,'native_cleanup_unproven')
    verify_inventory(run);bundle=inspect_bundle(run_path(run)/'cases/timeout/bundle')
    plan.require(bundle.result.data['verdict']==expected and bundle.status['cleanup_ok'] and not bundle.status['unresolved'],'canonical_verdict_or_cleanup_differs')
    from resmgrcheck.deployment import native_builds
    plan.require(bundle.plan.data['builds']==native_builds(run.build.manifest,'sensor-v1' if run.profile=='sensor' else 'job-v1'),'evidence_source_build_mismatch')
    return bundle

def observe(request,credentials,output,stop=None):
    from control.models import Run,AccessCode
    from control.engine import run_path
    run=qualified_run(request['run_id'],credentials);kind=request['action'];fd=None
    plan.require((kind=='recover' and run.profile=='sensor' and str(run.build_id)==plan.IDS['before'] and run.fixture_mode=='ignore-unblock') or
        (kind=='revoke-observe' and run.profile=='job' and str(run.build_id)==plan.IDS['after']),'observation_scope_invalid')
    def response(stage,value):
        path=output/('response-'+request['request_id']+'-'+stage+'.json');temporary=output/('.response-'+uuid.uuid4().hex)
        ops.new_file(temporary,(json.dumps(value)+'\n').encode(),owner=(output.stat().st_uid,output.stat().st_gid))
        os.link(temporary,path,follow_symlinks=False);temporary.unlink();ops.fsync_directory(output)
    try:
        pending=None;deadline=time.monotonic()+30;supervisor=None
        while time.monotonic()<deadline:
            plan.require(stop is None or not stop.is_set(),'acceptance_observation_interrupted')
            run.refresh_from_db()
            if run.state=='running':
                pending=timed_pending(run)
                if pending:
                    status=target_read(run,'status.json')
                    if status:supervisor=json.loads(status)['supervisor_pid']
                    fd,pid=pause_collection(run.native_run_id+'-timeout',run.build.manifest['directory']+'/targetctl')
                    if fd is not None and supervisor:break
                    resume(fd);fd=None
            time.sleep(.03)
        plan.require(fd is not None and pending and supervisor,'exact_pending_collection_not_observed')
        response('ready',{'passed':True,'timed_pending_observed':True,'collection_PID_pinned':True})
        partial_hash=None;uncertain=False;queued=None;revoked=False;deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            plan.require(stop is None or not stop.is_set(),'acceptance_observation_interrupted')
            run.refresh_from_db()
            if kind=='recover' and run.state=='launch_uncertain':
                uncertain=True;partial=run_path(run)/'cases/timeout/partial-events.jsonl'
                if partial.is_file():partial_hash=plan.digest(plan.read_owned(partial,pwd.getpwnam('resmgr-exec').pw_uid,{0o600,0o640},2*1024**2))
            if kind=='revoke-observe' and not revoked:
                revoked=AccessCode.objects.get(pk=run.access_session.code_id).revoked_at is not None
                if revoked:
                    candidates=list(Run.objects.filter(access_session_id=run.access_session_id,state='queued',created_at__gt=run.created_at))
                    plan.require(len(candidates)==1,'exact_revoked_queued_job_required');queued=qualified_run(str(candidates[0].pk),credentials)
                    resume(fd);fd=None
            if run.state=='completed':break
            plan.require(run.state not in {'blocked','rejected','cancelled'},'observed_run_failed_closed')
            time.sleep(.1)
        bundle=completed(run,'FAIL' if kind=='recover' else 'PASS')
        if kind=='recover':
            plan.require(uncertain and partial_hash and bundle.status['supervisor_pid']==supervisor,'same_ID_same_supervisor_recovery_unproven')
            plan.require({'cancellation_not_completed','pending_state_not_released'}<=set(bundle.result.data['reasons']),'intentional_defect_reasons_changed')
            matches=[path for path in (run_path(run)/'history').rglob('partial-events.jsonl') if path.is_file() and
                plan.digest(plan.read_owned(path,pwd.getpwnam('resmgr-exec').pw_uid,{0o400,0o440,0o600,0o640},2*1024**2))==partial_hash]
            plan.require(matches and run.incidents,'partial_evidence_not_preserved')
            value={'passed':True,'native_run_id':run.native_run_id,'same_supervisor':True,'launch_uncertain_observed':True,
                'partial_SHA256':partial_hash,'partial_evidence_preserved':True,'canonical_verdict':'FAIL','cleanup_verified':True,
                'fault':'SIGSTOP exact pidfd-pinned executor collection SSH child; engine timeout/reap; collect same ID after lease expiry'}
        else:
            plan.require(revoked and queued is not None,'live_revocation_not_observed')
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                queued.refresh_from_db()
                if queued.state=='rejected':break
                time.sleep(.1)
            plan.require(queued.state=='rejected' and queued.error_code=='actor_authorization_revoked' and queued.started_at is None and not run_path(queued).exists() and not queued.target_cleanup_verified,'revoked_queued_job_not_withheld')
            code=AccessCode.objects.get(pk=run.access_session.code_id)
            plan.require(run.started_at<code.revoked_at<run.finished_at,'revocation_outside_live_collection')
            value={'passed':True,'live_run_id':str(run.pk),'queued_run_id':str(queued.pk),'timed_pending_observed':True,
                'revoked_during_live_collection':True,'live_canonical_verdict':'PASS','live_cleanup_verified':True,
                'queued_state':'rejected','queued_native_launch':False,'queued_verdict':'NOT_RUN; no native evidence claimed'}
        response('complete',value);return value
    finally:resume(fd)

def acceptance_run(driver):
    from django.db import connections
    from control.models import AuditEvent,Run
    from control.jobs import ACTIVE
    selected=approved_plan()
    plan.require(selected.get('target_id')==plan.IDS['target'] and selected.get('before_build')==plan.IDS['before'] and selected.get('after_build')==plan.IDS['after'],'exact_approved_native_plan_required')
    previous=plan.STATE/'native-result.json'
    if previous.exists():
        result=json.loads(ops.read(previous,private=True));plan.require(result.get('driver_revision')==driver,'native_result_driver_differs')
        if result.get('passed') is True:
            for row in result['native_runs']:completed(Run.objects.get(pk=row['web_run_id']),'FAIL' if row['role']=='before' else 'PASS')
            return result
    # Reconcile only our intents whose append-only creation audit proves custody.
    for path in plan.STATE.glob('native-*.intent.json'):
        intent=json.loads(ops.read(path,private=True));identifier=uuid.UUID(intent['acceptance_id'])
        cleanup=plan.STATE/('native-'+identifier.hex+'.cleanup.json')
        if cleanup.exists():continue
        event=AuditEvent.objects.select_related('actor').filter(action='https.acceptance.created',details__acceptance_id=str(identifier)).first()
        if event:ops.record(cleanup,acceptance.close({'acceptance_id':str(identifier),'account_id':str(event.actor_id),'username':event.actor.username}))
    identifier=uuid.uuid4();owner=pwd.getpwuid(ops.SOURCE.stat().st_uid)
    output=ops.SOURCE/'.local/web/evidence'/('production-native-'+identifier.hex);output.mkdir(mode=0o700);os.chown(output,owner.pw_uid,owner.pw_gid)
    ops.record(plan.STATE/('native-'+identifier.hex+'.intent.json'),{'acceptance_id':str(identifier),'application':plan.APPLICATION,'driver_revision':driver})
    credentials=acceptance.bootstrap(identifier,selected);stop=threading.Event();proofs=[];errors=[];seen=set()
    def monitor():
        try:
            while not stop.is_set():
                for path in output.glob('request-*.json'):
                    name=path.name
                    if name in seen:continue
                    request=json.loads(plan.read_owned(path,owner.pw_uid,{0o600},4096))
                    plan.require(set(request)=={'request_id','action','run_id'} and re.fullmatch('[0-9a-f]{32}',request['request_id']) and
                        name=='request-'+request['request_id']+'.json' and request['action'] in {'recover','revoke-observe'},'observation_request_invalid')
                    plan.require(len(seen)<4 and request['action'] not in seen,'observation_request_duplicate')
                    seen.add(name);seen.add(request['action']);proofs.append(observe(request,credentials,output,stop))
                stop.wait(.025)
        except BaseException as error:errors.append(type(error).__name__)
        finally:connections.close_all()
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        ops.command(['/usr/sbin/runuser','-u',owner.pw_name,'--',ops.SOURCE/'.local/browser-test/bin/python','-I','-B',
            ops.HERE/'executor_native_browser.py','--out',output],data=json.dumps(credentials).encode(),timeout=1200)
        stop.set();thread.join(timeout=10);plan.require(not thread.is_alive() and not errors and len(proofs)==2,'native_observations_incomplete')
        report=json.loads(plan.read_owned(output/'browser-report.json',owner.pw_uid,{0o600}))
        plan.require(report.get('passed') is True and report.get('native',{}).get('new_native_executions')==3,'native_browser_unproven')
        runs=[row for row in report['runs'] if row['status']=='passed'];plan.require(len(runs)==3,'exact_native_case_count')
        native=[]
        for role,row in zip(['before','after','job'],runs):
            run=qualified_run(row['web_run_id'],credentials);bundle=completed(run,'FAIL' if role=='before' else 'PASS')
            native.append({'role':role,'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'verdict':bundle.result.data['verdict'],
                'bundle_id':bundle.manifest.data['bundle_id'],'cleanup_verified':True,'download_verified':row.get('download_verified') is True})
        plan.require(all(row['download_verified'] for row in native),'evidence_download_unproven')
        from resmgrcheck.workflow import compare_executions
        from control.engine import run_path
        before,after=[qualified_run(row['web_run_id'],credentials) for row in native[:2]]
        comparison=compare_executions(run_path(before),run_path(after));plan.require(comparison['label']=='fixed' and not comparison['fixture_mode_changed'],'canonical_source_comparison_not_fixed')
        result={'passed':True,'native_passed':True,'driver_revision':driver,'application':plan.APPLICATION,
            'native_runs':native,'observations':proofs,'browser_evidence':str(output),'comparison':'fixed',
            'customer_runner':'disabled','AI':'disabled','independent_UAT':'pending'}
    except BaseException as error:
        failure={'driver_revision':driver,'failed_check':str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z0-9_]{1,100}',str(error)) else type(error).__name__,
            'observer_errors':errors,'browser_failed_step':'unavailable'}
        report_path=output/'browser-report.json'
        if report_path.exists():
            try:
                step=json.loads(plan.read_owned(report_path,owner.pw_uid,{0o600})).get('failed_step','unavailable')
                if isinstance(step,str) and re.fullmatch('[A-Za-z0-9_-]{1,100}',step):failure['browser_failed_step']=step
            except (ValueError,OSError):pass
        ops.record(plan.STATE/'native-failure.json',failure);raise
    finally:
        stop.set();thread.join(timeout=10)
        cleanup=acceptance.close(credentials);ops.record(plan.STATE/('native-'+identifier.hex+'.cleanup.json'),cleanup)
        ops.new_file(output/'operator-cleanup.json',(json.dumps(cleanup,indent=2)+'\n').encode(),owner=(owner.pw_uid,owner.pw_gid))
    plan.require(not cleanup['own_native_work_still_active'],'native_work_still_active_preserved')
    result['cleanup']=cleanup;ops.record(previous,result);return result

def rehearse():
    # Lock the rows used by enqueue and claim throughout the idle-only rehearsal.
    # A concurrent dashboard request cannot race into the stopped executor.
    from django.db import transaction
    from control.models import ExecutorSlot
    with transaction.atomic():
        for name in ['dispatch','private-qnx']:
            ExecutorSlot.objects.get_or_create(name=name)
            ExecutorSlot.objects.select_for_update().get(name=name)
        idle();check_bindings()
        ops.command(['systemctl','stop','resmgrcheck-executor.service'],timeout=30)
        ops.command(['systemctl','start','resmgrcheck-executor.service'],timeout=45)
        plan.require(ops.command(['systemctl','show','--value','--property=ActiveState','resmgrcheck-executor.service']).strip()==b'active','executor_restart_not_active')
    return {'passed':True,'idle_executor_stop_start':'passed','full_application_rollback':'not_run'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['prepare','publish','acceptance','idle','verify','rehearse','resume-preflight'],required=True);parser.add_argument('--driver-revision',required=True);args=parser.parse_args()
    try:
        ops.DIAGNOSTIC=plan.STATE/'operator-diagnostic.log';ops.source_check(plan.APPLICATION,args.driver_revision);acceptance.load_application(plan.APPLICATION)
        if args.phase=='prepare':prepare();result={'passed':True,'approved':False}
        elif args.phase=='publish':publish(args.driver_revision);result={'passed':True,'approved':True}
        elif args.phase=='acceptance':result=acceptance_run(args.driver_revision)
        elif args.phase=='idle':idle();result={'passed':True}
        elif args.phase=='resume-preflight':approved_plan();result={'passed':True,'read_only':True}
        elif args.phase=='rehearse':result=rehearse()
        else:
            idle();check_bindings();result=json.loads(ops.read(plan.STATE/'native-result.json',private=True));plan.require(result.get('passed') is True,'native_result_not_verified')
            from control.models import Run
            for row in result['native_runs']:completed(Run.objects.get(pk=row['web_run_id']),row['verdict'])
        print(json.dumps(result))
    except BaseException as error:
        failure={'passed':False,'phase':args.phase,'driver_revision':args.driver_revision,
            'failed_check':str(error) if isinstance(error,(ValueError,ops.CheckFailed)) and re.fullmatch('[a-z0-9_]{1,100}',str(error)) else type(error).__name__,'secrets_printed':False}
        if os.geteuid()==0 and plan.STATE.is_dir():
            try:ops.record(plan.STATE/'operator-failure.json',failure)
            except (ValueError,OSError,ops.CheckFailed):pass
        print(json.dumps(failure));raise SystemExit(1) from None
