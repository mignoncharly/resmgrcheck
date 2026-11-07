from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from allauth.mfa.models import Authenticator
from allauth.usersessions.models import UserSession
from control.models import User
from control.security import audit
from .provision_administrator import local_operator,protected_password

class Command(BaseCommand):
    help='Protected local administrator recovery, never email. Revoke all sessions; optional explicit lost-MFA reset requires reenrollment.'
    def add_arguments(self,parser):
        parser.add_argument('--username',required=True);parser.add_argument('--password-file');parser.add_argument('--reset-mfa',action='store_true')
    def handle(self,*args,**options):
        local_operator()
        with transaction.atomic():
            user=User.objects.select_for_update().filter(username__iexact=options['username'],is_staff=True).first()
            if not user:raise CommandError('Administrator not found')
            password=protected_password(options['password_file']);validate_password(password,user);user.set_password(password)
            user.session_version+=1;user.is_active=True;user.save(update_fields=['password','session_version','is_active'])
            for session in UserSession.objects.filter(user=user):session.end()
            if options['reset_mfa']:Authenticator.objects.filter(user=user).delete()
            audit(user,'administrator.local_recovery',object_id=user.pk,mfa_reset=options['reset_mfa'],sessions_revoked=True)
        self.stdout.write('Local recovery completed; all previous sessions are revoked. No email was sent.')
