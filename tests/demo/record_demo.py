#!/usr/bin/env python3
"""Record actual lab CLI/report footage. Optional local Playwright/FFmpeg only."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
from resmgrcheck.artifacts import evaluator_identity,sha256
from resmgrcheck.contracts import canonical,load,loads
from resmgrcheck.workflow import inspect_execution,run_id

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--out',required=True);p.add_argument('--prefix',required=True)
p.add_argument('--fixed-source',required=True);a=p.parse_args();run_id(a.prefix)
assert len(a.prefix)<=20
out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
fixed=Path(a.fixed_source).resolve();source=evaluator_identity();assert not source['dirty']
assert subprocess.check_output(['git','-C',str(fixed),'status','--porcelain'])==b''
commands=[];observations={};passed=False;page=None;start=None;stage=0;title='';caption='';history=[]
HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#0b1d2c;color:#e9f2f8;font-family:system-ui,sans-serif}header{padding:22px 32px 8px;font-size:32px;font-weight:750}#scene{color:#91d4eb;font-size:23px;padding:0 32px 12px}#terminal{margin:0 32px;height:390px;padding:18px;background:#122c40;border:1px solid #36536a;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere;overflow:hidden;font:16px/1.4 ui-monospace,monospace}#caption{margin:18px 32px 0;font-size:20px;line-height:1.4}footer{position:fixed;bottom:10px;left:32px;color:#acc1d0;font-size:13px}</style><header>ResMgrCheck · actual QNX lab</header><div id="scene"></div><pre id="terminal"></pre><p id="caption"></p><footer>Intentional fixture defects are labelled · Actual output; full evidence preserved · No simulated transport</footer></html>'''

def display():
    if page is None:return
    page.locator('#scene').evaluate('(e,v)=>e.textContent=v',title)
    page.locator('#caption').evaluate('(e,v)=>e.textContent=v',caption)
    page.locator('#terminal').evaluate('(e,v)=>{e.textContent=v;e.scrollTop=e.scrollHeight;}', '\n'.join(history)[-6000:])

def terminal(number,heading,text):
    global stage,title,caption,history
    stage=number;title=heading;caption=text;history=[]
    page.set_content(HTML);display()

def wait_until(seconds):
    while time.monotonic()-start<seconds:page.wait_for_timeout(max(1,min(250,(seconds-(time.monotonic()-start))*1000)))

def call(argv,expected=0,timeout=120):
    argv=list(map(str,argv));entry={'argv':argv,'expected_exit':expected,'stage':stage,'exit':None};commands.append(entry)
    history.append('$ '+shlex.join(argv));display()
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);begin=time.monotonic()
        try:
            while process.poll() is None:
                if time.monotonic()-begin>timeout:raise TimeoutError('command incomplete; preserve its existing native run ID')
                stdout.seek(0);text=stdout.read(1024*1024).decode(errors='replace');stderr.seek(0);error=stderr.read(65536).decode(errors='replace')
                if page is not None:
                    saved=history[:];history.append(text+error);display();history[:]=saved;page.wait_for_timeout(100)
                else:time.sleep(.05)
            stdout.seek(0);raw=stdout.read();stderr.seek(0);diagnostic=stderr.read()
            entry.update(exit=process.returncode,stdout=raw.decode(errors='replace'),stderr=diagnostic.decode(errors='replace'),elapsed_ms=round((time.monotonic()-begin)*1000))
            history.append(entry['stdout']+entry['stderr']);display()
            assert process.returncode==expected,entry
            return raw
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=2)
            (out/'commands.json').write_bytes(canonical(commands)+b'\n')

def cli(*argv,expected=0,timeout=120):return call([sys.executable,'-m','resmgrcheck',*argv],expected,timeout)

def run(name,profile,mode='fixed',expected=0):
    location='runs/'+a.prefix+'-'+name
    cli('run','--target','lab','--profile',profile,'--suite','profile','--fixture-mode',mode,'--out',location,'--run-id',a.prefix+'-'+name,expected=expected)
    req,result,_=inspect_execution(location);observations[name]={'location':location,'request':req.data,'result':result}
    return Path(location)

def evidence(name):
    root=Path(observations[name]['location']);case=next(root.glob('cases/*/bundle'))
    result=load(case/'result.json');records=[loads(line) for line in (case/'observations.jsonl').read_bytes().splitlines()]
    selected={'baseline_validity','pending_precondition','cancellation_completion','cancellation_not_completed','pending_state_cleanup','fresh_client_health','client_departure','ocb_lifetime','owned_process_cleanup'}
    keys={'operation','pending','live','raw_return','raw_errno','error_name','facts','completed','all_reaped','child_pid','signal','exit_code','exited','signaled'}
    lines=['Actual saved assertions and selected source records; full raw stream preserved:']
    for assertion in result['assertions']:
        if assertion['id'] not in selected:continue
        refs=assertion['event_refs'];shown=[]
        for ref in refs[:4 if assertion['id']=='client_departure' else 1]:
            event=records[ref]
            shown.append({'record':ref,'event':event.get('event'),**{k:v for k,v in event.get('data',{}).items() if k in keys}})
        lines.append(assertion['id']+' = '+assertion['verdict']+' '+json.dumps(shown,separators=(',',':')))
    history[:]=lines;display()


def overlay(text):
    page.evaluate('''text=>{const n=document.createElement('aside');n.textContent=text;n.style.cssText='position:fixed;bottom:0;left:0;right:0;background:#0b1d2c;color:white;padding:12px 24px;font:18px/1.4 system-ui;z-index:10000';document.body.append(n);}''',text)

try:
    # Compile/deploy before recording; these actual commands remain in the
    # manifest. The correction's candidate build is shown during recording.
    call(['make','-B','qnx','QNX_VARIANT=gcc_ntox86_64'])
    cli('deploy','--target','lab','--build','build/qnx-x86_64')
    (out/'original-deployment.json').write_bytes(Path('build/qnx-x86_64/manifest.json').read_bytes())
    with sync_playwright() as browser_api:
        browser=browser_api.chromium.launch();context=browser.new_context(viewport={'width':1280,'height':720},record_video_dir=str(out/'raw-video'),record_video_size={'width':1280,'height':720})
        page=context.new_page();video=page.video;page.set_content(HTML);start=time.monotonic()
        terminal(1,'1 / 7 · Real target and corrected sensor','Actual QNX8.0 target. Corrected baselines and fresh-client health use supervised native workers.')
        call(['ssh','-F','.local/ssh_config','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','resmgrcheck-qnx','uname -a && uname -p'])
        cli('doctor','--target','lab')
        normal=run('normal','profiles/sensor.json');evidence('normal');wait_until(20)
        terminal(2,'2 / 7 · Intentional fixture defect','The fixture deliberately ignores a current unblock. Cancellation completion and pending cleanup remain separate failures; cleanup is a separate fact.')
        broken=run('broken','profiles/sensor.json','ignore-unblock',1);evidence('broken');wait_until(55)
        cli('report',broken,'--out',broken/'report.html')
        page.goto((broken/'report.html').resolve().as_uri());page.locator('#case-1').evaluate("e=>e.open=true");page.locator('#case-1 table tbody tr').filter(has_text='cancellation_not_completed').first.scroll_into_view_if_needed()
        overlay('Actual saved report · expected versus observed · source event references · missing health is not inferred')
        page.screenshot(path=str(out/'broken-report.png'));wait_until(80)
        terminal(4,'4 / 7 · Source correction and explicit candidate replay','Actual handler correction; saved contract, timing and ignore-unblock setting stay unchanged. Candidate hashes are verified before launch.')
        call(['git','-C',fixed,'show','--format=short','HEAD','--','native/fixtures/sensor.c','native/fixtures/job.c'])
        call(['make','-C',fixed,'qnx','QNX_VARIANT=gcc_ntox86_64'],timeout=120)
        cli('deploy','--target','lab','--build',fixed/'build/qnx-x86_64')
        manifest=fixed/'build/qnx-x86_64/manifest.json';(out/'candidate-deployment.json').write_bytes(manifest.read_bytes())
        after=Path('runs')/(a.prefix+'-after')
        cli('replay',broken/'replay.json','--target','lab','--candidate-manifest',manifest,'--out',after,'--run-id',a.prefix+'-after')
        req,result,_=inspect_execution(after);observations['after']={'location':str(after),'request':req.data,'result':result};evidence('after')
        cli('compare',broken,after,'--out','runs/'+a.prefix+'-comparison');comparison=load('runs/'+a.prefix+'-comparison/comparison.json');assert comparison['label']=='fixed' and not comparison['fixture_mode_changed']
        assert time.monotonic()-start<115,'source-fix scene exceeded its allotted recording time'
        wait_until(115)
        terminal(5,'5 / 7 · Exact-worker departure and next client','Pending first, then only the owned worker is terminated. Actual exit/reaping and default close bookkeeping are required before health can pass.')
        departure=run('departure','profiles/sensor-departure.json');evidence('departure');wait_until(140)
        terminal(6,'6 / 7 · Job adapter, same generic engine','Waiter state and service-owned jobs are distinct. The same runner/worker checks cancellation, job retention and fresh-client result420.')
        job=run('job','profiles/job.json');evidence('job')
        assert observations['job']['request']['cases'][0]['builds']['binaries']['worker']==observations['after']['request']['cases'][0]['builds']['binaries']['worker']
        assert time.monotonic()-start<165,'job scene exceeded its allotted recording time'
        wait_until(165)
        terminal(7,'7 / 7 · Reproduce from source','README · docs/codelab.md · versioned contracts · immutable raw/JSON/JUnit/HTML. Qualified lab scope; unsupported and incomplete coverage remain visible.')
        history.extend(['python3 -m resmgrcheck --help','python3 -m resmgrcheck verify --target lab --suite release','docs/codelab.md','docs/TEST_EVIDENCE.md','Native run IDs and original/candidate source/build hashes are preserved in this recording manifest.']);display();wait_until(170)
        raw_video=video.path();context.close();browser.close();page=None
    call(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',raw_video,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',out/'demo.mp4'])
    info=json.loads(call(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',out/'demo.mp4']))
    duration=float(info['format']['duration']);assert 165<=duration<180
    assert evaluator_identity()==source
    passed=True
finally:
    if page is not None:
        try:context.close();browser.close()
        except Exception:pass
    (out/'manifest.json').write_bytes(canonical({'kind':'actual-qnx-demo-recording','schema_version':1,'passed':passed,'source':source,'observations':observations,'commands_file':'commands.json','public_video_url':None,'publication_performed':False,'duration_ms':int(duration*1000) if passed else None,'video_sha256':sha256((out/'demo.mp4').read_bytes()) if (out/'demo.mp4').exists() else None,'caption_language':'English','audio':'none; English on-screen explanation; optional narration supplied separately','target':'Existing owned QNX8.0.0 KVM lab; not recreated'})+b'\n')
if not passed:raise SystemExit(2)
print('Actual QNX recording passed:',duration,'seconds;',out/'demo.mp4')
