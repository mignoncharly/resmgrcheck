"""Separate web runtime; never imports authenticated QNX configuration into HTTP."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from .credentials import CredentialError,read_credential

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
ENVIRONMENT = os.environ.get('RMC_WEB_ENV', 'production')
if ENVIRONMENT not in {'production', 'staging', 'test'}:
    raise ImproperlyConfigured('RMC_WEB_ENV must be production, staging or test')
SERVICE_ROLE=os.environ.get('RMC_WEB_ROLE','web')
if SERVICE_ROLE not in {'web','executor','ai','operator','backup'}:raise ImproperlyConfigured('Unknown private service role')

def secret(name, required=True):
    filename = os.environ.get(name + '_FILE')
    if ENVIRONMENT=='production' and not filename:raise ImproperlyConfigured(name+' requires a protected credential file in production')
    if filename:
        try:
            value=read_credential(filename,name,SERVICE_ROLE)
        except (CredentialError,OSError):
            raise ImproperlyConfigured(name+' credential file permissions/type invalid') from None
    else:value=os.environ.get(name, '')
    if required and len(value) < 32:
        raise ImproperlyConfigured(name + ' must be configured privately (32+ characters)')
    return value

SECRET_KEY = secret('RMC_WEB_SECRET_KEY')
MFA_ENCRYPTION_KEY = secret('RMC_WEB_MFA_KEY') if SERVICE_ROLE in {'web','operator'} else ''
DEBUG = False
ALLOWED_HOSTS = os.environ.get('RMC_WEB_ALLOWED_HOSTS', 'qnx-resmgrcheck.gestionatech.de').split(',')
CSRF_TRUSTED_ORIGINS = [v for v in os.environ.get('RMC_WEB_CSRF_ORIGINS', 'https://qnx-resmgrcheck.gestionatech.de').split(',') if v]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
                 'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
                 'django.contrib.sites','allauth','allauth.account','allauth.mfa','allauth.usersessions','control']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware','allauth.account.middleware.AccountMiddleware']
ROOT_URLCONF = 'resmgr_web.urls'
WSGI_APPLICATION = 'resmgr_web.wsgi.application'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates', 'DIRS':[BASE_DIR/'templates'], 'APP_DIRS':True,
              'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.environ.get('RMC_WEB_DB_NAME','resmgrcheck_web'),
                       'USER':os.environ.get('RMC_WEB_DB_USER','resmgrcheck_web'), 'PASSWORD':os.environ.get('RMC_WEB_DB_PASSWORD',''),
                       'HOST':os.environ.get('RMC_WEB_DB_HOST','/run/postgresql'), 'PORT':os.environ.get('RMC_WEB_DB_PORT','5432'),
                       'CONN_MAX_AGE':0,'OPTIONS':{'connect_timeout':5,'options':'-c statement_timeout=10000 -c lock_timeout=5000'},
                       'TEST':{'NAME':os.environ.get('RMC_WEB_TEST_DB_NAME','test_resmgrcheck_web')}}}
AUTH_USER_MODEL = 'control.User'
AUTHENTICATION_BACKENDS = ['control.auth.AdministratorBackend']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher','django.contrib.auth.hashers.PBKDF2PasswordHasher']
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
                            {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
                            {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
                            {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {'username'}
ACCOUNT_SIGNUP_FIELDS = ['username*','password1*','password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_NOTIFICATIONS = False
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if ENVIRONMENT == 'production' else 'http'
MFA_SUPPORTED_TYPES = ['totp','recovery_codes']
MFA_TOTP_ISSUER = 'ResMgrCheck'
USERSESSIONS_TRACK_ACTIVITY = True
EMAIL_BACKEND = 'control.auth.DisabledMailBackend'
LOGIN_REDIRECT_URL = '/app/'
LOGOUT_REDIRECT_URL = '/'
SESSION_COOKIE_NAME = 'resmgrcheck_session'
CSRF_COOKIE_NAME = 'resmgrcheck_csrf'
SESSION_COOKIE_SECURE = ENVIRONMENT == 'production'
CSRF_COOKIE_SECURE = ENVIRONMENT == 'production'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 43200
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = ENVIRONMENT == 'production'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https') if ENVIRONMENT == 'production' else None
SECURE_HSTS_SECONDS = 31536000 if ENVIRONMENT == 'production' else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144
FILE_UPLOAD_MAX_MEMORY_SIZE = 131072
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
DATA_UPLOAD_MAX_NUMBER_FILES = 1
STATIC_URL = '/static/'
STATIC_ROOT = Path(os.environ.get('RMC_WEB_STATIC_ROOT',REPO_ROOT/'.local/web/static'))
MEDIA_ROOT = Path(os.environ.get('RMC_WEB_ARTIFACT_ROOT',REPO_ROOT/'.local/web/artifacts'))
PRIVATE_ROOT = Path(os.environ.get('RMC_WEB_PRIVATE_ROOT',REPO_ROOT/'.local/web/private'))
EXECUTOR_REGISTRY = os.environ.get('RMC_WEB_EXECUTOR_REGISTRY','')
ENGINE_ROOT = Path(os.environ.get('RMC_WEB_ENGINE_ROOT',REPO_ROOT))
ENGINE_PYTHON = os.environ.get('RMC_WEB_ENGINE_PYTHON','/usr/bin/python3')
AI_CONFIG = os.environ.get('RMC_WEB_AI_CONFIG','') # Private AI worker only; HTTP never reads provider credentials.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
CACHES = {'default':{'BACKEND':'django.core.cache.backends.db.DatabaseCache','LOCATION':'control_cache'}}
LOGGING = {'version':1,'disable_existing_loggers':False,'formatters':{'private':{'()':'control.logging.PrivateFormatter'}},'handlers':{'console':{'class':'logging.StreamHandler','formatter':'private'}},
           'root':{'handlers':['console'],'level':'WARNING'},'loggers':{'django.request':{'handlers':['console'],'level':'ERROR','propagate':False}}}
# No request bodies, credentials or raw provider errors are logged.
ACCOUNT_ADAPTER = 'control.auth.AccountAdapter'
MFA_ADAPTER = 'control.auth.MFAAdapter'
MIDDLEWARE.append('control.middleware.PolicyMiddleware')
import sys
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))
ENGINE_EXECUTION_TIMEOUT = 600
MAX_QUEUED_JOBS = 30
RUNNER_ENABLED=os.environ.get('RMC_WEB_RUNNER_ENABLED','0')=='1'
RUNNER_ORIGIN='https://qnx-resmgrcheck.gestionatech.de'
RUNNER_SIGNING_KEY=secret('RMC_WEB_RUNNER_KEY') if RUNNER_ENABLED and SERVICE_ROLE in {'web','operator'} else ''
if RUNNER_SIGNING_KEY:
    import re
    if not re.fullmatch('[0-9a-f]{64}',RUNNER_SIGNING_KEY):raise ImproperlyConfigured('Runner signing key must be a private Ed25519 seed')
TEMPLATES[0]['OPTIONS']['context_processors'].append('control.context.product')
MIDDLEWARE.insert(MIDDLEWARE.index('control.middleware.PolicyMiddleware'),'allauth.usersessions.middleware.UserSessionsMiddleware')

MIDDLEWARE.insert(MIDDLEWARE.index('control.middleware.PolicyMiddleware'),'control.access_middleware.AccessSessionMiddleware')

LOGIN_URL = '/administrator/login/'

if ENVIRONMENT=='production':
    if ALLOWED_HOSTS!=['qnx-resmgrcheck.gestionatech.de'] or CSRF_TRUSTED_ORIGINS!=['https://qnx-resmgrcheck.gestionatech.de']:raise ImproperlyConfigured('Production host/origin must match the approved hostname')
    if not DATABASES['default']['HOST'].startswith('/') or DATABASES['default']['PASSWORD']:raise ImproperlyConfigured('Production requires the dedicated peer-auth Unix-socket database')
    for name in ['RMC_WEB_STATIC_ROOT','RMC_WEB_ARTIFACT_ROOT','RMC_WEB_PRIVATE_ROOT']:
        value=os.environ.get(name,'')
        if not value or not Path(value).is_absolute() or '.local' in Path(value).parts:raise ImproperlyConfigured(name+' requires an explicit dedicated absolute production path')
    if SERVICE_ROLE=='web' and (EXECUTOR_REGISTRY or AI_CONFIG):raise ImproperlyConfigured('Public web service must not receive executor/provider configuration')
    if SERVICE_ROLE=='executor' and (not EXECUTOR_REGISTRY or AI_CONFIG):raise ImproperlyConfigured('Executor requires its private registry and no AI provider configuration')
    if SERVICE_ROLE=='ai' and EXECUTOR_REGISTRY:raise ImproperlyConfigured('AI worker must not receive executor configuration')
