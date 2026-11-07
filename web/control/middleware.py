from django.conf import settings
from django.http import HttpResponse
from .security import consume_rate

class PolicyMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.method=='POST':
            # Nginx overwrites X-Real-IP; only trust it behind the private production socket.
            peer=request.META.get('REMOTE_ADDR','')
            if settings.ENVIRONMENT=='production' and peer in {'','127.0.0.1','::1'}:
                peer=request.META.get('HTTP_X_REAL_IP',peer)
            identity=str(request.user.pk) if request.user.is_authenticated else peer
            if request.path.startswith('/accounts/signup'):
                allowed=consume_rate('signup',peer,6,3600)
            elif request.path.startswith('/accounts/'):
                allowed=consume_rate('account',identity,30,60)
            else:allowed=consume_rate('mutation',identity,60,60)
            if not allowed:
                response=HttpResponse('Request limit reached. Try again shortly.',status=429)
                response['Retry-After']='60';return response
        response=self.get_response(request)
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['Cache-Control']='no-store' if request.user.is_authenticated or request.path.startswith('/accounts/') else 'no-cache'
        return response
