#!/usr/bin/env python3
"""Qualify a fresh extracted jury archive offline; no build or target access."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'tests/jury'))
from prepare_review import check_links, scan, sha
from resmgrcheck.__main__ import parser as cli_parser
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.build_identity import source_hash
from resmgrcheck.contracts import Invalid, Profile, load
from resmgrcheck.workflow import compare_executions, inspect_execution
from playwright.sync_api import sync_playwright

args_parser = argparse.ArgumentParser(description=__doc__)
args_parser.add_argument('--archive',required=True); args_parser.add_argument('--out',required=True)
args=args_parser.parse_args(); archive=Path(args.archive).resolve(); out=Path(args.out)
out.mkdir(parents=True,exist_ok=False)
original_hash=sha(archive); runtime=source_hash(ROOT)
checks=[]; snapshots=[]; command_count=0; bash_count=0
with tempfile.TemporaryDirectory(prefix='resmgrcheck-jury-') as temporary:
    extracted=Path(temporary)
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        for member in source.infolist():
            destination=(extracted/member.filename).resolve()
            assert extracted.resolve() in destination.parents and not member.is_dir()
            assert (member.external_attr >> 16) & 0o170000 != 0o120000, 'symlink member'
        source.extractall(extracted)
    package=extracted/'resmgrcheck-jury'
    sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (package/'SHA256SUMS').read_text().splitlines()}
    assert set(sums)=={str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p.name!='SHA256SUMS'}
    for name,digest in sums.items(): assert sha(package/name)==digest, name
    links=check_links(package); privacy=scan(package)
    manifest=load(package/'package-manifest.json')
    for name,digest in manifest['original_files'].items():
        assert sha(package/name)==sha(ROOT/name)==digest, name
    identities=load(package/'docs/jury/identities.json')
    assert runtime==identities['cases']['broken']['builds']['source_tree_sha256']
    bundles=[]; reports={}
    for label in ('broken','after','job'):
        location=package/'docs/evidence/phase10/executions'/('p10demo2-'+label)
        _,summary,_=inspect_execution(location)
        bundle=inspect_bundle(location/'cases/timeout/bundle');bundles.append(bundle)
        assert bundle.manifest.data['bundle_id']==identities['cases'][label]['bundle_id']
        assert summary['execution_exit']==(1 if label=='broken' else 0)
        reports[label]=location/'report.html'
    comparison=compare_executions(reports['broken'].parent,reports['after'].parent)
    saved=load(package/'docs/evidence/phase10/comparison/comparison.json')
    assert comparison['label']=='fixed' and comparison['cases']==saved['cases']
    assert comparison['original_request_sha256']==saved['original_request_sha256']
    assert comparison['candidate_request_sha256']==saved['candidate_request_sha256']
    assert not comparison['fixture_mode_changed']
    assert len({bundle.plan.data['builds']['binaries']['runner'] for bundle in bundles})==1
    assert len({bundle.plan.data['builds']['binaries']['worker'] for bundle in bundles})==1
    assert bundles[0].plan.data['profile_sha256']==bundles[1].plan.data['profile_sha256']
    assert bundles[0].plan.data['fixture_mode']==bundles[1].plan.data['fixture_mode']=='ignore-unblock'
    assert bundles[0].plan.data['builds']['binaries']['fixture']!=bundles[1].plan.data['builds']['binaries']['fixture']
    assert sha(package/'demo.mp4')==identities['recording']['sha256']
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(package/'demo.mp4')],text=True))
    assert float(probe['format']['duration'])==170 and probe['streams'][0]['codec_name']=='h264'
    # Check the actual documented grammar without executing any target command.
    guide=(package/'docs/JURY_START_HERE.md').read_text()
    for language,body in re.findall(r'```(\w*)\n(.*?)```',guide,re.S):
        if language in {'bash','sh'}:
            subprocess.run(['bash','-n'],input=body,text=True,check=True);bash_count+=1
            for line in body.splitlines():
                if line.startswith('python3 -m resmgrcheck '):
                    cli_parser().parse_args(shlex.split(line)[3:]);command_count+=1
    for filename in ('profiles/sensor.json','profiles/job.json'):
        Profile.parse(load(ROOT/filename))
    subprocess.run(['git','apply','--check','docs/jury/source-fix.patch'],cwd=ROOT,check=True)
    # The archived patch is the exact actual recorded candidate change.
    assert (package/'docs/jury/source-fix.patch').read_bytes()==subprocess.check_output(['git','show','39b99d7a163c21c88d831456cc438e3c02a56ac9','--format=','--binary'],cwd=ROOT)
    # New README references and anchors, excluding documented archive-only media.
    readme=(ROOT/'README.md').read_text().split('## Prerequisites')[0]
    readme_refs=0
    for href in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',readme):
        parsed=urlsplit(href)
        if parsed.scheme:continue
        path=ROOT/parsed.path;assert path.is_file(),href
        if parsed.fragment:
            from prepare_review import slug
            assert parsed.fragment in [slug(line.lstrip('#').strip()) for line in path.read_text().splitlines() if line.startswith('#')],href
        readme_refs+=1
    reports.update({'comparison':package/'docs/evidence/phase10/comparison/report.html',
                    'entry':package/'START_HERE.html','index':package/'docs/jury/EVIDENCE_INDEX.html'})
    with sync_playwright() as driver:
        browser=driver.chromium.launch();browser_version=browser.version
        for mode,width,height,javascript in [('laptop',1440,1000,True),('narrow',390,844,True),('laptop-no-js',1440,1000,False),('narrow-no-js',390,844,False)]:
            context=browser.new_context(viewport={'width':width,'height':height},java_script_enabled=javascript)
            context.set_offline(True)
            for name,path in reports.items():
                page=context.new_page();network=[];errors=[];failed=[]
                page.on('request',lambda req:network.append(req.url) if urlsplit(req.url).scheme not in {'file','data'} else None)
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('requestfailed',lambda req:failed.append(req.url))
                page.goto(path.as_uri(),wait_until='load')
                assert page.locator('h1').count()==1
                assert not network and not errors and not failed,(name,mode,network,errors,failed)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(name,mode,'page overflow')
                detail=page.locator('.case-detail').first
                if detail.count():
                    detail.locator('summary').first.focus();page.keyboard.press('Enter')
                    assert detail.get_attribute('open') is not None
                    text=detail.inner_text()
                    if name=='broken':
                        assert 'cancellation_not_completed' in text and 'pending_state_not_released' in text
                        assert 'NOT_RUN' in text
                    else:assert 'all_obligations_satisfied' in text
                    if javascript:
                        reference=detail.locator('a[href^="#event-"]').first
                        reference.click()
                        assert page.evaluate("document.getElementById(location.hash.slice(1)).closest('details').open")
                    else:assert page.locator('#filters').is_hidden()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(name,mode,'detail overflow')
                    detail.locator('summary').first.scroll_into_view_if_needed()
                if mode in {'laptop','narrow'}:
                    shot=out/'screenshots'/(name+'-'+mode+'.png');shot.parent.mkdir(exist_ok=True)
                    page.screenshot(path=str(shot));snapshots.append(str(shot.relative_to(out)))
                checks.append({'document':name,'mode':mode,'viewport':[width,height],'javascript':javascript,'offline':True,
                               'external_requests':len(network),'page_errors':len(errors),'failed_loads':len(failed),'no_page_overflow':True,'case_keyboard_disclosure':bool(detail.count())})
                page.close()
            context.close()
        browser.close()
    # Negative integrity check on a disposable extracted copy, never original evidence.
    raw=bundles[0].path/'observations.jsonl';raw.write_bytes(raw.read_bytes()+b'\n')
    try:inspect_bundle(bundles[0].path)
    except Invalid:tamper_rejected=True
    else:raise AssertionError('modified evidence accepted')
assert sha(archive)==original_hash and source_hash(ROOT)==runtime
index={'kind':'portable-jury-review-qualification','schema_version':1,'passed':True,'native_execution_performed':False,
       'archive_name':archive.name,'archive_sha256':original_hash,'archive_bytes':archive.stat().st_size,
       'runtime_sha256':runtime,'fresh_temporary_extraction':True,'crc_passed':True,'checksum_files':len(sums),
       'original_files_preserved':len(manifest['original_files']),'sealed_bundles_validated':3,'canonical_comparison_matches':True,
       'unchanged_contract_settings':True,'source_patch_exact_and_applies':True,'tamper_rejected':tamper_rejected,
       'video_seconds':170,'video_sha256':identities['recording']['sha256'],'bash_blocks_syntax_checked':bash_count,
       'cli_commands_argparse_checked':command_count,'profiles_validated':2,'readme_links_checked':readme_refs,
       'browser':browser_version,'playwright':version('playwright'),'browser_checks':checks,'screenshots':snapshots,
       'link_checks':links,'privacy_review':privacy,'not_run':['Native rebuild or QNX integration matrices: documentation/packaging only, runtime fingerprint unchanged.','Fresh licensed guest setup by an independent juror.','Video upload, YouTube changes and Devpost submission.']}
(out/'qualification.json').write_text(json.dumps(index,indent=2)+'\n')
print(f'PASS: {len(checks)} offline browser views, {links["local_references_checked"]} local references, {len(sums)} checksums, 3 sealed bundles; no QNX execution.')
