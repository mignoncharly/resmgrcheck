"""Local provisioning only; no browser route and no password in argv/output."""
import getpass,os,re,stat
from pathlib import Path
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from control.models import User,Organization,Membership
from control.security import audit

def local_operator():
    if os.geteuid()==0:return
    # Development permission cannot be gained merely by changing RMC_WEB_ENV.
    # It is restricted to this user's own socket-only staging/test database.
    database=settings.DATABASES['default'];expected=settings.REPO_ROOT/'.local/web/pgsocket'
    local_stage=(settings.ENVIRONMENT in {'staging','test'} and settings.REPO_ROOT.stat().st_uid==os.geteuid()
        and Path(database['HOST']).resolve()==expected.resolve() and str(database['PORT'])=='5438'
        and database['NAME'] in {'resmgrcheck_web_stage','test_resmgrcheck_web'})
    if not local_stage:raise CommandError('Production administrator provisioning/recovery requires the local root operator.')

def protected_password(filename):
    if not filename:
        first=getpass.getpass('Administrator password: ');second=getpass.getpass('Repeat password: ')
        if first!=second:raise CommandError('Passwords did not match')
        return first
    descriptor=os.open(filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid not in {0,os.getuid()} or info.st_mode&0o077 or info.st_size>1024:raise CommandError('Password file must be an owned0600 regular file, at most1024 bytes')
        return os.read(descriptor,1025).decode().rstrip('\r\n')
    finally:os.close(descriptor)

class Command(BaseCommand):
    help='Provision an administrator locally. Password uses getpass or an owned0600 file; never argv. Optional explicit legacy adoption preserves evidence identity/MFA.'
    def add_arguments(self,parser):
        parser.add_argument('--username',required=True);parser.add_argument('--password-file');parser.add_argument('--adopt-user');parser.add_argument('--preserve-existing-password',action='store_true');parser.add_argument('--platform-owner',action='store_true');parser.add_argument('--organization',action='append',default=[]);parser.add_argument('--role',choices=['admin','owner'],default='admin')
    def handle(self,*args,**options):
        local_operator();username=options['username'].strip().lower()
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{2,39}',username):raise CommandError('username: expected3..40 lower-case letters, digits, dots, underscores or hyphens')
        if options['preserve_existing_password'] and not options['adopt_user']:raise CommandError('Password preservation requires explicit legacy adoption')
        with transaction.atomic():
            if User.objects.filter(username__iexact=username).exists():raise CommandError('Administrator username already exists')
            user=User.objects.select_for_update().get(pk=options['adopt_user']) if options['adopt_user'] else User()
            if options['adopt_user'] and user.is_staff and user.username:raise CommandError('Already an administrator; use protected recovery')
            user.username=username;user.email=None;user.is_staff=True;user.is_active=True;user.is_superuser=options['platform_owner'];user.session_version+=1
            if not options['preserve_existing_password']:
                password=protected_password(options['password_file']);validate_password(password,user);user.set_password(password)
            elif not user.has_usable_password():raise CommandError('Legacy password is unusable')
            user.save()
            for identifier in options['organization']:
                organization=Organization.objects.filter(pk=identifier,active=True).first()
                if not organization:raise CommandError('organization: unknown active organization')
                Membership.objects.update_or_create(user=user,organization=organization,defaults={'role':options['role'],'active':True})
            audit(user,'administrator.provisioned',object_id=user.pk,legacy_adopted=bool(options['adopt_user']),platform_owner=user.is_superuser,organization_ids=options['organization'])
        self.stdout.write('Administrator provisioned; existing sessions revoked. Username/password authentication is enabled; MFA is deferred for this release.')
