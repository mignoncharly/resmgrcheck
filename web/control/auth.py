from cryptography.fernet import Fernet
from django.conf import settings
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.account.adapter import DefaultAccountAdapter
from .models import Membership

class MFAAdapter(DefaultMFAAdapter):
    def encrypt(self,text):return Fernet(settings.MFA_ENCRYPTION_KEY.encode()).encrypt(text.encode()).decode()
    def decrypt(self,text):return Fernet(settings.MFA_ENCRYPTION_KEY.encode()).decrypt(text.encode()).decode()
    def can_delete_authenticator(self,authenticator):
        privileged=Membership.objects.filter(user=authenticator.user,active=True,role__in=['owner','admin']).exists()
        return not (privileged or authenticator.user.is_staff)

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self,request):
        return settings.REGISTRATION_OPEN and super().is_open_for_signup(request)
