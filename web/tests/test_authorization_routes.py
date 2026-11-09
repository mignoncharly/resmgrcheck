"""Enumerate exposed routes; real DB principals, no production accounts or keys."""
import re,uuid
from datetime import timedelta
import time
from django.conf import settings
from django.test import TestCase,Client,override_settings
from django.urls import get_resolver,URLResolver,resolve,reverse
from django.utils import timezone
from control.access import create_code
from .helpers import tenant,signed_client

UNKNOWN=uuid.UUID('91116d07-5158-46ac-aeb0-790815735df6')
def routes(patterns=None,prefix=''):
    for row in patterns or get_resolver().url_patterns:
        value=prefix+str(row.pattern)
        if isinstance(row,URLResolver):yield from routes(row.url_patterns,value)
        else:
            value=re.sub(r'<uuid:[^>]+>',str(UNKNOWN),value)
            value=re.sub(r'<int:[^>]+>','999999',value)
            value=re.sub(r'<(?:str|path):([^>]+)>',lambda m:'enroll' if m[1]=='operation' else 'before' if m[1]=='selection' else 'unused',value)
            if '<' not in value:yield '/'+value,row.callback

@override_settings(RUNNER_ENABLED=False)
class RouteBoundaryTests(TestCase):
    def setUp(self):
        self.user,self.org,self.project=tenant('Route review','route-review@example.test')
        _,self.raw=create_code(self.user,self.org,'Route-scoped viewer',[{'project':self.project,'targets':[],'all_evidence':False}],max_sessions=2)
        self.viewer=Client();self.assertEqual(self.viewer.post('/access/',{'code':self.raw}).status_code,302)
        self.admin=signed_client(self.user,mfa=True)
    def test_every_registered_private_route_denies_anonymous_get_and_post(self):
        covered=[]
        for path,_ in routes():
            if not path.startswith(('/app/','/api/','/administrator/')) or path=='/administrator/login/':continue
            covered.append(path)
            for method in ['get','post']:
                response=getattr(self.client,method)(path)
                self.assertIn(response.status_code,{302,303,403,404,405,429},(path,method,response.status_code))
                self.assertNotIn(response.status_code,{200,201,202,500},path)
        self.assertGreaterEqual(len(covered),40)
    def test_access_principal_cannot_enter_any_administrator_or_foreign_object_route(self):
        for path,_ in routes():
            if path.startswith('/administrator/'):
                self.assertEqual(self.viewer.get(path).status_code,404,path)
                self.assertIn(self.viewer.post(path).status_code,{404,429},path)
        for path in ['/api/projects/'+str(UNKNOWN)+'/','/app/projects/'+str(UNKNOWN)+'/',
                '/app/runs/'+str(UNKNOWN)+'/','/api/runs/'+str(UNKNOWN)+'/']:
            self.assertEqual(self.viewer.get(path).status_code,404,path)
    def test_only_machine_endpoint_is_csrf_exempt_and_disabled_for_all_principals(self):
        exemptions={path for path,view in routes() if getattr(view,'csrf_exempt',False)}
        self.assertEqual(exemptions,{'/runner/v1/enroll/'})
        for client in [self.client,self.viewer,self.admin]:
            for operation in ['enroll','exchange','unknown']:
                self.assertEqual(client.post('/runner/v1/'+operation+'/',data='{}',content_type='application/json').status_code,404)
        checked=Client(enforce_csrf_checks=True)
        for path in ['/access/','/administrator/login/','/sign-out/']:
            self.assertEqual(checked.post(path,{'code':'not-a-secret'}).status_code,403,path)
    def test_code_idle_and_absolute_expiry_are_enforced_by_real_middleware(self):
        from control.models import AccessSession
        session=AccessSession.objects.get()
        AccessSession.objects.filter(pk=session.pk).update(last_access=timezone.now()-timedelta(minutes=31))
        self.assertEqual(self.viewer.get('/app/').status_code,302)
        fresh=Client();self.assertEqual(fresh.post('/access/',{'code':self.raw}).status_code,302)
        AccessSession.objects.filter(pk=fresh.session['rmc_access_session']).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(fresh.get('/app/').status_code,302)
    def test_administrator_objects_still_require_recent_password_and_membership(self):
        self.assertEqual(self.admin.get(reverse('project',args=[self.project.pk])).status_code,200)
        stale=signed_client(self.user)
        session=stale.session;session['account_authentication_methods'][0]['at']=time.time()-1000;session.save()
        self.assertIn('reauthenticate',stale.get(reverse('access_codes',args=[self.org.pk])).url)
        self.assertEqual(self.admin.get(reverse('project',args=[UNKNOWN])).status_code,404)
