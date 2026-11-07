#!/usr/bin/env python3
"""Qualify real PostgreSQL runtime grants inside a rolled-back private-staging TX.

No persistent roles/ACL/data changes, QNX contact or production OS-isolation claim.
"""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
import django;django.setup()
from django.conf import settings
import psycopg
from psycopg import sql

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);options=parser.parse_args()
d=settings.DATABASES['default']
assert settings.ENVIRONMENT=='staging' and d['HOST']==str(ROOT/'.local/web/pgsocket') and str(d['PORT'])=='5438' and d['NAME']=='resmgrcheck_web_stage'
roles=['resmgr_web','resmgr_exec','resmgr_ai','resmgr_backup'];observations=[]
connection=psycopg.connect(dbname=d['NAME'],host=d['HOST'],port=d['PORT'],user=d['USER'],connect_timeout=5)
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM pg_roles WHERE rolname=ANY(%s)',[roles]);assert cursor.fetchone()[0]==0,'Refuse existing role names'
        for role in roles:cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role)))
        text=(ROOT/'web/ops/production/database-grants.sql').read_text();text='\n'.join(line for line in text.splitlines() if not line.startswith('\\'))
        text=text.replace('DATABASE resmgrcheck_web','DATABASE resmgrcheck_web_stage');cursor.execute(text)
        for role in roles:
            cursor.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(role)))
            cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user');assert not any(cursor.fetchone())
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)");assert cursor.fetchone()[0]==0
            cursor.execute('SELECT count(*) FROM control_artifact');cursor.fetchone()
            operations=[('schema-create','CREATE TABLE public.forbidden_runtime_probe(id int)'),
                ('audit-rewrite','UPDATE control_auditevent SET action=action WHERE false'),
                ('trigger-disable','ALTER TABLE control_auditevent DISABLE TRIGGER ALL')]
            if role=='resmgr_web':operations += [('executor-lease-write','UPDATE control_executorslot SET expires_at=expires_at WHERE false'),('provider-state-write','UPDATE control_aiproviderstate SET available=available WHERE false')]
            if role in {'resmgr_exec','resmgr_ai','resmgr_backup'}:operations += [('administrator-write','UPDATE control_user SET is_superuser=is_superuser WHERE false'),('code-write','UPDATE control_accesscode SET description=description WHERE false')]
            if role in {'resmgr_ai','resmgr_backup'}:operations += [('native-job-write','UPDATE control_run SET state=state WHERE false')]
            for label,statement in operations:
                cursor.execute('SAVEPOINT permission_probe')
                try:cursor.execute(statement)
                except psycopg.errors.InsufficientPrivilege:denied=True
                else:denied=False
                cursor.execute('ROLLBACK TO SAVEPOINT permission_probe');assert denied,(role,label,'unexpected privilege')
                observations.append({'role':role,'operation':label,'sqlstate':'42501','denied':True})
            cursor.execute('RESET ROLE')
finally:
    connection.rollback();connection.close()
with psycopg.connect(dbname=d['NAME'],host=d['HOST'],port=d['PORT'],user=d['USER'],connect_timeout=5) as verify:
    with verify.cursor() as cursor:cursor.execute('SELECT count(*) FROM pg_roles WHERE rolname=ANY(%s)',[roles]);assert cursor.fetchone()[0]==0
record={'passed':True,'kind':'actual-postgresql-runtime-grant-qualification','negative_checks':observations,'roles_nonprivileged_and_nonowner':True,'evidence_select_permitted':True,
    'all_role_and_acl_changes_rolled_back':True,'qnx_contacted':False,'production_os_isolation_qualified':False,
    'scope':'Private staging transaction with real SET ROLE and PostgreSQL permission checks. Actual production peer mappings/service identities are a separate pending root qualification.'}
Path(options.out).write_text(json.dumps(record,indent=2)+'\n');print('PASS: real PostgreSQL least-privilege denials; no persistent roles, ACL or data changes.')
