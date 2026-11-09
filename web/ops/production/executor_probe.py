#!/usr/bin/env python3
"""Runs only under the canonical executor unit's credential/sandbox context."""
import io,json,os,pwd,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import executor_plan as plan

def probe():
    uid=pwd.getpwnam('resmgr-exec').pw_uid
    plan.require(os.geteuid()==uid and os.environ.get('CREDENTIALS_DIRECTORY')=='/run/credentials/resmgrcheck-executor.service','actual_executor_context_required')
    root=Path('/opt/resmgrcheck/releases')/plan.APPLICATION
    plan.require(Path('/opt/resmgrcheck/current').resolve()==root,'active_release_differs')
    sys.path[:0]=[str(root/'web'),str(root)]
    os.environ['DJANGO_SETTINGS_MODULE']='resmgr_web.settings'
    import django;django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection
    from resmgrcheck.transport import Target,Transport
    from resmgrcheck.deployment import Deployment,verify_remote,engine_info
    from resmgrcheck.contracts import Profile,load
    plan.require(settings.SERVICE_ROLE=='executor' and settings.ENVIRONMENT=='production' and not settings.RUNNER_ENABLED and not settings.AI_CONFIG,'executor_policy')
    output=io.StringIO();call_command('runtime_check',stdout=output)
    runtime=json.loads(output.getvalue())
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_user');plan.require(cursor.fetchone()[0]=='resmgr_exec','database_role_differs')
        for table,privilege,expected in [('control_run','UPDATE',True),('control_artifact','INSERT',True),
                ('control_auditevent','INSERT',True),('control_auditevent','UPDATE',False),
                ('control_auditevent','DELETE',False),('control_user','UPDATE',False),('control_accesscode','UPDATE',False)]:
            cursor.execute('SELECT has_table_privilege(current_user,%s,%s)',['public.'+table,privilege])
            plan.require(cursor.fetchone()[0]==expected,'executor_database_grant_differs')
        for table in ['control_user','control_accesscode']:
            cursor.execute("SELECT attname FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped AND has_column_privilege(current_user,attrelid,attnum,'UPDATE')",['public.'+table])
            plan.require({row[0] for row in cursor.fetchall()}=={'id'},'executor_lock_only_column_grants_differ')
    from django.db import transaction
    with transaction.atomic(),connection.cursor() as cursor:
        for table in ['control_user','control_accesscode']:
            cursor.execute('SELECT id FROM public.'+table+' LIMIT 1 FOR UPDATE');cursor.fetchall()
        transaction.set_rollback(True)
    plan.require(json.loads(plan.read_owned(plan.CONFIG/'registry.json',uid,{0o600}))==plan.registry(),'registry_differs')
    plan.require(plan.read_owned(plan.CONFIG/'ssh-config',uid,{0o600})==plan.ssh_config(),'ssh_configuration_differs')
    plan.require(plan.digest(plan.read_owned(plan.CONFIG/'known-hosts',uid,{0o600}))==plan.KNOWN_HOSTS_SHA,'host_identity_differs')
    plan.read_owned(plan.CONFIG/'ssh-key',uid,{0o600},16384)
    target=Target.read('lab',plan.CONFIG/'target.json');plan.require(target.data==plan.target_config()['targets']['lab'],'target_configuration_differs')
    transport=Transport(target);deployments={};capabilities=None
    for role,(name,expected) in plan.MANIFESTS.items():
        raw=plan.read_owned(plan.CONFIG/(role+'-deployment.json'),uid,{0o600})
        plan.require(plan.digest(raw)==expected,'manifest_hash_differs');d=Deployment.parse(json.loads(raw))
        observed=verify_remote(transport,d)
        caps=engine_info(transport.command(d.data['directory']+'/worker','--describe'))
        plan.require(set(caps)=={'sensor-v1','job-v1'} and all(set(Profile.parse(load(root/'profiles'/(profile+'.json'))).data['capabilities']['required'])<=set(caps[profile+'-v1']) for profile in ['sensor','job']),'required_capabilities_missing')
        if capabilities is not None:plan.require(caps==capabilities,'build_capability_mismatch')
        capabilities=caps;deployments[role]={'deployment_id':d.data['deployment_id'],'verified_files':len(observed),'source_revision':d.data['build']['source_revision']}
    raw=transport.ssh('df -g /data');match=re.search(rb'Files\s*:\s*([0-9]+) total\s+([0-9]+) avail',raw)
    plan.require(match and int(match[2])>=128,'target_file_budget_insufficient')
    return {'passed':True,'kind':'actual-systemd-executor-probe','application':plan.APPLICATION,
        'driver_revision':Path(__file__).resolve().parent.name,'runtime':runtime,'database_grants_verified':True,
        'deployments':deployments,'compiled_adapters':capabilities,'target_file_entries_available':int(match[2]),
        'target_contact':'read-only identity, manifests, SHA256 downloads and compiled capability discovery',
        'service_instance_health':'unknown until native run','SDK_access':'not required or granted','tests_launched':False}

if __name__=='__main__':
    try:
        result=probe();path=plan.probe_file(result['driver_revision'])
        if path.exists() or path.is_symlink():
            old=json.loads(plan.read_owned(path,os.geteuid(),{0o600}))
            plan.require(set(old)==set(result) and old.get('passed') is True and all(old.get(key)==result[key] for key in ['kind','application','driver_revision']),'unknown_probe_receipt')
        from resmgrcheck.artifacts import atomic_write
        atomic_write(path,(json.dumps(result,sort_keys=True,indent=2)+'\n').encode());path.chmod(0o600)
        print(json.dumps({'executor_probe':'passed','secrets_printed':False}))
    except BaseException as error:
        print(json.dumps({'executor_probe':'failed','error_class':type(error).__name__,'secrets_printed':False}));raise SystemExit(1) from None
