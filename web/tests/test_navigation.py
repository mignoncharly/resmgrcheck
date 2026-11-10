"""Real authorized routes and local browser rendering; no native execution."""
import json,os,re,sys,uuid,tempfile,subprocess,copy
from pathlib import Path
from html.parser import HTMLParser
from django.test import TestCase,override_settings,Client
from django.urls import reverse
from django.conf import settings
from control.models import Target,BuildRelease,Run
from .helpers import tenant,signed_client

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href','').startswith('/'):self.links.append(attrs['href'])

@override_settings(ADMIN_MFA_REQUIRED=False)
class NavigationTests(TestCase):
    def setUp(self):
        self.owner,self.org,self.project=tenant('Navigation lab','navigation@example.test',mfa=False)
        self.client=signed_client(self.owner)
        self.target=Target.objects.create(project=self.project,name='Navigation target',approved=True,state='available',kind='managed-lab')
        manifest=json.loads((settings.REPO_ROOT/'docs/evidence/phase10/original-deployment.json').read_text())
        self.build=BuildRelease.objects.create(target=self.target,label='Recorded approved fixture',manifest=manifest,approved=True)
        self.run=Run.objects.create(project=self.project,target=self.target,build=self.build,actor=self.owner,native_run_id='navigation-not-executed',operation='run',profile='sensor',suite='profile',fixture_mode='fixed',state='rejected',idempotency_key='navigation-fixture',intent_sha256='0'*64,actor_auth_hash='0'*64,mfa_at=self.owner.date_joined)
        self.routes=[('overview',[]),('projects',[]),('project',[self.project.pk]),('target_list',[]),('targets',[self.project.pk]),('new_run',[self.project.pk]),('run_history',[]),('run_detail',[self.run.pk]),('replay_run',[self.run.pk]),('compare',[]),('team',[self.org.pk]),('access_codes',[self.org.pk]),('audit_log',[self.org.pk]),('retention',[self.org.pk]),('ai_settings',[self.project.pk]),('upload_source',[self.project.pk]),('administrator_settings',[]),('usersessions_list',[]),('account_change_password',[]),('organization_create',[]),('project_create',[self.org.pk])]

    def test_browser_captures(self):
        phase=os.environ.get('RMC_NAV_CAPTURE','after')
        root=settings.REPO_ROOT;out=root/'.local/web/evidence/global-navigation';out.mkdir(parents=True,exist_ok=True)
        if phase=='before':
            temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
            for name in ['base.html','partials/mobile_nav.html','project.html']:
                path=Path(temporary.name)/'control'/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(subprocess.check_output(['git','show','HEAD:web/control/templates/control/'+name]))
            templates=copy.deepcopy(settings.TEMPLATES);templates[0]['DIRS']=[temporary.name,*templates[0]['DIRS']]
            override=override_settings(TEMPLATES=templates);override.enable();self.addCleanup(override.disable)
        clients={'project':self.client,'run':self.client}
        if phase!='before':
            from control.access import create_code
            _,raw=create_code(self.owner,self.org,'Browser navigation viewer',[{'project':self.project,'targets':[self.target],'all_evidence':True}])
            restricted=Client();self.assertEqual(restricted.post(reverse('developer_access'),{'code':raw}).status_code,302)
            clients.update({'code-project':restricted,'code-run':restricted})
        paths={label:reverse('project',args=[self.project.pk]) if label.endswith('project') else reverse('run_detail',args=[self.run.pk]) for label in clients}
        pages={label:client.get(paths[label]).content.decode() for label,client in clients.items()}
        for site in (root/'.local/browser-test/lib').glob('python*/site-packages'):sys.path.append(str(site))
        from playwright.sync_api import sync_playwright
        captures={}
        for label,client in clients.items():
            captures[label]={}
            for path in [reverse('projects'),reverse('overview'),*set(paths.values())]:
                body=client.get(path).content.decode()
                body=re.sub(r'<script.*?</script>','',body);body=re.sub(r'<link[^>]+>','',body)
                css=subprocess.check_output(['git','show','HEAD:web/control/static/control/app.css']).decode() if phase=='before' else (root/'web/control/static/control/app.css').read_text()
                captures[label][path]=body.replace('</head>','<style>'+css+'</style></head>')
        checks=[]
        with sync_playwright() as p:
            b=p.chromium.launch(executable_path='/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
            for label,html in pages.items():
                html=re.sub(r'<script.*?</script>','',html);html=re.sub(r'<link[^>]+>','',html);html=html.replace('</head>','<style>'+(subprocess.check_output(['git','show','HEAD:web/control/static/control/app.css']).decode() if phase=='before' else (root/'web/control/static/control/app.css').read_text())+'</style></head>')
                for width in [1440,900,390,320]:
                    for js in [True,False]:
                        c=b.new_context(viewport={'width':width,'height':1000},java_script_enabled=js);page=c.new_page()
                        from urllib.parse import urlsplit
                        page.route('http://navigation.test/**',lambda route:route.fulfill(status=200,content_type='text/html',body=captures[label][urlsplit(route.request.url).path]))
                        page.goto('http://navigation.test'+paths[label])
                        self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                        if width<760:
                            page.locator('.mobile-menu summary').click();self.assertTrue(page.locator('.mobile-menu nav').is_visible());page.locator('.mobile-menu summary').click()
                        page.keyboard.press('Tab');page.locator('.skip').focus();self.assertNotEqual(page.locator('.skip').evaluate('e=>getComputedStyle(e).outlineStyle'),'none')
                        issues=[]
                        if js:
                            page.evaluate((root/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text());issues=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>v.id)")
                            if phase!='before':self.assertEqual(issues,[])
                        page.locator('.skip').evaluate('e=>e.blur()')
                        if not label.startswith('code-'):page.screenshot(path=str(out/f'{phase}-{label}-{width}{"-no-js" if not js else ""}.png'),full_page=True)
                        if phase!='before':
                            page.get_by_role('navigation',name='Return to section').get_by_role('link',name='Back to Projects',exact=True).click()
                            self.assertEqual(urlsplit(page.url).path,reverse('projects'))
                            page.get_by_role('navigation',name='Breadcrumb',exact=True).get_by_role('link',name='Dashboard',exact=True).click()
                            self.assertEqual(urlsplit(page.url).path,reverse('overview'))
                            page.goto('http://navigation.test'+paths[label]);page.reload();self.assertTrue(page.locator('h1').is_visible())
                        checks.append({'forward_parent_dashboard_and_refresh':phase!='before','page':label,'width':width,'javascript':js,'overflow':False,'axe_violations':issues if js else 'not_run','keyboard_focus':True,'mobile_menu':'passed' if width<760 else 'not_applicable'});c.close()
            b.close()
        (out/f'{phase}-checks.json').write_text(json.dumps({'fixture':'Actual Django routes and disposable database identities; static rendering for browser checks','checks':checks},indent=2)+'\n')

    def nav_links(self,response):
        from control.templatetags.navigation import app_navigation
        context=dict(response.context.flatten()) if hasattr(response.context,'flatten') else {}
        # Inspect the same model used by all three shared components.
        for ctx in response.context:
            try:context.update(ctx.flatten())
            except AttributeError:pass
        context['request']=response.wsgi_request
        return app_navigation(context)

    def test_every_main_section_and_nested_route_has_authorized_parents(self):
        links=set()
        for name,args in self.routes:
            path=reverse(name,args=args)
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,(name,response.status_code))
            nav=self.nav_links(response)
            self.assertTrue(nav['crumbs'],name)
            self.assertEqual(sum(e['active'] for e in nav['sections']),1,name)
            expected={'targets':'targets','project':'projects','run_detail':'runs','replay_run':'runs','ai_settings':'projects','team':'security','account_change_password':'security','compare':'compare'}.get(name)
            if expected:self.assertEqual(next(e['key'] for e in nav['sections'] if e['active']),expected)
            for e in nav['sections']+nav['crumbs']+nav['backs']:
                if e.get('url'):links.add(e['url'])
            self.assertEqual(self.client.get(path).status_code,200) # Direct refresh.
            if name in {'project','targets','new_run','run_detail','replay_run','ai_settings','upload_source'}:
                self.assertIn(reverse('projects'),[e['url'] for e in nav['backs']],name)
        for link in links:self.assertEqual(self.client.get(link).status_code,200,link)

    def test_run_returns_to_authorized_project_and_filtered_history(self):
        response=self.client.get(reverse('run_detail',args=[self.run.pk]),{'history_state':'rejected','history_service':'sensor'});nav=self.nav_links(response)
        self.assertEqual(next(e['key'] for e in nav['sections'] if e['active']),'runs')
        history=next(e['url'] for e in nav['backs'] if e['label']=='Back to project runs')
        self.assertIn('state=rejected',history);self.assertIn('service=sensor',history)
        response=self.client.get(history);self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['project'],self.project);self.assertEqual(list(response.context['runs']),[self.run])
        self.assertContains(response,'name="project"')
        _,_,foreign=tenant('Foreign navigation','foreign-nav@example.test',mfa=False)
        self.assertEqual(self.client.get(reverse('run_history'),{'project':foreign.pk}).status_code,404)
        self.assertEqual(self.client.get(reverse('run_history'),{'project':'invalid'}).status_code,404)

    def test_code_session_never_links_administrator_or_ungranted_project(self):
        from control.access import create_code
        code,raw=create_code(self.owner,self.org,'Navigation restricted viewer',[{'project':self.project,'targets':[self.target],'all_evidence':True}])
        client=Client();self.assertEqual(client.post(reverse('developer_access'),{'code':raw}).status_code,302)
        for name,args in [('overview',[]),('projects',[]),('targets',[self.project.pk]),('project',[self.project.pk]),('run_detail',[self.run.pk]),('account_settings',[])]:
            response=client.get(reverse(name,args=args));self.assertEqual(response.status_code,200,name)
            nav=self.nav_links(response)
            for entry in nav['sections']+nav['crumbs']+nav['backs']:
                if entry.get('url'):
                    self.assertFalse(entry['url'].startswith('/administrator/'))
                    self.assertEqual(client.get(entry['url']).status_code,200,entry['url'])
        self.assertEqual(client.get(reverse('administrator_settings')).status_code,404)
        from django.utils import timezone
        code.revoked_at=timezone.now();code.save(update_fields=['revoked_at'])
        response=client.get(reverse('project',args=[self.project.pk]));self.assertEqual(response.status_code,302)
        self.assertNotContains(client.get(response.url),'Navigation lab')

    def test_anonymous_and_revoked_admin_do_not_get_context_links(self):
        self.assertEqual(Client().get(reverse('project',args=[self.project.pk])).status_code,302)
        self.owner.session_version+=1;self.owner.save(update_fields=['session_version'])
        response=self.client.get(reverse('project',args=[self.project.pk]));self.assertEqual(response.status_code,302)

    def test_runner_ai_source_and_code_detail_have_real_closer_parents(self):
        from control.models import CustomerRunner,SourceSubmission,AIAnalysis
        from control.access import create_code
        from django.utils import timezone
        runner_target=Target.objects.create(project=self.project,name='Runner navigation fixture',kind='customer-runner')
        from .test_runners import discovery
        CustomerRunner.objects.create(target=runner_target,public_key='a'*64,inventory=discovery(),inventory_sha256='b'*64)
        source=SourceSubmission.objects.create(project=self.project,actor=self.owner,label='Navigation source fixture',original_sha256='a'*64,redacted_sha256='b'*64,redacted_text='/* navigation fixture */',expires_at=timezone.now())
        analysis=AIAnalysis.objects.create(run=self.run,actor=self.owner,actor_auth_hash='0'*64,mfa_at=timezone.now(),idempotency_key='navigation-analysis',task='explain',input_sha256='a'*64,provider='disabled',requested_model='unavailable',reserved_microusd=0,accounted_microusd=0,state='cancelled')
        code,_=create_code(self.owner,self.org,'Navigation detail fixture',[{'project':self.project,'targets':[self.target]}])
        for name,args,parent in [('runner_detail',[self.project.pk,runner_target.pk],reverse('targets',args=[self.project.pk])),('source_detail',[source.pk],reverse('project',args=[self.project.pk])),('ai_detail',[analysis.pk],reverse('run_detail',args=[self.run.pk])),('code_detail',[code.pk],reverse('access_codes',args=[self.org.pk]))]:
            response=self.client.get(reverse(name,args=args));self.assertEqual(response.status_code,200,name)
            nav=self.nav_links(response);urls=[e['url'] for e in nav['crumbs']+nav['backs'] if e.get('url')]
            self.assertIn(parent,urls,name)
            if name in {'runner_detail','source_detail','ai_detail'}:
                from control.templatetags.navigation import app_navigation
                fallback=app_navigation({'request':response.wsgi_request})
                self.assertIn(parent,[e['url'] for e in fallback['crumbs']+fallback['backs'] if e.get('url')],name)
            for url in urls:self.assertEqual(self.client.get(url).status_code,200,url)
