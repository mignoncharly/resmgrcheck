from django.contrib.auth.signals import user_logged_in,user_logged_out,user_login_failed
from django.dispatch import receiver
from .security import audit

@receiver(user_logged_in)
def login_audit(sender,request,user,**kwargs):
    from django.utils import timezone
    if request is not None:
        request.session['rmc_admin_started_at']=timezone.now().timestamp()
        request.session['rmc_admin_last_seen']=request.session['rmc_admin_started_at']
    audit(user,'account.login')
@receiver(user_logged_out)
def logout_audit(sender,request,user,**kwargs):audit(user,'account.logout')
@receiver(user_login_failed)
def failed_audit(sender,credentials,request,**kwargs):audit(None,'account.login_denied')
from allauth.account.signals import password_changed
from allauth.mfa.signals import authenticator_added,authenticator_removed,authentication_failed

@receiver(password_changed)
def password_audit(sender,request,user,**kwargs):audit(user,'account.password_changed')

@receiver(authenticator_added)
def mfa_added(sender,request,user,authenticator,**kwargs):audit(user,'account.mfa_added',authenticator_type=authenticator.type)

@receiver(authenticator_removed)
def mfa_removed(sender,request,user,authenticator,**kwargs):audit(user,'account.mfa_removed',authenticator_type=authenticator.type)

@receiver(authentication_failed)
def mfa_denied(sender,request,user,authenticator,**kwargs):audit(user,'account.mfa_denied')
