"""Local-only additive upgrade gate. Never exposes keys or runs native work."""
import hashlib,io,json,os,re,secrets,stat
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from django.db import connection,transaction
from django.db.migrations.executor import MigrationExecutor
from .provision_administrator import local_operator

MIGRATIONS=['0018_customerrunner_alter_target_kind_alter_target_state_and_more',
    '0019_runnerjob_runnerchunk','0020_alter_run_profile']
ROLES=['resmgr_web','resmgr_exec','resmgr_ai','resmgr_backup']
TABLES=['control_customerrunner','control_runnerenrollment','control_runnernonce','control_runnerjob','control_runnerchunk']
PRIVILEGES=['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']
STATIC=Path('/var/lib/resmgrcheck/static')


def schema_plan(executor):
    executor.loader.check_consistent_history(connection)
    if ('control','0017_session_and_scope_integrity') not in executor.loader.applied_migrations:
        raise CommandError('Expected qualified schema through0017')
    plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
    pending=[migration.name for migration,backwards in plan]
    expected=[name for name in MIGRATIONS if ('control',name) not in executor.loader.applied_migrations]
    if (pending!=expected or any(backwards or migration.app_label!='control' for migration,backwards in plan)):
        raise CommandError('Unexpected migration plan; separate review required')
    return plan


def expected_privileges(role,table):
    result={'SELECT'}
    if role==ROLES[0]:
        result|={'INSERT','UPDATE'} if table in TABLES[:2]+[TABLES[3]] else {'INSERT','DELETE'} if table==TABLES[2] else {'INSERT'}
    if role==ROLES[1]:result|={'UPDATE'} if table==TABLES[3] else {'DELETE'} if table==TABLES[4] else set()
    return result


def verify_grants():
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_user');owner_role=cursor.fetchone()[0]
        for role in ROLES:
            cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s',[role])
            row=cursor.fetchone()
            if row is None or any(row):raise CommandError('Unexpected dedicated runtime role flags')
            cursor.execute('SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)',[role])
            if cursor.fetchone():raise CommandError('Unexpected runtime role membership')
            for table in TABLES:
                cursor.execute('SELECT tableowner FROM pg_tables WHERE schemaname=%s AND tablename=%s',['public',table])
                owner=cursor.fetchone()
                if not owner or owner[0]!=owner_role or owner[0] in ROLES:raise CommandError('Unexpected runner relation ownership')
                actual=set()
                for privilege in PRIVILEGES:
                    cursor.execute('SELECT has_table_privilege(%s,%s,%s)',[role,'public.'+table,privilege])
                    if cursor.fetchone()[0]:actual.add(privilege)
                if actual!=expected_privileges(role,table):raise CommandError('Runner role permissions differ from reviewed matrix')
        for role in ROLES:
            for name in ['control_runnernonce_id_seq','control_runnerchunk_id_seq']:
                for privilege in ['USAGE','SELECT','UPDATE']:
                    cursor.execute('SELECT has_sequence_privilege(%s,%s,%s)',[role,'public.'+name,privilege])
                    expected=(role==ROLES[0] and privilege in {'USAGE','SELECT'}) or (role==ROLES[3] and privilege=='SELECT')
                    if cursor.fetchone()[0]!=expected:
                        raise CommandError('Runner sequence permissions differ')


def rollback_safe():
    from control.models import Target,Run,BuildRelease
    with connection.cursor() as cursor:
        for name in TABLES:
            cursor.execute('SELECT EXISTS(SELECT 1 FROM '+connection.ops.quote_name(name)+')')
            if cursor.fetchone()[0]:raise CommandError('Rollback incompatible with retained runner records; preserve data and use forward repair')
    if (Target.objects.filter(kind='customer-runner').exists() or Run.objects.filter(profile='mailbox').exists() or
            BuildRelease.objects.filter(manifest__files__has_key='mailbox-v1-fixture').exists()):
        raise CommandError('Rollback incompatible with customer/mailbox records; use forward repair')


def asset_inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        info=path.lstat()
        if stat.S_ISDIR(info.st_mode):
            if info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)!=0o755:raise CommandError('Unexpected static directory')
            continue
        if path==root/'.release-static.json':continue
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or stat.S_IMODE(info.st_mode)!=0o644:
            raise CommandError('Unexpected static member')
        if info.st_size>16*1024**2:raise CommandError('Static member exceeds bound')
        result[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    if not result or len(result)>5000:raise CommandError('Static inventory unavailable or too large')
    return result


def assets(revision):
    # Separate tree, never collectstatic into the earlier release's STATIC_ROOT.
    from customer_runner.archive import publish
    if any(path.is_symlink() for path in [STATIC,*STATIC.parents]):raise CommandError('Static parent symlink')
    info=STATIC.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)!=0o755:raise CommandError('Unexpected static parent')
    target=STATIC/revision
    if target.exists() or target.is_symlink():return verify_assets(revision)
    attempt=STATIC/('.stage-'+revision+'-'+secrets.token_hex(12));attempt.mkdir(mode=0o755);attempt.chmod(0o755)
    from django.test.utils import override_settings
    with override_settings(STATIC_ROOT=attempt,FILE_UPLOAD_PERMISSIONS=0o644,FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o755):
        call_command('collectstatic',interactive=False,verbosity=0,stdout=io.StringIO())
    inventory=asset_inventory(attempt)
    record={'revision':revision,'files':inventory}
    descriptor=os.open(attempt/'.release-static.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'w') as stream:json.dump(record,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    for path in attempt.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:os.fsync(stream.fileno())
    for path in [*sorted((p for p in attempt.rglob('*') if p.is_dir()),reverse=True),attempt]:
        descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    publish(attempt,target)
    descriptor=os.open(STATIC,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
    return verify_assets(revision)


def verify_assets(revision):
    target=STATIC/revision
    if target.is_symlink() or not target.is_dir() or target.stat().st_uid!=os.geteuid() or stat.S_IMODE(target.stat().st_mode)!=0o755:
        raise CommandError('Static tree is not owned')
    path=target/'.release-static.json';info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>1024**2:
        raise CommandError('Static completion manifest is not protected')
    if json.loads(path.read_text())!={'revision':revision,'files':asset_inventory(target)}:raise CommandError('Static inventory changed')
    return str(target)


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser):
        parser.add_argument('operation',choices=['prepare','check','rollback-check']);parser.add_argument('--revision',required=True)
    def handle(self,*args,**options):
        local_operator();revision=options['revision']
        if not re.fullmatch('[0-9a-f]{40}',revision):raise CommandError('Exact release commit required')
        if settings.RUNNER_ENABLED:raise CommandError('Initial upgrade keeps customer endpoints disabled; enable only after separate qualification')
        if settings.ENVIRONMENT=='production' and (settings.SERVICE_ROLE!='operator' or settings.REPO_ROOT!=Path('/opt/resmgrcheck/releases')/revision or
                connection.settings_dict['NAME']!='resmgrcheck_web' or connection.settings_dict['USER']!='resmgr_owner' or
                str(connection.settings_dict['HOST'])!='/run/resmgrcheck-db' or str(connection.settings_dict['PORT'])!='5448'):
            raise CommandError('Expected immutable release and dedicated operator database context')
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext('resmgrcheck-private-upgrade'))")
            if not cursor.fetchone()[0]:raise CommandError('Another schema operator is active')
        try:
            executor=MigrationExecutor(connection);plan=schema_plan(executor)
            if options['operation']=='prepare':
                # All DDL and additive grants commit together on PostgreSQL; retry is safe.
                sql=(settings.REPO_ROOT/'web/ops/production/runner-grants.sql').read_text()
                with transaction.atomic():
                    executor.migrate(executor.loader.graph.leaf_nodes())
                    with connection.cursor() as cursor:cursor.execute(sql)
                    verify_grants()
                static=assets(revision)
            else:
                if plan:raise CommandError('Additive schema is not prepared')
                verify_grants();static=verify_assets(revision)
                if options['operation']=='rollback-check':rollback_safe()
            self.stdout.write(json.dumps({'passed':True,'operation':options['operation'],'revision':revision,'static_directory':static,
                'runner_enabled':False,'reversed_migrations':False,'services_changed':False}))
        finally:
            with connection.cursor() as cursor:cursor.execute("SELECT pg_advisory_unlock(hashtext('resmgrcheck-private-upgrade'))")
