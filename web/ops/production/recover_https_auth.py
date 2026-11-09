#!/usr/bin/env python3
"""One operator command: immutable544 auth correction, private qualification, HTTPS.

Default is read-only. Apply touches only dedicated releases/pointer/static assets,
protected own receipts, own web/socket, own backup and the reviewed HTTPS workflow.
No migrations, credential replacement, unit edits, native grants or route provisioning.
"""
import argparse,http.client,json,os,re,secrets,shutil,signal,socket,stat,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as https
import upgrade_private as previous
from https_checks import require,CheckFailed
release=previous.release;p=previous.p
ACTIVE='544f22c174ad48e1c8d741db0afdd3bf5b54f947'
FAILED_DRIVER='cf15209ba98c7891fe2ab991868b5c06eed57de3'
MANIFEST='.https-auth-release.json'
SETTING=b"# Production is reachable only through the private Unix socket. Dedicated Nginx\n# overwrites this header with its original peer and strips forwarded-IP chains.\nALLAUTH_TRUSTED_CLIENT_IP_HEADER = 'X-Real-IP' if ENVIRONMENT == 'production' else None\n"
ANCHOR=b"ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if ENVIRONMENT == 'production' else 'http'\n"

def scope(revision,driver):
    https.source_check(revision,driver)
    https.git('merge-base','--is-ancestor',ACTIVE,revision)
    changed=https.git('diff','--name-only',ACTIVE,revision).decode().splitlines()
    require(all(name=='web/resmgr_web/settings.py' or name.startswith(('docs/web/','web/tests/','web/ops/production/')) for name in changed),'auth_upgrade_scope_exceeded')
    frozen=['web/ops/production/runtime.py','web/ops/production/prepare.py',*['web/ops/production/'+name for name in p.UNITS]]
    require(not https.git('diff','--name-only',ACTIVE,revision,'--',*frozen).strip(),'auth_upgrade_runtime_or_units_changed')
    old=https.git('show',ACTIVE+':web/resmgr_web/settings.py');new=https.git('show',revision+':web/resmgr_web/settings.py')
    require(old.count(ANCHOR)==1 and new==old.replace(ANCHOR,ANCHOR+SETTING),'auth_upgrade_settings_differs')

def identity(revision):
    return {'kind':'resmgrcheck-https-auth-release','from_revision':ACTIVE,'revision':revision,
        'source':str(p.SOURCE),'venv':previous.identity(ACTIVE)['venv']}

def validate(path,revision):
    release.owned_directory(path)
    require(p.protected_json(path/MANIFEST)==identity(revision),'auth_release_manifest_differs')
    release.check_clean(path,revision,{MANIFEST,'.venv'});release.check_venv(path/'.venv',Path(identity(revision)['venv']))

def stage(revision,new):
    if new.exists() or new.is_symlink():validate(new,revision);return
    require(shutil.disk_usage(p.OPT).free>=2*1024**3,'keep_two_GiB_free')
    # Interrupted incomplete attempts are preserved; never overwrite/adopt them.
    attempt=new.parent/('.https-auth-stage-'+revision+'-'+secrets.token_hex(12))
    p.clone(attempt,revision);release.check_clean(attempt,revision,set());p.public_code_permissions(attempt)
    (attempt/'.venv').symlink_to(Path(identity(revision)['venv']),target_is_directory=True)
    p.write(attempt/MANIFEST,json.dumps(identity(revision),sort_keys=True)+'\n');validate(attempt,revision)
    release.publish_new_release(attempt,new);https.fsync_directory(new.parent)

def private_ready():
    for attempt in range(6):
        connection=http.client.HTTPConnection('localhost',timeout=4);stream=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);stream.settimeout(4)
        try:
            stream.connect('/run/resmgrcheck-web/application.sock');connection.sock=stream
            connection.request('GET','/readyz/',headers={'Host':https.HOST,'X-Forwarded-Proto':'https'})
            response=connection.getresponse();body=response.read(1025)
            if response.status==200 and json.loads(body)=={'status':'ready'}:return
        except (OSError,ValueError,http.client.HTTPException):pass
        finally:connection.close();stream.close()
        if attempt<5:time.sleep(1)
    raise CheckFailed('private_auth_release_readiness_failed')

def web(action):https.command(['systemctl',action,'resmgrcheck-web.socket','resmgrcheck-web.service'],timeout=60)

def original_http(state):
    targets=[('site',https.SITE,https.site_config(state['application_revision']).encode(),0o644),
        ('http',https.HTTP,https.http_config().encode(),0o644),('hook',https.HOOK,https.renewal_hook().encode(),0o755)]
    https.verify_original_http(state,targets,https.Client(address='127.0.0.1'))

def bind_https(revision,driver):
    with https.locked():
        path=https.STATE/'state.json';state=json.loads(https.read(path,private=True))
        if state.get('application_revision')==revision and state.get('driver_revision')==driver:return
        require(state.get('application_revision')==ACTIVE and state.get('driver_revision')==FAILED_DRIVER and
            state.get('phase')=='rolled_back_after_failure' and state.get('failure')=='command_failed_python','expected_failed_auth_deployment_required')
        require(state.get('after')==https.recorded_candidate_hashes(FAILED_DRIVER,ACTIVE),'failed_auth_candidate_hashes_differ')
        original_http(state)
        history=https.STATE/('driver-'+FAILED_DRIVER+'.json')
        if history.exists():require(json.loads(https.read(history,private=True))==state,'auth_driver_history_differs')
        else:https.new_file(history,(json.dumps(state,sort_keys=True,indent=2)+'\n').encode())
        state.update(application_revision=revision,driver_revision=driver,phase='prepared_after_immutable_auth_correction',
            after={'site':https.digest(https.site_config(revision).encode()),'http':https.digest(https.http_config().encode()),'hook':https.digest(https.renewal_hook().encode())},
            rollback_verified=False)
        https.record(path,state)

def snapshot(journal,path,new):
    if journal.get('backup_verified'):
        require(previous.backup_binding(journal['backup']['archive'],path,fresh=False)==journal['backup'],'auth_backup_binding_differs');return
    if not journal.get('backup'):
        require(https.command(['systemctl','show','--value','--property=ActiveState','resmgrcheck-backup.service']).strip() in {b'inactive',b'failed'},'dedicated_backup_in_progress_retry')
        before=set(p.BACKUP.glob('snapshot_*.rmc'))
        print(json.dumps({'step':'dedicated_pre_auth_upgrade_backup','status':'running'}),flush=True)
        https.command(['systemctl','start','resmgrcheck-backup.service'],timeout=300,progress='dedicated_pre_auth_upgrade_backup')
        fresh=set(p.BACKUP.glob('snapshot_*.rmc'))-before
        require(len(fresh)==1,'exactly_one_new_auth_backup_required')
        journal['backup']=previous.backup_binding(str(fresh.pop()),path);https.record(path,journal)
    require(previous.backup_binding(journal['backup']['archive'],path,fresh=False)==journal['backup'],'auth_backup_binding_differs')
    print(json.dumps({'step':'isolated_pre_auth_upgrade_restore','status':'running'}),flush=True)
    previous.verify_backup(new,journal['backup']);journal['backup_verified']=True;https.record(path,journal)

def apply(revision,driver,rollback=False):
    https.require_root();os.umask(0o027);scope(revision,driver)
    for directory in [p.OPT,p.OPT/'releases',https.STATE]:https.directory(directory)
    with release.release_lock():
        journal_path=https.STATE/'auth-upgrade.json';binding={**identity(revision),'driver_revision':driver}
        if journal_path.exists():
            journal=json.loads(https.read(journal_path,private=True));require(all(journal.get(k)==v for k,v in binding.items()),'another_auth_upgrade_recorded')
        else:
            require(not rollback,'no_auth_upgrade_to_rollback');journal={**binding,'phase':'prepared'};https.record(journal_path,journal)
        old=p.OPT/'releases'/ACTIVE;new=p.OPT/'releases'/revision;current=p.OPT/'current'
        release.check_current(current,old,new);previous.validate(old,ACTIVE)
        for name in p.UNITS:
            require(https.read(p.UNIT_ROOT/name)==(old/'web/ops/production'/name).read_bytes(),'auth_upgrade_installed_unit_differs')
            require(not https.command(['systemctl','show','--value','--property=DropInPaths',name]).strip(),'auth_upgrade_unit_overrides_require_review')
        for name in ['application-key','mfa-key','backup-key']:p.check_private_file(p.CONFIG/'keys'/name)
        for unit in ['resmgrcheck-executor.service','resmgrcheck-ai.service']:
            require(https.command(['systemctl','show','--value','--property=ActiveState',unit]).strip() in {b'inactive',b'failed'},'private_workers_must_remain_inactive')
        if rollback:
            validate(new,revision);https.apply(revision,driver,True,False)
            web('stop');release.check_current(current,old,new);release.switch_current(current,old);web('start');private_ready();https.units_and_runtime(ACTIVE)
            journal['phase']='rolled_back';https.record(journal_path,journal);print(json.dumps({'auth_upgrade_rollback':'passed','private_revision':ACTIVE,'keys_database_units_preserved':True}));return
        stage(revision,new)
        state=json.loads(https.read(https.STATE/'state.json',private=True))
        if state.get('phase')=='verified' and state.get('application_revision')==revision and state.get('driver_revision')==driver:
            require(current.resolve()==new,'verified_auth_release_pointer_differs');https.apply(revision,driver);return
        original_http(state);snapshot(journal,journal_path,new)
        try:
            web('stop');release.check_current(current,old,new);release.switch_current(current,new)
            journal['phase']='private_pointer_switched';https.record(journal_path,journal)
            raw=https.command([str(new/'.venv/bin/python'),'-I',https.HERE/'auth_release_runtime.py','--release',revision],timeout=120)
            require(json.loads(raw).get('passed') is True,'auth_release_runtime_unproven')
            web('start');private_ready();https.units_and_runtime(revision)
            journal['phase']='private_runtime_verified';https.record(journal_path,journal)
            bind_https(revision,driver);https.apply(revision,driver)
            journal['phase']='HTTPS_browser_workflow_completed';https.record(journal_path,journal)
        except BaseException as error:
            journal['failure']=str(error) if isinstance(error,CheckFailed) else type(error).__name__
            https.record(journal_path,journal)
            try:
                state=json.loads(https.read(https.STATE/'state.json',private=True));original_http(state)
                release.check_current(current,old,new);web('stop');release.switch_current(current,old);web('start');private_ready();https.units_and_runtime(ACTIVE)
                journal['phase']='failed_original_private_restored';https.record(journal_path,journal)
            except BaseException:
                journal['phase']='recovery_requires_operator_review';https.record(journal_path,journal)
                raise CheckFailed('auth_upgrade_failed_recovery_requires_review') from None
            raise CheckFailed('auth_upgrade_failed_original_private_restored') from None

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--release',required=True);parser.add_argument('--driver-revision',required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    def interrupted(signum,frame):raise CheckFailed('operator_auth_upgrade_interrupted')
    if args.apply:signal.signal(signal.SIGTERM,interrupted)
    try:
        if args.apply:apply(args.release,args.driver_revision,args.rollback)
        else:
            scope(args.release,args.driver_revision)
            print(json.dumps({'mode':'read-only immutable authentication recovery plan','from_revision':ACTIVE,'release':args.release,'driver_revision':args.driver_revision,
                'new_release_directory':str(p.OPT/'releases'/args.release),'original_release_preserved':True,'fresh_backup_and_isolated_restore':True,
                'migrations_keys_units_native_grants_changed':False,'dedicated_web_restart_required':True,'HTTPS_acceptance_after_private_runtime':True,'root_required':True}))
    except BaseException as error:
        print(json.dumps({'passed':False,'failed_check':str(error) if isinstance(error,CheckFailed) else type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
