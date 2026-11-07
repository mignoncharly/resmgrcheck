import time
from django.test import Client
import hashlib,re
from allauth.mfa.totp.internal.auth import TOTP,generate_totp_secret,hotp_value,format_hotp_value
from control.models import User,Organization,Membership,Project,ProjectMembership

PASSWORD='Integration account password 792! Strong phrase'

def user(email,verified=True,mfa=False):
    username=re.sub('[^a-z0-9_.-]','-',email.lower())[:29]+'-'+hashlib.sha256(email.lower().encode()).hexdigest()[:8]
    result=User.objects.create_user(username,PASSWORD,is_staff=True,is_active=verified)
    if mfa:TOTP.activate(result,generate_totp_secret())
    return result

def signed_client(result,mfa=False,csrf=False):
    client=Client(enforce_csrf_checks=csrf);client.force_login(result)
    if mfa:
        session=client.session
        session['account_authentication_methods_user']=str(result.pk)
        session['account_authentication_methods']=[{'method':'mfa','type':'totp','at':time.time()}]
        session.save()
    return client

def tenant(name,email):
    owner=user(email,mfa=True);organization=Organization.objects.create(name=name)
    Membership.objects.create(organization=organization,user=owner,role='owner')
    project=Project.objects.create(organization=organization,name=name+' project',created_by=owner)
    return owner,organization,project
