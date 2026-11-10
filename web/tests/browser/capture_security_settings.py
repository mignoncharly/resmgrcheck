"""Local rendered-template captures; synthetic display data, no production access.
Run through staging manage.py shell with exec(open(this_file).read()).
RMC_SECURITY_CAPTURE_PHASE controls the artifact label (default after).
"""
import json,re,sys,os
from pathlib import Path
from django.test import RequestFactory
from django.template.loader import render_to_string
from control.models import User
from control.forms import PasswordConfirmation
from django.contrib.sessions.backends.db import SessionStore
root=Path('/home/mignon/projects/resmgrcheck');mode=os.environ.get('RMC_SECURITY_CAPTURE_PHASE','after')
u=User(username='local-preview-admin',is_staff=True,is_active=True);u.pk='11111111-1111-1111-1111-111111111111'
r=RequestFactory().get('/administrator/settings/');r.user=u;r.session=SessionStore();r.session._session_key='preview-only'
from django.utils import timezone
from types import SimpleNamespace
rows=[SimpleNamespace(created_at=timezone.now(),last_seen_at=timezone.now(),current=True)]
html=render_to_string('control/account.html',{'user':u,'sessions_form':PasswordConfirmation(),'sessions':rows,**({'is_account_page':False} if mode=='after' else {})},request=r)
html=re.sub(r'<script.*?</script>','',html);html=re.sub(r'<link[^>]+>','',html);html=html.replace('</head>','<style>'+(root/'web/control/static/control/app.css').read_text()+'</style></head>')
for site in (root/'.local/browser-test/lib').glob('python*/site-packages'):sys.path.append(str(site))
from playwright.sync_api import sync_playwright
out=root/'.local/web/evidence/administrator-security-redesign';out.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/home/mignon/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell')
 for label,width in [('desktop',1440),('tablet',900),('mobile',390),('small-mobile',320)]:
  for js in [True,False]:
   ctx=b.new_context(viewport={'width':width,'height':1000},java_script_enabled=js);page=ctx.new_page();page.set_content(html);page.screenshot(path=str(out/f'{mode}-{label}{"-no-js" if not js else ""}.png'),full_page=True)
   page.locator('input[name=password]').focus()
   assert page.locator('input[name=password]').evaluate("el=>getComputedStyle(el).outlineStyle!='none'")
   overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth');issues=[]
   if js:
    page.evaluate((root/'.local/web/browser/node_modules/axe-core/axe.min.js').read_text());issues=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(x=>({id:x.id,impact:x.impact}))")
   assert not overflow
   if mode=='after':assert not issues,issues
   checks.append({'keyboard_focus_visible':True,'width':width,'javascript':js,'overflow':overflow,'violations':issues});ctx.close()
 b.close()
(out/f'{mode}-checks.json').write_text(json.dumps({'fixture':'Local template preview; synthetic display identity/session; no production access','checks':checks},indent=2))
print(json.dumps(checks))
