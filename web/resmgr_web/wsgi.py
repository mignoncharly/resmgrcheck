import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','resmgr_web.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from django.conf import settings
if settings.ENVIRONMENT=='production' and settings.SERVICE_ROLE!='web':
    raise RuntimeError('Only the web service role may expose WSGI')
