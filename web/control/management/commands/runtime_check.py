"""Read-only runtime-role/deployment checks; no service, target or key output."""
import errno,json,os,pwd,socket
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import connection

class Command(BaseCommand):
    help='Check the current DB role is nonprivileged/nonowner and this process cannot read unrelated private credentials. Does not qualify public HTTPS.'
    def handle(self,*args,**options):
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user')
            privileges=cursor.fetchone()
            cursor.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND pg_get_userbyid(c.relowner)=current_user")
            owned=cursor.fetchone()[0]
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN ('resmgr_owner','resmgr_pg','pg_write_server_files','pg_read_server_files','pg_execute_server_program','pg_signal_backend') AND pg_has_role(current_user,oid,'MEMBER'))")
            privileged_membership=cursor.fetchone()[0]
            cursor.execute("SELECT has_schema_privilege(current_user,'public','CREATE') OR has_database_privilege(current_user,current_database(),'CREATE')")
            schema_creation=cursor.fetchone()[0]
        private_paths=['/etc/resmgrcheck/executor/ssh-key','/etc/resmgrcheck/ai/provider.json','/etc/resmgrcheck/keys/mfa-key']
        forbidden=private_paths[:2] if settings.SERVICE_ROLE=='web' else private_paths[1:] if settings.SERVICE_ROLE=='executor' else [private_paths[0],private_paths[2]]
        identity={'web':'resmgr-web','executor':'resmgr-exec','ai':'resmgr-ai'}.get(settings.SERVICE_ROLE)
        web_network_denied=None
        if settings.SERVICE_ROLE=='web':
            try:probe=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            except OSError as error:web_network_denied=error.errno in {errno.EAFNOSUPPORT,errno.EPERM,errno.EACCES}
            else:probe.close();web_network_denied=False
        evidence_writable=os.access(settings.MEDIA_ROOT,os.W_OK)
        result={'service_role':settings.SERVICE_ROLE,'production_environment':settings.ENVIRONMENT=='production','nonroot_process':os.geteuid()!=0,
            'dedicated_os_identity':bool(identity) and pwd.getpwuid(os.geteuid()).pw_name==identity,
            'nonprivileged_database_role':bool(privileges) and not any(privileges),'owns_public_relations':bool(owned),
            'privileged_role_membership':privileged_membership,'can_create_schema_objects':schema_creation,
            'forbidden_credentials_readable':any(os.access(path,os.R_OK) for path in forbidden),'home_tree_readable':os.access('/home',os.R_OK),
            'web_ip_socket_creation_denied':web_network_denied,'evidence_write_matches_role':evidence_writable==(settings.SERVICE_ROLE=='executor'),
            'qnx_contacted':False,'public_https_verified':False}
        self.stdout.write(json.dumps(result))
        if not result['production_environment'] or not result['nonroot_process'] or not result['dedicated_os_identity'] or not result['nonprivileged_database_role'] or owned or privileged_membership or schema_creation or result['forbidden_credentials_readable'] or result['home_tree_readable'] or not result['evidence_write_matches_role'] or web_network_denied is False:raise CommandError('Production runtime isolation not established')
