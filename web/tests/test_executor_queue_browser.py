"""Actual HTTP-form/database-role reproduction, without a worker or QNX launch."""
import json,logging,re,sys,uuid
from unittest.mock import patch
from pathlib import Path
from django.test import TestCase,TransactionTestCase,Client,override_settings
from django.db import connection,connections,transaction,DatabaseError
from control.models import Target,BuildRelease,Run,ExecutorSlot
from control.access import create_code
from .helpers import tenant
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
import executor_plan as plan
from executor_native_browser import NativeJourney

def web_role(template='resmgr_web'):
    name='queue_role_'+uuid.uuid4().hex[:12];quote=connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute('CREATE ROLE '+quote(name)+' NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        cursor.execute('GRANT USAGE ON SCHEMA public TO '+quote(name))
        cursor.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO '+quote(name))
        cursor.execute('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO '+quote(name))
        source=(plan.SOURCE/'web/ops/production/database-grants.sql').read_text()
        for match in re.finditer(r'GRANT\s+[^;]+;',source):
            command=match[0];parts=re.split(r'\bTO\s+',command,maxsplit=1)
            if len(parts)!=2 or ' ON DATABASE ' in command:continue
            roles={value.strip() for value in parts[1].rstrip(';').split(',')}
            if template in roles:cursor.execute(parts[0]+'TO '+quote(name))
    return name

def fixture():
    actor,organization,project=tenant('Queue browser fixture','queue-browser@example.test',mfa=False)
    from resmgrcheck.contracts import Profile,load
    caps={name+'-v1':Profile.parse(load(plan.SOURCE/'profiles'/(name+'.json'))).data['capabilities']['required'] for name in ['sensor','job']}
    target=Target.objects.create(project=project,name='Isolated approved lab',kind='managed-lab',approved=True,state='available',inventory={'compiled_adapters':caps})
    pair=plan.manifest_pair(plan.SOURCE)
    builds={name:BuildRelease.objects.create(target=target,label=name,approved=True,manifest=value) for name,value in pair.items()}
    code,raw=create_code(actor,organization,'Queue browser fixture',[{'project':project,'targets':[target],'can_run':True,'can_download':True,'all_evidence':True}],allow_live=True)
    return project,target,builds,raw

@override_settings(ADMIN_MFA_REQUIRED=False,ALLOWED_HOSTS=['testserver'],CSRF_TRUSTED_ORIGINS=['https://testserver'])
class WebQueueRoleTests(TestCase):
    def setUp(self):
        silence=patch.object(logging.getLogger('django.request'),'disabled',True);silence.start();self.addCleanup(silence.stop)
        self.project,self.target,self.builds,raw=fixture();self.role=web_role()
        self.client=Client(enforce_csrf_checks=True,HTTPS='on',HTTP_ORIGIN='https://testserver')
        self.post('/access/',{'code':raw})
        self.path='/app/projects/'+str(self.project.pk)+'/runs/new/'
        self.data={'target':str(self.target.pk),'build':str(self.builds['before'].pk),'profile':'sensor','suite':'profile',
            'fixture_mode':'ignore-unblock','idempotency_key':'isolated-browser-queue-key'}
    def post(self,path,data):
        page=self.client.get(path);self.assertEqual(page.status_code,200)
        token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.content.decode()).group(1)
        return self.client.post(path,{**data,'csrfmiddlewaretoken':token})
    def test_actual_web_role_previews_but_confirmation_cannot_create_dispatch_sentinel(self):
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+connection.ops.quote_name(self.role))
            try:
                preview=self.post(self.path,self.data);self.assertEqual(preview.status_code,200)
                self.assertFalse(preview.context['form'].errors);self.assertContains(preview,'Confirm and queue')
                data={**self.data,'confirmed':'on','confirmation':preview.context['form'].data['confirmation']}
                with self.assertRaisesRegex(DatabaseError,'control_executorslot'),transaction.atomic():self.post(self.path,data)
            finally:cursor.execute('RESET ROLE')
        self.assertEqual(Run.objects.count(),0)
    def test_existing_sentinel_alone_still_lacks_select_for_update_permission(self):
        ExecutorSlot.objects.create(name='dispatch')
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+connection.ops.quote_name(self.role))
            try:
                with self.assertRaisesRegex(DatabaseError,'control_executorslot'),transaction.atomic():
                    cursor.execute("SELECT name FROM control_executorslot WHERE name='dispatch' FOR UPDATE")
            finally:cursor.execute('RESET ROLE')

    def test_guarded_lock_permission_allows_real_HTTP_confirmation_but_no_lease_writes(self):
        from web_dispatch_locking import install
        install(connection,role=self.role,prefix='web_guard_'+uuid.uuid4().hex[:10])
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+connection.ops.quote_name(self.role))
            try:
                preview=self.post(self.path,self.data);self.assertEqual(preview.status_code,200)
                data={**self.data,'confirmed':'on','confirmation':preview.context['form'].data['confirmation']}
                queued=self.post(self.path,data);self.assertEqual(queued.status_code,302)
                self.assertEqual(self.post(self.path,data).url,queued.url)
                with self.assertRaisesRegex(DatabaseError,'web_dispatch_update_forbidden'),transaction.atomic():
                    cursor.execute("UPDATE public.control_executorslot SET name=name WHERE name='dispatch'")
                for statement in ["INSERT INTO public.control_executorslot(name) VALUES('private-qnx')", "DELETE FROM public.control_executorslot", "UPDATE public.control_executorslot SET token=NULL", "ALTER TABLE public.control_executorslot DISABLE TRIGGER ALL"]:
                    with self.assertRaises(DatabaseError),transaction.atomic():cursor.execute(statement)
            finally:cursor.execute('RESET ROLE')
        run=Run.objects.get();self.assertEqual(run.fixture_mode,'ignore-unblock');self.assertIsNotNone(run.access_session_id)
        self.assertEqual(run.state,'queued');self.assertIsNone(run.started_at)
        executor=web_role('resmgr_exec')
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE '+connection.ops.quote_name(executor))
            try:
                cursor.execute("INSERT INTO public.control_executorslot(name) VALUES('private-qnx')")
                cursor.execute("UPDATE public.control_executorslot SET run_id=%s,token=%s,expires_at=CURRENT_TIMESTAMP WHERE name='private-qnx'",[run.pk,uuid.uuid4()])
                cursor.execute("UPDATE public.control_executorslot SET run_id=NULL,token=NULL,expires_at=NULL WHERE name='private-qnx'")
            finally:cursor.execute('RESET ROLE')

    def test_occupied_mutex_is_preserved_and_permission_changes_roll_back(self):
        from web_dispatch_locking import install
        marker=uuid.uuid4();ExecutorSlot.objects.create(name='dispatch',token=marker)
        with self.assertRaisesRegex(ValueError,'dispatch_sentinel_missing_or_occupied'),transaction.atomic():
            install(connection,role=self.role,prefix='web_guard_'+uuid.uuid4().hex[:10])
        self.assertEqual(ExecutorSlot.objects.get(name='dispatch').token,marker)
        with connection.cursor() as cursor:
            cursor.execute("SELECT has_column_privilege(%s,'control_executorslot','name','UPDATE')",[self.role]);self.assertFalse(cursor.fetchone()[0])

@override_settings(ADMIN_MFA_REQUIRED=False,ALLOWED_HOSTS=['testserver'],CSRF_TRUSTED_ORIGINS=['https://testserver'])
class ChromiumQueueRoleTests(TransactionTestCase):
    @patch.object(logging.getLogger('django.request'),'disabled',True)
    def test_actual_chromium_queue_reproduces_500_then_confirms_under_restricted_role(self):
        import tempfile
        import threading
        from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
        from concurrent.futures import ThreadPoolExecutor
        from urllib.parse import urlsplit
        from types import MethodType
        for site in (plan.SOURCE/'.local/browser-test/lib').glob('python*/site-packages'):
            if str(site) not in sys.path:sys.path.append(str(site))
        from playwright.sync_api import sync_playwright,TimeoutError as BrowserTimeout
        binary=Path('/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
        self.assertTrue(binary.is_file());self.assertTrue(connection.settings_dict['NAME'].startswith('test_'))
        project,target,builds,raw=fixture();role=web_role();prefix='web_browser_'+uuid.uuid4().hex[:10]
        client=Client(enforce_csrf_checks=True,HTTPS='on',HTTP_ORIGIN='https://testserver')
        page=client.get('/access/');token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.content.decode()).group(1)
        self.assertEqual(client.post('/access/',{'code':raw,'csrfmiddlewaretoken':token}).status_code,302);raw=None
        requests=[];streamed=[];database=ThreadPoolExecutor(max_workers=1)
        def http(method,path,body,content_type):
            from django.http import HttpResponse
            with connection.cursor() as cursor:
                cursor.execute('SET ROLE '+connection.ops.quote_name(role))
                try:
                    try:response=client.generic(method,path,body,content_type=content_type)
                    except DatabaseError:response=HttpResponse(status=500)
                    if method=='POST':requests.append(response.status_code)
                    if response.streaming:
                        body=b''.join(response.streaming_content);streamed.append((response.status_code,len(body)))
                    else:body=response.content
                    return response.status_code,dict(response.items()),body
                finally:cursor.execute('RESET ROLE')
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.respond()
            def do_POST(self):self.respond()
            def respond(self):
                raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
                status,headers,body=database.submit(http,self.command,self.path,raw,self.headers.get('Content-Type','application/octet-stream')).result(timeout=10)
                self.send_response(status)
                for key,value in headers.items():
                    if key.lower() not in {'content-length','transfer-encoding'}:self.send_header(key,value)
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def visit(journey,document,path,label,mode='desktop',**unused):
            journey.step=label;response=document.goto(journey.origin+path,wait_until='networkidle')
            self.assertEqual(response.status,200);return response
        try:
            with tempfile.TemporaryDirectory() as temporary,sync_playwright() as runtime:
                browser=runtime.chromium.launch(executable_path=str(binary));context=browser.new_context()
                request_failures=[];context.on('requestfailed',lambda request:request_failures.append(request.failure))
                document=context.new_page();document.set_default_timeout(1200);document.set_default_navigation_timeout(1200)
                credentials={'native':{'project_id':str(project.pk),'target_id':str(target.pk)}}
                journey=NativeJourney('http://127.0.0.1:'+str(server.server_port),Path(temporary),credentials);journey.visit=MethodType(visit,journey)
                with self.assertRaisesRegex(AssertionError,'native_confirm_not_accepted'):journey.queue(document,'sensor',str(builds['before'].pk),mode='ignore-unblock')
                self.assertEqual(requests,[200,500]);self.assertEqual(database.submit(lambda:Run.objects.count()).result(),0)
                self.assertEqual(journey.results['native_form_requests'],[{'stage':'native-preview','status':200},{'stage':'native-confirm','status':500}])
                from web_dispatch_locking import install
                database.submit(lambda:install(connection,role=role,prefix=prefix)).result();requests.clear()
                row=journey.queue(document,'sensor',str(builds['before'].pk),mode='ignore-unblock')
                saved=database.submit(lambda:Run.objects.get()).result()
                self.assertEqual(requests,[200,302]);self.assertEqual(str(saved.pk),row['web_run_id'])
                self.assertIsNone(saved.started_at);document.wait_for_load_state('networkidle')
                self.assertTrue(streamed);self.assertTrue(all(status==200 and size>0 for status,size in streamed))
                self.assertEqual(request_failures,[]);browser.close()
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()
            database.submit(connections.close_all).result(timeout=5);database.shutdown(wait=True)
            with connection.cursor() as cursor:
                cursor.execute('DROP FUNCTION IF EXISTS public.'+connection.ops.quote_name(prefix+'_guard')+'() CASCADE')
                cursor.execute('DROP OWNED BY '+connection.ops.quote_name(role));cursor.execute('DROP ROLE '+connection.ops.quote_name(role))
