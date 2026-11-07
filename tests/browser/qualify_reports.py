#!/usr/bin/env python3
"""Optional local Chromium qualification; never a QNX execution or product dependency."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
from resmgrcheck.artifacts import create_bundle, evaluator_identity, sha256, inspect_bundle
from resmgrcheck.contracts import canonical, load
from resmgrcheck.exports import junit
from resmgrcheck.reports import report
from resmgrcheck.workflow import compare_executions

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True)
args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
start=evaluator_identity()
runs=Path('docs/evidence/phase7/executions')
# Snapshot source artifacts, including sealed results and raw streams. Derived
# reports are written elsewhere and cannot rewrite JSON/JUnit/native observations.
inputs=[p for p in runs.rglob('*') if p.is_file()]
before={str(p):sha256(p.read_bytes()) for p in inputs}
reports={};origins={}
for name,source in [('fixed',runs/'sensor-fixed'),('broken',runs/'sensor-broken'),('replay',runs/'sensor-replay'),
                    ('job',runs/'release/job-timeout-corrected'),('external',runs/'job-external'),
                    ('unsupported',runs/'sensor-external-lifecycle'),('recovered',runs/'interrupted'),
                    ('missing-optional',runs/'sensor-fixed/cases/timeout/bundle')]:
    reports[name]=source;origins[name]='Actual previously qualified QNX evidence; no new target execution.'
for name,base,tag in [('failed-baseline',Path('docs/evidence/phase5-supervision'),'unavailable'),
                      ('cleanup-failed',Path('docs/evidence/phase5-clean-lifecycle'),'sensor-repeat-ignore-unblock-cleanup'),
                      ('service-interference',Path('docs/evidence/phase5-clean-supervision'),'manager_pending')]:
    source=out/'native-bundles'/name;source.parent.mkdir(exist_ok=True)
    bundle=create_bundle(source,(base/(tag+'-plan.json')).read_bytes(),(base/(tag+'-events.jsonl')).read_bytes(),(base/(tag+'-status.json')).read_bytes())
    reports[name]=source;origins[name]={'native_source':str(base/tag),'raw_sha256':sha256(bundle.raw),'native_builds':bundle.plan.data['builds'],
                                     'note':'Host resealing/re-evaluation of unchanged older actual QNX bytes, not execution against the report revision.'}
for name,original,candidate in [('source-comparison','sensor-source-before','sensor-source-after'),('control-comparison','sensor-broken','sensor-replay')]:
    source=out/'comparisons'/name;source.mkdir(parents=True)
    (source/'comparison.json').write_bytes(canonical(compare_executions(runs/original,runs/candidate))+b'\n')
    reports[name]=source;origins[name]='Derived comparison of actual QNX bundles; original/candidate contract/build/target facts preserved.'
for name in ('empty','long-error'):
    source=out/'synthetic-formatting'/name;source.mkdir(parents=True);reports[name]=source
    origins[name]='SYNTHETIC formatting only; no QNX observations or service conclusions.'
    if name=='long-error':
        (source/'partial.json').write_bytes(canonical({'kind':'partial-run','schema_version':1,'error_type':'SYNTHETIC FORMATTING '+('long-error-path/'*180)+' </script><img src="https://invalid.example/forbidden" onerror="alert(1)">'}))
html_dir=out/'reports';html_dir.mkdir()
for name,source in reports.items():report(source,html_dir/(name+'.html'))
# Exact verdicts remain authoritative in a separately saved standard JUnit export.
bundles=[inspect_bundle(p) for p in (runs/'sensor-broken').glob('cases/*/bundle')]
xml=junit(bundles);(out/'broken.xml').write_bytes(xml)
checks=[];screenshots=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    browser_version=browser.version
    for mode,width,height,javascript in [('laptop',1440,1000,True),('narrow',390,844,True),('no-js',1280,900,False)]:
        context=browser.new_context(viewport={'width':width,'height':height},java_script_enabled=javascript)
        for name,source in reports.items():
            page=context.new_page();network=[];errors=[]
            page.on('request',lambda r: network.append(r.url) if urlsplit(r.url).scheme not in {'file','data'} else None)
            page.on('pageerror',lambda e: errors.append(str(e)))
            html=html_dir/(name+'.html');page.goto(html.resolve().as_uri(),wait_until='load')
            assert page.locator('h1').count()==1
            assert page.locator('h2').count()>=3
            assert not network and not errors,(name,mode,network,errors)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),(name,mode,'page overflow')
            if name in {'empty','long-error'}:
                assert 'INCOMPLETE: no finalized evaluated results' in page.locator('main').inner_text()
                assert page.locator('img,svg,iframe,object').count()==0
            for href in page.locator('a').evaluate_all('(links)=>links.map(a=>a.getAttribute("href"))'):
                if href.startswith('#'):
                    assert page.locator('[id="'+href[1:]+'"]').count()==1,(name,href)
                else:
                    parsed=urlsplit(href);assert not parsed.scheme and not parsed.netloc,(name,href)
                    assert (html.parent/unquote(parsed.path)).resolve().is_file(),(name,href,'missing artifact')
            if (mode=='laptop' and name in {'fixed','broken','failed-baseline','cleanup-failed','empty','unsupported','source-comparison'}) or (mode=='narrow' and name in {'fixed','long-error','control-comparison'}):
                shot=out/'screenshots'/(name+'-'+mode+'.png');shot.parent.mkdir(exist_ok=True)
                page.screenshot(path=str(shot));screenshots.append(str(shot.relative_to(out)))
            detail=page.locator('.case-detail').first
            if detail.count():
                summary=detail.locator('summary').first;summary.focus();page.keyboard.press('Enter')
                assert detail.get_attribute('open') is not None,(name,mode,'keyboard disclosure')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),(name,mode,'detail overflow')
                if javascript:
                    reference=detail.locator('a[href^="#event-"]').first
                    if reference.count():
                        reference.click()
                        assert page.evaluate('''() => { const e=document.getElementById(location.hash.slice(1)); return e && e.closest('details').open; }''')
                    select=page.locator('#verdict-filter');assert select.is_visible()
                    select.select_option('FAIL')
                    visible=page.locator('tr[data-verdict]:visible').evaluate_all('(rows)=>rows.map(r=>r.dataset.verdict)')
                    assert set(visible)<= {'FAIL'}
                    page.get_by_role('button',name='Show all',exact=True).click()
                    assert all(not page.locator('tr[data-verdict]').nth(i).is_hidden() for i in range(page.locator('tr[data-verdict]').count()))
                else:
                    assert page.locator('#filters').is_hidden()
                if mode=='narrow' and name=='broken':
                    detail.evaluate("e=>{e.open=true;e.scrollIntoView({block:'start'});} ");shot=out/'screenshots'/'broken-detail-narrow.png';page.screenshot(path=str(shot));screenshots.append(str(shot.relative_to(out)))
            checks.append({'report':name,'mode':mode,'viewport':[width,height],'javascript':javascript,'external_requests':network,'page_errors':errors,
                           'artifact_links_valid':True,'no_page_overflow':True,'keyboard_disclosure':bool(detail.count())})
            page.close()
        context.close()
    browser.close()
assert before=={str(p):sha256(p.read_bytes()) for p in inputs}
assert xml==junit(bundles)
assert evaluator_identity()==start,'source changed during browser qualification'
index={'kind':'phase8-offline-report-gate','schema_version':1,'passed':True,'source':start,
       'browser':browser_version,'playwright':importlib.metadata.version('playwright'),'product_dependencies':'Python standard library only',
       'reports':{name:{'source':str(source),'origin':origins[name],'html_sha256':sha256((html_dir/(name+'.html')).read_bytes())} for name,source in reports.items()},
       'checks':checks,'screenshots':screenshots,'source_artifact_count':len(inputs),'source_bytes_unchanged':True,'junit_bytes_unchanged':True}
(out/'index.json').write_bytes(canonical(index)+b'\n')
print(len(reports),'reports;',len(checks),'browser views; no external requests; source bytes and JUnit unchanged')
