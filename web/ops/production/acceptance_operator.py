#!/usr/bin/env python3
"""Root coordinator: append an audited temporary principal, run browser as operator,
then disable only that identity. Never changes existing users, keys or target routes.
"""
import argparse,json,os,pwd,re,secrets,signal,stat,sys,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True # -I ignores PYTHONDONTWRITEBYTECODE; protect immutable source.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import deploy_https as deployment
from https_checks import require,CheckFailed
REGISTRY=Path('/etc/resmgrcheck/executor/registry.json')


def load_application(release):
    require(os.geteuid()==0,'local_root_operator_required')
    root=Path('/opt/resmgrcheck/releases')/release
    require(Path('/opt/resmgrcheck/current').resolve()==root,'active_release_differs')
    data=json.loads(deployment.read(Path('/etc/resmgrcheck/operator.json'),private=True,limit=16384))
    require(isinstance(data,dict) and all(k.startswith('RMC_WEB_') and isinstance(v,str) for k,v in data.items()),'operator_config_invalid')
    os.environ.clear();os.environ.update({**deployment.ENV,**data,'DJANGO_SETTINGS_MODULE':'resmgr_web.settings'})
    sys.path.insert(0,str(root));sys.path.insert(0,str(root/'web'))
    import django;django.setup()
    from django.conf import settings
    from django.db import connection
    require(settings.ENVIRONMENT=='production' and settings.SERVICE_ROLE=='operator' and
        str(connection.settings_dict['HOST'])=='/run/resmgrcheck-db' and str(connection.settings_dict['PORT'])=='5448' and
        connection.settings_dict['NAME']=='resmgrcheck_web' and connection.settings_dict['USER']=='resmgr_owner','dedicated_operator_context_required')
    require(not settings.ADMIN_MFA_REQUIRED and not settings.RUNNER_ENABLED and not settings.AI_CONFIG,'customer_runner_and_AI_must_stay_disabled')
    from control.models import AIProviderState
    require(not AIProviderState.objects.filter(available=True).exists(),'AI_provider_state_must_be_disabled')


def native_plan():
    from control.models import Target,BuildRelease,Run,ExecutorSlot
    from control.jobs import ACTIVE
    registry=REGISTRY
    if not registry.exists():return {'status':'blocked','reason':'approved_executor_registry_missing'}
    info=registry.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid not in {0,pwd.getpwnam('resmgr-exec').pw_uid} or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1 or info.st_size>65536:
        return {'status':'blocked','reason':'approved_executor_registry_protection_invalid'}
    descriptor=os.open(registry,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:data=json.loads(os.read(descriptor,65537))
    finally:os.close(descriptor)
    if not isinstance(data,dict) or set(data)!={'schema_version','targets'} or data['schema_version']!=1 or not isinstance(data['targets'],dict):
        return {'status':'blocked','reason':'approved_executor_registry_schema_invalid'}
    if Run.objects.filter(state__in=ACTIVE).exists() or ExecutorSlot.objects.filter(run__isnull=False).exists():
        return {'status':'blocked','reason':'existing_work_or_slot_requires_reconciliation'}
    choices=[]
    for target in Target.objects.filter(kind='managed-lab',approved=True,state='available',project__active=True,project__organization__active=True).select_related('project__organization'):
        row=data['targets'].get(str(target.pk))
        if not isinstance(row,dict) or set(row)!={'organization_id','project_id','engine_root','config','alias','builds'}:continue
        if row['organization_id']!=str(target.project.organization_id) or row['project_id']!=str(target.project_id) or target.binding!=str(target.pk):continue
        # Only already operator-approved immutable native candidates. Labels select
        # intent; real evidence/comparison, never labels, must prove FAIL→PASS.
        builds=list(BuildRelease.objects.filter(target=target,approved=True))
        before=[b for b in builds if re.search(r'\b(before|defect|broken)\b',b.label,re.I)]
        after=[b for b in builds if re.search(r'\b(after|corrected|fixed)\b',b.label,re.I)]
        for left in before:
            for right in after:
                if left.pk==right.pk or left.manifest.get('build',{}).get('source_tree_sha256')==right.manifest.get('build',{}).get('source_tree_sha256'):continue
                if not {'sensor-v1','job-v1'}<=set(right.manifest.get('candidates',{})) or 'sensor-v1' not in left.manifest.get('candidates',{}):continue
                if any(str(build.pk) not in row.get('builds',{}) or build.binding!=str(build.pk) for build in [left,right]):continue
                # Reuse only the pre-existing approved lab custody. Never copy SSH
                # keys, choose a new host or silently bless a new route here.
                if row['engine_root']!='/opt/resmgrcheck/engine':continue
                try:
                    from django.test.utils import override_settings
                    from control.engine import registry as binding_for,PolicyError
                    with override_settings(EXECUTOR_REGISTRY=str(registry)):
                        for build in [left,right]:binding_for(target,build)
                except (ValueError,OSError,PolicyError,TypeError,KeyError):
                    # No private path/config/exception text goes in the report.
                    continue
                choices.append({'status':'approved-existing-route','target_id':str(target.pk),'project_id':str(target.project_id),
                    'organization_id':str(target.project.organization_id),'before_build':str(left.pk),'after_build':str(right.pk)})
    if len(choices)!=1:return {'status':'blocked','reason':'exactly_one_operator_approved_before_after_lab_pair_required','candidate_pairs':len(choices)}
    unit=Path('/etc/systemd/system/resmgrcheck-executor.service')
    root=Path('/opt/resmgrcheck/current')
    if deployment.read(unit)!=(root/'web/ops/production/resmgrcheck-executor.service').read_bytes():
        return {'status':'blocked','reason':'executor_unit_requires_review'}
    if deployment.command(['systemctl','show','--value','--property=DropInPaths','resmgrcheck-executor.service']).strip():
        return {'status':'blocked','reason':'executor_overrides_require_review'}
    return choices[0]


def bootstrap(identifier,plan):
    from django.db import transaction
    from control.models import User,Organization,Membership,Project
    from control.security import audit
    password=secrets.token_urlsafe(36)
    with transaction.atomic():
        account=User.objects.create_user('accept-'+identifier.hex[:18],password,is_staff=True,is_active=True)
        organization=Organization.objects.create(name='HTTPS acceptance '+identifier.hex[:12])
        Membership.objects.create(user=account,organization=organization,role='owner')
        project=Project.objects.create(organization=organization,name='HTTPS acceptance workspace',created_by=account)
        foreign=Organization.objects.create(name='HTTPS ungranted scope '+identifier.hex[:12])
        foreign_project=Project.objects.create(organization=foreign,name='Ungrantable acceptance boundary',created_by=account)
        if plan.get('status')=='approved-existing-route':
            organization=Organization.objects.get(pk=plan['organization_id']);project=Project.objects.get(pk=plan['project_id'])
            Membership.objects.create(user=account,organization=organization,role='admin')
        audit(account,'https.acceptance.created',organization,account.pk,acceptance_id=str(identifier),native_plan=plan['status'])
    return {'username':account.username,'password':password,'account_id':str(account.pk),
        'acceptance_id':str(identifier),'organization_id':str(organization.pk),'project_id':str(project.pk),
        'foreign_project_id':str(foreign_project.pk),'native':plan}


def close(credentials):
    from django.db import transaction
    from django.utils import timezone
    from django.db.models import F
    from allauth.usersessions.models import UserSession
    from control.models import User,AccessCode,AccessSession,AuditEvent,Run
    from control.security import audit
    from control.jobs import ACTIVE
    with transaction.atomic():
        account=User.objects.select_for_update().get(pk=credentials['account_id'],username=credentials['username'])
        require(account.username.startswith('accept-') and AuditEvent.objects.filter(actor=account,action='https.acceptance.created',details__acceptance_id=credentials['acceptance_id']).exists(),'acceptance_cleanup_identity_differs')
        own=AccessCode.objects.select_for_update().filter(created_by=account)
        ids=list(own.values_list('pk',flat=True));own.filter(revoked_at=None).update(revoked_at=timezone.now(),policy_version=F('policy_version')+1)
        AccessSession.objects.filter(code_id__in=ids,revoked_at=None).update(revoked_at=timezone.now())
        User.objects.filter(pk=account.pk).update(is_active=False,session_version=F('session_version')+1)
        for session in UserSession.objects.filter(user=account):session.end()
        audit(account,'https.acceptance.closed',object_id=account.pk,acceptance_id=credentials['acceptance_id'],records_preserved=True)
        active=Run.objects.filter(actor=account,state__in=ACTIVE).exists() or Run.objects.filter(access_session__code_id__in=ids,state__in=ACTIVE).exists()
    return {'temporary_account_disabled':True,'temporary_codes_revoked':True,'existing_users_changed':False,
        'audit_runs_evidence_preserved':True,'own_native_work_still_active':active}


def run(release,driver,state):
    load_application(release);deployment.DIAGNOSTIC=state/'acceptance-diagnostic.log'
    source=deployment.SOURCE;owner=pwd.getpwuid(source.stat().st_uid);require(owner.pw_uid!=0,'browser_must_run_nonroot')
    browser_python=source/'.local/browser-test/bin/python';require(browser_python.is_file(),'installed_browser_environment_missing')
    # Reconcile only our interrupted attempts, using protected intents and the
    # append-only creation audit. Never adopt an account based on its name alone.
    from control.models import AuditEvent
    for intent in state.glob('acceptance-*.intent.json'):
        item=json.loads(deployment.read(intent,private=True));previous=uuid.UUID(item['acceptance_id'])
        cleanup_path=state/('acceptance-'+previous.hex+'.cleanup.json')
        if cleanup_path.exists():continue
        event=AuditEvent.objects.select_related('actor').filter(action='https.acceptance.created',details__acceptance_id=str(previous)).first()
        if event and event.actor_id:
            closed=close({'acceptance_id':str(previous),'account_id':str(event.actor_id),'username':event.actor.username})
            deployment.record(cleanup_path,closed)
    plan=native_plan()
    completed=state/'acceptance-report.json'
    if completed.exists():
        prior=json.loads(deployment.read(completed,private=True))
        if (prior.get('application_revision')==release and prior.get('driver_revision')==driver and
                prior.get('authentication_policy')=='administrator-password-only-v1' and prior.get('browser_passed') is True and prior.get('temporary_account_disabled') is True and
                (prior.get('native',{}).get('status')=='passed' or plan['status']!='approved-existing-route')):
            print(json.dumps({'overall_acceptance':'passed' if prior.get('passed') else 'in_progress',
                'reused_verified_browser_acceptance':True,'administrator_password':prior['administrator_password'],'administrator_MFA':'deferred',
                'access_codes':prior['access_codes'],'native':prior['native'],'independent_external_acceptance':'pending'}));return
    identifier=uuid.uuid4()
    output=source/'.local/web/evidence'/('production-https-'+identifier.hex);output.mkdir(mode=0o700)
    os.chown(output,owner.pw_uid,owner.pw_gid);output.chmod(0o700)
    executor_before=deployment.command(['systemctl','show','--value','--property=ActiveState','resmgrcheck-executor.service']).strip()
    deployment.record(state/('acceptance-'+identifier.hex+'.intent.json'),{'acceptance_id':str(identifier),'application_revision':release,'driver_revision':driver})
    started=False;cleanup=None;result=None;credentials=None
    try:
        credentials=bootstrap(identifier,plan)
        # New acceptance secrets stay root600 and are sent only on the owned pipe.
        private=state/('acceptance-'+identifier.hex+'.private.json');deployment.new_file(private,json.dumps(credentials).encode())
        if plan['status']=='approved-existing-route' and executor_before in {b'inactive',b'failed'}:
            deployment.command(['systemctl','start','resmgrcheck-executor.service']);started=True
        raw=deployment.command(['/usr/sbin/runuser','-u',owner.pw_name,'--',browser_python,'-I','-B',deployment.HERE/'public_acceptance.py',
            '--origin','https://'+deployment.HOST,'--out',output],data=json.dumps(credentials).encode(),timeout=1500)
        result=json.loads(raw);require(result.get('authentication_policy')=='administrator-password-only-v1' and result.get('administrator_password')=='passed' and result.get('administrator_MFA')=='deferred' and result.get('access_codes')=='passed','authenticated_acceptance_failed')
    finally:
        cleanup=close(credentials) if credentials else {'bootstrap_committed':False,'own_native_work_still_active':False}
        if started and not cleanup['own_native_work_still_active']:
            from control.models import Run
            from control.jobs import ACTIVE
            if not Run.objects.filter(state__in=ACTIVE).exists():deployment.command(['systemctl','stop','resmgrcheck-executor.service'])
        deployment.record(state/('acceptance-'+identifier.hex+'.cleanup.json'),cleanup)
        # Publish only safe cleanup metadata even when browser acceptance fails.
        # The protected receipt remains authoritative; no credentials are copied.
        deployment.new_file(output/'operator-cleanup.json',(json.dumps(cleanup,indent=2)+'\n').encode(),owner=(owner.pw_uid,owner.pw_gid))
    result.update(cleanup);result['application_revision']=release;result['driver_revision']=driver
    deployment.record(state/'acceptance-report.json',result)
    print(json.dumps({'overall_acceptance':'passed' if result.get('passed') else 'in_progress','browser_passed':result.get('browser_passed'),
        'administrator_password':result['administrator_password'],'administrator_MFA':'deferred','access_codes':result['access_codes'],
        'native':result.get('native',{'status':'not_run'}),'browser_evidence':str(output),'cleanup':cleanup,'independent_external_acceptance':'pending'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--release',required=True);parser.add_argument('--driver-revision',required=True);parser.add_argument('--state',required=True)
    args=parser.parse_args()
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        require(re.fullmatch('[0-9a-f]{40}',args.release) and re.fullmatch('[0-9a-f]{40}',args.driver_revision),'exact_commits_required')
        require(Path(args.state)==deployment.STATE,'protected_state_path_differs')
        run(args.release,args.driver_revision,Path(args.state))
    except BaseException:
        print(json.dumps({'passed':False,'error':'production_acceptance_failed_safely','secrets_printed':False}),flush=True)
        raise SystemExit(1) from None

if __name__=='__main__':main()
