from django.conf import settings
from django.http import HttpResponse
from .security import consume_rate

class AdministratorSessionMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        from django.contrib.auth import logout
        from django.utils import timezone
        from .security import is_code,audit
        if request.user.is_authenticated and not is_code(request.user):
            now=timezone.now().timestamp();started=request.session.get('rmc_admin_started_at');seen=request.session.get('rmc_admin_last_seen')
            valid=(isinstance(started,(int,float)) and isinstance(seen,(int,float)) and
                now-settings.ADMIN_SESSION_ABSOLUTE_SECONDS<started<=now+5 and now-settings.ADMIN_SESSION_IDLE_SECONDS<seen<=now+5)
            if not valid:
                audit(request.user,'administrator.session_expired');logout(request)
            else:request.session['rmc_admin_last_seen']=now
        return self.get_response(request)

class PolicyMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        from .security import is_code
        if not settings.ADMIN_MFA_REQUIRED and request.path.startswith('/administrator/2fa/'):
            return HttpResponse('Not found.',status=404)
        if request.path.startswith('/administrator/') and is_code(request.user):
            return HttpResponse('Administrator access required. Sign out before administrator login.',status=404)
        if request.method=='POST':
            # Nginx overwrites X-Real-IP; only trust it behind the private production socket.
            peer=request.META.get('REMOTE_ADDR','')
            if settings.ENVIRONMENT=='production' and peer in {'','127.0.0.1','::1'}:
                peer=request.META.get('HTTP_X_REAL_IP',peer)
            identity=str(request.user.pk) if request.user.is_authenticated else peer
            if request.path.startswith('/runner/v1/'):
                allowed=consume_rate('runner-ingress',peer,600,60)
            elif request.path=='/access/':
                allowed=consume_rate('code-redemption-ip',peer,10,60) and consume_rate('code-redemption-global','all',200,3600)
            elif request.path.startswith('/administrator/'):
                if request.path.endswith('/login/'):
                    name=str(request.POST.get('login','')).strip().lower()[:80]
                    allowed=consume_rate('administrator-login-ip',peer,10,60) and consume_rate('administrator-login-name',name,10,900)
                else:allowed=consume_rate('administrator',identity,30,60)
            else:allowed=consume_rate('mutation',identity,60,60)
            if not allowed:
                response=HttpResponse('Request limit reached. Try again shortly.',status=429)
                response['Retry-After']='60';return response
        response=self.get_response(request)
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['Cache-Control']='no-store' if request.user.is_authenticated or request.path.startswith(('/access/','/administrator/','/runner/')) else 'no-cache'
        return response
