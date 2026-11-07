"""Separate web runtime; never imports authenticated QNX configuration into HTTP."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
ENVIRONMENT = os.environ.get('RMC_WEB_ENV', 'production')
if ENVIRONMENT not in {'production', 'staging', 'test'}:
    raise ImproperlyConfigured('RMC_WEB_ENV must be production, staging or test')

def secret(name, required=True):
    filename = os.environ.get(name + '_FILE')
    value = Path(filename).read_text().strip() if filename else os.environ.get(name, '')
    if required and len(value) < 32:
        raise ImproperlyConfigured(name + ' must be configured privately (32+ characters)')
    return value

SECRET_KEY = secret('RMC_WEB_SECRET_KEY')
MFA_ENCRYPTION_KEY = secret('RMC_WEB_MFA_KEY')
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
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend','allauth.account.auth_backends.AuthenticationBackend']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher','django.contrib.auth.hashers.PBKDF2PasswordHasher']
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
                            {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
                            {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
                            {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*','password1*','password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if ENVIRONMENT == 'production' else 'http'
MFA_SUPPORTED_TYPES = ['totp','recovery_codes']
MFA_TOTP_ISSUER = 'ResMgrCheck'
USERSESSIONS_TRACK_ACTIVITY = True
EMAIL_BACKEND = os.environ.get('RMC_WEB_EMAIL_BACKEND','django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('RMC_WEB_EMAIL_HOST','127.0.0.1')
EMAIL_PORT = int(os.environ.get('RMC_WEB_EMAIL_PORT','587'))
EMAIL_HOST_USER = os.environ.get('RMC_WEB_EMAIL_USER','')
EMAIL_HOST_PASSWORD = os.environ.get('RMC_WEB_EMAIL_PASSWORD','')
EMAIL_USE_TLS = os.environ.get('RMC_WEB_EMAIL_TLS','1') == '1'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get('RMC_WEB_FROM_EMAIL','ResMgrCheck <noreply@qnx-resmgrcheck.gestionatech.de>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
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
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
CACHES = {'default':{'BACKEND':'django.core.cache.backends.db.DatabaseCache','LOCATION':'control_cache'}}
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},
           'root':{'handlers':['console'],'level':'WARNING'},'loggers':{'django.request':{'handlers':['console'],'level':'ERROR','propagate':False}}}
# No request bodies, credentials or raw provider errors are logged.
EMAIL_FILE_PATH = PRIVATE_ROOT / 'mail'
