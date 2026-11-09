"""Permit PostgreSQL authorization-row locks while denying all executor updates.

SELECT FOR UPDATE needs UPDATE privilege on at least one column. The invoker-role
trigger denies every actual UPDATE from that role, including id=id. No SECURITY
DEFINER, table ownership, schema privilege or authorization mutation is granted.
"""
import re
from executor_plan import require

ROLE='resmgr_exec'
PREFIX='rmc_executor_lock_only'
TABLES=['control_user','control_accesscode']

def install(connection,role=ROLE,prefix=PREFIX):
    from django.db import transaction
    require(re.fullmatch('[a-z_][a-z0-9_]{0,62}',role) and re.fullmatch('[a-z_][a-z0-9_]{0,40}',prefix),'lock_guard_identity_invalid')
    quote=connection.ops.quote_name
    function=prefix+'_guard'
    body="BEGIN\n IF current_user = '"+role+"' THEN\n  RAISE EXCEPTION 'executor_authorization_update_forbidden';\n END IF;\n RETURN NEW;\nEND;"
    with transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s',[role])
        flags=cursor.fetchone();require(flags is not None and not any(flags),'lock_role_privileged_or_missing')
        cursor.execute("SELECT p.oid,p.prosrc,p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner),current_user,p.prorettype='trigger'::regtype FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname=%s AND p.pronargs=0",[function])
        rows=cursor.fetchall();require(len(rows)<=1,'lock_guard_function_ambiguous')
        if rows:
            row=rows[0];require(row[1]==body and row[2] is False and row[3]==['search_path=pg_catalog'] and row[4]==row[5] and row[6] is True,'existing_lock_guard_differs')
        else:
            cursor.execute('CREATE FUNCTION public.'+quote(function)+'() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $rmc$'+body+'$rmc$')
            cursor.execute('REVOKE ALL ON FUNCTION public.'+quote(function)+'() FROM PUBLIC')
        cursor.execute("SELECT ('public.'||quote_ident(%s)||'()')::regprocedure::oid",[function]);function_oid=cursor.fetchone()[0]
        for index,table in enumerate(TABLES):
            trigger=prefix+'_'+str(index)
            cursor.execute('SELECT pg_get_userbyid(relowner)=current_user,pg_get_userbyid(relowner)=%s FROM pg_class WHERE oid=%s::regclass',[role,'public.'+table])
            owner=cursor.fetchone();require(owner==(True,False),'lock_table_ownership_invalid')
            cursor.execute("SELECT a.attname FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped AND has_column_privilege(%s,a.attrelid,a.attnum,'UPDATE')",['public.'+table,role])
            columns={row[0] for row in cursor.fetchall()};require(columns in (set(),{'id'}),'unexpected_authorization_update_grants')
            cursor.execute('SELECT tgfoid,tgtype,tgenabled,tgnargs,tgqual IS NULL,tgattr::text,tgisinternal FROM pg_trigger WHERE tgrelid=%s::regclass AND tgname=%s',['public.'+table,trigger])
            existing=cursor.fetchone()
            if existing:
                require(existing==(function_oid,19,'O',0,True,'',False),'existing_lock_trigger_differs')
            else:
                require(not columns,'unprotected_existing_authorization_grant')
                cursor.execute('CREATE TRIGGER '+quote(trigger)+' BEFORE UPDATE ON public.'+quote(table)+' FOR EACH ROW EXECUTE FUNCTION public.'+quote(function)+'()')
            cursor.execute('GRANT UPDATE(id) ON public.'+quote(table)+' TO '+quote(role))
            cursor.execute('SELECT has_table_privilege(%s,%s,\'UPDATE\'),has_table_privilege(%s,%s,\'TRIGGER\')',[role,'public.'+table,role,'public.'+table])
            require(cursor.fetchone()==(False,False),'authorization_table_privilege_widened')
    return {'role':role,'columns':['id'],'actual_updates':'denied by invoker-role triggers','schema_or_table_ownership_granted':False}
