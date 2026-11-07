from django.conf import settings
from django.utils import timezone
from .security import is_code

def product(request):
    code=is_code(request.user)
    return {'environment':settings.ENVIRONMENT,'now':timezone.now(),'product_version':'ResMgrCheck Web',
        'is_account_page':request.path.startswith(('/administrator/','/access/')),
        'is_access_code':code,'is_administrator':request.user.is_authenticated and not code and request.user.is_staff,
        'live_allowed':not code or request.user.access_session.code.allow_live,
        'ai_allowed':not code or request.user.access_session.code.allow_ai}
