#!/usr/bin/env python3
"""Exact evidence-story release and compatible application rollback drill. Default read-only; apply requires local root."""
import argparse,json,os,re,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as ops
import recover_https_auth as auth
from https_checks import require,CheckFailed
ACTIVE='dfe1060e6a517b686d4948f8cea2fc848fcd0956'
CANDIDATE='7ecb81231cbce91dfe866d515a6458073b0d0e0e'
STATE=Path('/var/lib/resmgrcheck/private/operator/evidence-story-release')
STEP='source_scope'
APP_FILES={
    'resmgrcheck/reports.py', 'resmgrcheck/story.py',
    'web/control/templates/control/partials/case.html',
    'web/control/templatetags/ui.py',
}
EXTRA_FILES={'README.md','scripts/configure-target.py','tests/host/test_story.py',
             'tests/host/test_target_setup.py','tests/jury/prepare_review.py'}


def scope(driver):
    require(re.fullmatch('[0-9a-f]{40}',driver),'exact_driver_required')
    ops.git('merge-base','--is-ancestor',CANDIDATE,driver)
    ops.git('merge-base','--is-ancestor',driver,'HEAD')
    require(not ops.git('status','--porcelain','--untracked-files=no').strip(),'tracked_source_changes')
    require(not ops.git('diff','--name-only',driver,'HEAD','--','web/ops/production').strip(),'driver_code_differs')
    changed=ops.git('diff','--name-only',ACTIVE,CANDIDATE).decode().splitlines()
    require({p for p in changed if p.startswith(('web/control/','web/resmgr_web/','resmgrcheck/','native/','profiles/'))}==APP_FILES,'application_scope_differs')
    require(all(p in APP_FILES or p in EXTRA_FILES or p.startswith(('docs/','web/tests/','web/ops/production/')) for p in changed),'release_scope_exceeded')
    require(not ops.git('diff','--name-only',ACTIVE,CANDIDATE,'--','web/requirements.lock','web/ops/gunicorn.conf.py','web/ops/production/runtime.py','web/ops/production/resmgrcheck-*').strip(),'runtime_or_units_changed')

def site_bytes(revision):return ops.site_config(revision).encode()

def validate_site():
    require(ops.ENABLED.is_symlink() and ops.ENABLED.resolve()==ops.SITE,'enabled_site_differs')
    require(ops.read(ops.SITE) in {site_bytes(ACTIVE),site_bytes(CANDIDATE)},'unknown_site_configuration')
    require(ops.read(ops.HTTP)==ops.http_config().encode() and ops.read(ops.HOOK)==ops.renewal_hook().encode(),'http_or_hook_differs')

def health(revision):
    auth.private_ready();ops.units_and_runtime(revision)
    status,_,body=ops.Client().request('/readyz/')
    require(status==200 and json.loads(body)=={'status':'ready'},'public_readiness_failed')
    status,_,body=ops.Client().request('/static/control/app.css')
    expected=ops.static_asset(Path('/var/lib/resmgrcheck/static')/revision/'control/app.css')
    require(status==200 and ops.digest(body)==ops.digest(expected),'public_static_identity_differs')

def idle(revision):
    # Fresh process for each release; never reuse Django modules across pointers.
    import acceptance_operator as acceptance
    acceptance.load_application(revision)
    from control.models import Run,ExecutorSlot
    from control.jobs import ACTIVE as states
    require(not Run.objects.filter(state__in=states).exists() and not ExecutorSlot.objects.filter(run__isnull=False).exists(),'native_work_requires_reconciliation')

def runtime(revision):
    idle(revision)
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from control.management.commands.private_release import assets
    require(not MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes()),'unexpected_migrations')
    assets(revision)
    print(json.dumps({'passed':True,'revision':revision,'migrations_applied':False,'assets_verified':True}))

def helper(flag,revision,driver):
    raw=ops.command([str(ops.OPT/'releases'/revision/'.venv/bin/python'),'-I','-B',Path(__file__).resolve(),flag,'--revision',revision,'--driver-revision',driver],timeout=1800,progress=flag)
    require(json.loads(raw.splitlines()[-1]).get('passed') is True,'release_helper_failed')

def stage():
    old=ops.OPT/'releases'/ACTIVE;new=ops.OPT/'releases'/CANDIDATE
    auth.validate(old,ACTIVE);auth.stage(CANDIDATE,new)
    return old,new

def restore(old,new,journal,path):
    # Only exact owned states; never overwrite another operator's configuration.
    validate_site();auth.release.check_current(ops.OPT/'current',old,new)
    if (ops.OPT/'current').resolve()==old and ops.read(ops.SITE)==site_bytes(ACTIVE):
        # A queue race caught before pointer activation must not interrupt native work.
        auth.web('start');health(ACTIVE)
        if journal['executor_before']=='active':ops.command(['systemctl','start','resmgrcheck-executor.service'])
        journal['phase']='original_restored';ops.record(path,journal);return
    auth.web('stop');ops.command(['systemctl','stop','resmgrcheck-executor.service'])
    ops.replace_owned(ops.SITE,site_bytes(ACTIVE),ops.read(ops.SITE))
    ops.command(['nginx','-t']);ops.command(['systemctl','reload','nginx.service'])
    auth.release.switch_current(ops.OPT/'current',old);auth.web('start');health(ACTIVE)
    if journal['executor_before']=='active':ops.command(['systemctl','start','resmgrcheck-executor.service'])
    journal['phase']='original_restored';ops.record(path,journal)

def apply(driver):
    global STEP
    ops.require_root();scope(driver);os.umask(0o077)
    with auth.release.release_lock(),ops.locked():
        ops.directory(STATE.parent,0o700)
        if not STATE.exists():STATE.mkdir(mode=0o700)
        ops.directory(STATE,0o700);ops.DIAGNOSTIC=STATE/'diagnostic.log'
        path=STATE/'state.json';binding={'kind':'immutable-evidence-story-release','from_revision':ACTIVE,'revision':CANDIDATE,'driver_revision':driver}
        STEP='original_and_candidate_validation';old,new=stage()
        auth.release.check_current(ops.OPT/'current',old,new);validate_site()
        for unit in auth.p.UNITS:
            require(ops.read(auth.p.UNIT_ROOT/unit)==(old/'web/ops/production'/unit).read_bytes(),'canonical_unit_differs')
            require(not ops.command(['systemctl','show','--value','--property=DropInPaths',unit]).strip(),'unknown_unit_override')
        if path.exists():
            journal=json.loads(ops.read(path,private=True));require(all(journal.get(k)==v for k,v in binding.items()),'another_release_recorded')
        else:
            require((ops.OPT/'current').resolve()==old and ops.read(ops.SITE)==site_bytes(ACTIVE),'original_pointer_or_site_differs')
            health(ACTIVE);helper('--idle',ACTIVE,driver)
            before=ops.command(['systemctl','is-active','resmgrcheck-executor.service']).decode().strip()
            require(before=='active','executor_baseline_differs')
            journal={**binding,'phase':'prepared','executor_before':before};ops.new_file(path,(json.dumps(journal)+'\n').encode())
        if journal['phase']=='verified':
            require(journal.get('rollback_verified') is True,'rollback_receipt_missing')
            require((ops.OPT/'current').resolve()==new and ops.read(ops.SITE)==site_bytes(CANDIDATE),'verified_release_binding_differs')
            health(CANDIDATE);print(json.dumps({'passed':True,'revision':CANDIDATE,'reused_completed_release':True}));return
        if journal['phase'] not in {'prepared','original_restored'}:
            STEP='interrupted_activation_restore';restore(old,new,journal,path)
        unrelated=ops.unrelated_snapshot()
        STEP='fresh_backup_and_isolated_restore';auth.snapshot(journal,path,new)
        try:
            # Journal before stopping either service, so every interruption is recoverable.
            journal['phase']='activation_started';ops.record(path,journal)
            STEP='quiesce_web_and_executor';auth.web('stop')
            helper('--idle',ACTIVE,driver)
            ops.command(['systemctl','stop','resmgrcheck-executor.service'])
            helper('--idle',ACTIVE,driver)
            STEP='immutable_pointer_and_assets';auth.release.switch_current(ops.OPT/'current',new)
            helper('--runtime',CANDIDATE,driver)
            auth.web('start');auth.private_ready();ops.units_and_runtime(CANDIDATE)
            STEP='exact_static_alias_activation';ops.replace_owned(ops.SITE,site_bytes(CANDIDATE),site_bytes(ACTIVE))
            require(ops.unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
            ops.command(['nginx','-t']);ops.command(['systemctl','reload','nginx.service']);health(CANDIDATE)
            ops.command(['systemctl','start','resmgrcheck-executor.service'])
            STEP='authenticated_browser_acceptance';helper('--acceptance',CANDIDATE,driver)
            require(ops.unrelated_snapshot()==unrelated,'unrelated_configuration_changed')
            STEP='compatible_application_rollback_drill';rollback_drill(old,new,journal,path,driver)
            health(CANDIDATE);journal['phase']='verified';ops.record(path,journal)
            print(json.dumps({'passed':True,'revision':CANDIDATE,'driver_revision':driver,'HTTPS_and_browser':'passed','native_acceptance':'W036 retained; not rerun','protected_state':str(path),'full_application_rollback':'passed','independent_UAT':'pending'}))
        except BaseException:
            STEP='restore_original_after_failure'
            try:restore(old,new,journal,path)
            except BaseException:raise CheckFailed('release_failed_restore_requires_operator_review') from None
            raise CheckFailed('release_failed_original_restored') from None

def rollback_drill(old,new,journal,path,driver):
    # Quiesce before each compatibility switch. This release has no migrations,
    # dependency, unit, authorization or engine changes. Keep the live DB intact.
    auth.web('stop');helper('--idle',CANDIDATE,driver)
    ops.command(['systemctl','stop','resmgrcheck-executor.service'])
    helper('--idle',CANDIDATE,driver)
    journal['phase']='rollback_started';ops.record(path,journal)
    restore(old,new,journal,path)
    helper('--acceptance-rollback',ACTIVE,driver)
    journal['phase']='rollback_browser_verified';ops.record(path,journal)
    auth.web('stop');helper('--idle',ACTIVE,driver)
    ops.command(['systemctl','stop','resmgrcheck-executor.service'])
    helper('--idle',ACTIVE,driver)
    journal['phase']='reactivation_started';ops.record(path,journal)
    auth.release.switch_current(ops.OPT/'current',new)
    helper('--runtime',CANDIDATE,driver)
    auth.web('start');auth.private_ready();ops.units_and_runtime(CANDIDATE)
    ops.replace_owned(ops.SITE,site_bytes(CANDIDATE),site_bytes(ACTIVE))
    ops.command(['nginx','-t']);ops.command(['systemctl','reload','nginx.service'])
    health(CANDIDATE)
    if journal['executor_before']=='active':ops.command(['systemctl','start','resmgrcheck-executor.service'])
    helper('--acceptance-final',CANDIDATE,driver)
    journal['rollback_verified']=True;ops.record(path,journal)


def acceptance(revision,driver,label='candidate-before-rollback'):
    import acceptance_operator as a
    # UI qualification only; no native selection, start or approval changes.
    a.native_plan=lambda:{'status':'not_requested','reason':'UI-only release; W036 native evidence retained'}
    state=STATE/label
    if not state.exists():state.mkdir(mode=0o700)
    ops.directory(state,0o700)
    a.run(revision,driver,state)
    report=json.loads(ops.read(state/'acceptance-report.json',private=True))
    require(report.get('browser_passed') is True and report.get('administrator_password')=='passed' and report.get('access_codes')=='passed' and report.get('temporary_account_disabled') is True and report.get('temporary_codes_revoked') is True and report.get('existing_users_changed') is False,'browser_acceptance_unproven')
    print(json.dumps({'passed':True,'browser_acceptance':'passed','native_executions':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--driver-revision',required=True);parser.add_argument('--revision',default=CANDIDATE)
    for flag in ['apply','idle','runtime','acceptance','acceptance-rollback','acceptance-final']:parser.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    try:
        require(args.revision in {ACTIVE,CANDIDATE},'unreviewed_revision')
        if args.idle:idle(args.revision);print(json.dumps({'passed':True}))
        elif args.runtime:runtime(args.revision)
        elif args.acceptance:acceptance(args.revision,args.driver_revision)
        elif args.acceptance_rollback:acceptance(args.revision,args.driver_revision,'rollback')
        elif args.acceptance_final:acceptance(args.revision,args.driver_revision,'candidate-after-rollback')
        elif args.apply:
            ops.require_root()
            python=ops.OPT/'releases'/ACTIVE/'.venv/bin/python'
            if Path(sys.prefix).resolve()!=python.parent.parent.resolve():os.execv(str(python),[str(python),'-I','-B',str(Path(__file__).resolve()),*sys.argv[1:]])
            signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(CheckFailed('release_interrupted')))
            apply(args.driver_revision)
        else:
            scope(args.driver_revision);print(json.dumps({'read_only':True,'from_revision':ACTIVE,'revision':CANDIDATE,'fresh_backup_restore':True,'compatible_application_rollback_drill':True,'web_executor_restart':True,'Nginx_change':'exact own static alias only','database_migrations':False,'native_execution':False,'root_required':True,'protected_state':str(STATE)}))
    except BaseException as error:
        print(json.dumps({'passed':False,'step':STEP,'failed_check':str(error) if isinstance(error,CheckFailed) else type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
