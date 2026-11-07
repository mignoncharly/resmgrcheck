from cryptography.fernet import Fernet
from django.conf import settings
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.auth_backends import AuthenticationBackend
from django.core.mail.backends.base import BaseEmailBackend
from .models import Membership

class MFAAdapter(DefaultMFAAdapter):
    def encrypt(self,text):return Fernet(settings.MFA_ENCRYPTION_KEY.encode()).encrypt(text.encode()).decode()
    def decrypt(self,text):return Fernet(settings.MFA_ENCRYPTION_KEY.encode()).decrypt(text.encode()).decode()
    def can_delete_authenticator(self,authenticator):
        return False # Lost-MFA recovery is an audited protected local procedure.

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self,request):
        return False
    def authenticate(self,request,**credentials):
        user=super().authenticate(request,**credentials)
        return user if user and user.is_active and user.is_staff and user.username else None
    def send_notification_mail(self,*args,**kwargs):return None
    def send_mail(self,*args,**kwargs):raise RuntimeError('Email authentication is disabled')

class AdministratorBackend(AuthenticationBackend):
    def user_can_authenticate(self,user):return super().user_can_authenticate(user) and user.is_staff and bool(user.username)

class DisabledMailBackend(BaseEmailBackend):
    def send_messages(self,email_messages):raise RuntimeError('ResMgrCheck has no email workflow')
