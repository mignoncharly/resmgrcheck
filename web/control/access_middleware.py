import hmac,uuid
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .access import browser_binding
from .models import AccessSession,AccessCode
from .security import AccessPrincipal,session_valid,audit

class AccessSessionMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        identifier=request.session.get('rmc_access_session')
        if identifier and not request.user.is_authenticated:
            try:identifier=uuid.UUID(identifier)
            except (ValueError,TypeError):identifier=None
            session=AccessSession.objects.select_related('code__organization').filter(pk=identifier).first() if identifier else None
            if session and session_valid(session) and hmac.compare_digest(session.browser_key_hash,browser_binding(request.session.session_key or '')):
                request.user=AccessPrincipal(session)
                now=timezone.now()
                AccessSession.objects.filter(pk=session.pk,revoked_at=None).update(last_access=now)
                AccessCode.objects.filter(pk=session.code_id).update(last_access=now)
            else:request.session.flush();request.user=AnonymousUser()
        return self.get_response(request)
