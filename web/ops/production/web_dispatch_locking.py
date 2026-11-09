"""Precreate the queue mutex; web may lock it, never create/change executor leases."""
from executor_plan import require
from executor_locking import install as install_guard

def install(connection,*,role='resmgr_web',prefix='rmc_web_dispatch_lock_only',check_only=False):
    from django.db import transaction
    with transaction.atomic():
        guard=install_guard(connection,role,prefix,check_only=check_only,tables=['control_executorslot'],column='name',denial='web_dispatch_update_forbidden')
        with connection.cursor() as cursor:
            if not check_only:
                cursor.execute("INSERT INTO public.control_executorslot(name,run_id,token,expires_at) VALUES('dispatch',NULL,NULL,NULL) ON CONFLICT(name) DO NOTHING")
            cursor.execute("SELECT name,run_id,token,expires_at FROM public.control_executorslot WHERE name='dispatch'")
            require(cursor.fetchone()==('dispatch',None,None,None),'dispatch_sentinel_missing_or_occupied')
            for privilege in ['INSERT','DELETE','UPDATE','TRUNCATE','TRIGGER']:
                cursor.execute('SELECT has_table_privilege(%s,%s,%s)',[role,'public.control_executorslot',privilege])
                require(cursor.fetchone()[0] is False,'web_executor_lease_privilege_widened')
    return {**guard,'sentinel':'dispatch','web_lease_creation_or_mutation':False}
