#!/usr/bin/env python3
"""Clean-source README/release reproduction against an explicitly reused QNX lab."""
import argparse
from collections import Counter
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.artifacts import evaluator_identity,sha256
from resmgrcheck.contracts import canonical,load
from resmgrcheck.transport import Target,Transport
from resmgrcheck.workflow import inspect_execution

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True,help='new ignored qualification directory')
parser.add_argument('--fixed-source',required=True,help='separate clean committed cancellation-corrected checkout')
parser.add_argument('--input-prefix',required=True,help='fresh lab stage ID for input checks')
a=parser.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
fixed=Path(a.fixed_source).resolve();source=evaluator_identity();assert not source['dirty'],'clean source checkout required'
assert subprocess.check_output(['git','-C',str(fixed),'status','--porcelain'])==b'','clean candidate source required'
commands=[];facts={};passed=False

def call(argv,expected=0,timeout=300):
    argv=list(map(str,argv));p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':argv,'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    (out/'commands.json').write_bytes(canonical(commands)+b'\n')
    assert p.returncode==expected,commands[-1]
    return p.stdout

def cli(*argv,expected=0,timeout=300):return call([sys.executable,'-m','resmgrcheck',*argv],expected,timeout)

def record(name):
    request,summary,results=inspect_execution(Path('runs')/name)
    facts[name]={'run_id':request.data['run_id'],'execution_exit':summary['execution_exit'],'cases':summary['cases']}
    return request,summary,results

try:
    call(['git','rev-parse','HEAD']);call(['git','status','--porcelain'])
    # Manual prerequisites already met: installed SDK environment, already booted
    # reused target and existing verified local OpenSSH/SFTP authentication.
    cli('doctor','--target','lab','--out',out/'doctor-before.json',expected=3)
    cli('validate','profiles/sensor.json')
    call(['make','qnx','QNX_VARIANT=gcc_ntox86_64'])
    cli('deploy','--target','lab','--build','build/qnx-x86_64')
    cli('doctor','--target','lab','--out',out/'doctor-after.json')
    target=Target.read('lab');t=Transport(target)
    (out/'target-before.txt').write_bytes(call(['ssh','-F',target.data['ssh_config'],target.data['ssh_alias'],'uname -a; pidin ar; df -g /data']))
    (out/'main-build.json').write_bytes(Path('build/qnx-x86_64/manifest.json').read_bytes())
    cli('run','--target','lab','--profile','profiles/sensor.json','--suite','lifecycle','--fixture-mode','fixed','--out','runs/sensor-fixed');record('sensor-fixed')
    cli('run','--target','lab','--profile','profiles/sensor.json','--suite','lifecycle','--fixture-mode','ignore-unblock','--out','runs/sensor-broken',expected=2);record('sensor-broken')
    cli('replay','runs/sensor-broken/replay.json','--target','lab','--fixture-mode','fixed','--out','runs/sensor-replay');record('sensor-replay')
    cli('compare','runs/sensor-broken','runs/sensor-replay','--out','runs/comparison')
    assert load('runs/comparison/comparison.json')['label']=='incomparable'
    cli('report','runs/sensor-replay','--out','runs/sensor-replay/report.html')
    cli('report','runs/sensor-broken','--out','runs/sensor-broken/report.html')
    cli('verify','--target','lab','--suite','release',timeout=600)
    release=list(Path('runs').glob('release-r-*/result.json'));assert len(release)==1
    verdicts=load(release[0]);assert verdicts['qualification_passed'] and len(verdicts['cases'])==36
    assert Counter(r['verdict'] for r in verdicts['cases'])=={'PASS':12,'FAIL':19,'ERROR':2,'UNSUPPORTED':3}
    facts['release']={'location':str(release[0].parent),'result':verdicts}
    cli('junit','runs/sensor-fixed','runs/sensor-broken','runs/sensor-replay','--output',out/'workflow.xml')
    facts['junit_counts']=ET.parse(out/'workflow.xml').getroot().attrib
    call([sys.executable,'tests/qnx/qualify-input-bounds.py','--prefix',a.input_prefix,'--out',out/'input-bounds'])
    for service in ('sensor','job'):
        name=service+'-source-before'
        cli('run','--target','lab','--profile','profiles/'+service+'.json','--suite','profile','--fixture-mode','ignore-unblock','--out','runs/'+name,expected=1);record(name)
    call(['make','-C',fixed,'qnx','QNX_VARIANT=gcc_ntox86_64'])
    cli('deploy','--target','lab','--build',fixed/'build/qnx-x86_64')
    candidate=fixed/'build/qnx-x86_64/manifest.json';(out/'source-candidate.json').write_bytes(candidate.read_bytes())
    (out/'source-fix.patch').write_bytes(call(['git','-C',fixed,'show','--format=fuller','HEAD','--','native/fixtures/sensor.c','native/fixtures/job.c']))
    for service in ('sensor','job'):
        before=service+'-source-before';after=service+'-source-after'
        cli('replay','runs/'+before+'/replay.json','--target','lab','--candidate-manifest',candidate,'--out','runs/'+after);record(after)
        cli('compare','runs/'+before,'runs/'+after,'--out','runs/'+service+'-source-comparison')
        comparison=load('runs/'+service+'-source-comparison/comparison.json')
        assert comparison['label']=='fixed' and not comparison['fixture_mode_changed']
        assert all(r['same_contract'] and r['target_compatible'] and r['original_builds']['binaries']['fixture']!=r['candidate_builds']['binaries']['fixture'] for r in comparison['cases'])
        cli('report','runs/'+after,'--out','runs/'+after+'/report.html')
        cli('report','runs/'+service+'-source-comparison','--out','runs/'+service+'-source-comparison/report.html')
        facts[service+'-source-comparison']=comparison
    cli('deploy','--target','lab','--build','build/qnx-x86_64')
    (out/'target-after.txt').write_bytes(call(['ssh','-F',target.data['ssh_config'],target.data['ssh_alias'],'uname -a; pidin ar; df -g /data']))
    for path in Path('runs').rglob('cases/*/bundle/status.json'):
        status=load(path);assert status['cleanup_ok'] and not status['unresolved'],path
    assert evaluator_identity()==source,'source changed during qualification'
    assert subprocess.check_output(['git','-C',fixed,'status','--porcelain'])==b''
    passed=True
finally:
    (out/'commands.json').write_bytes(canonical(commands)+b'\n')
    value={'kind':'phase9-clean-source-reused-target-gate','schema_version':1,'passed':passed,'source':source,
           'workspace':str(Path.cwd()),'target_state':'Existing KVM guest reused; no fresh-target creation or reboot',
           'manual_prerequisites':['installed/local licensed SDK environment','already booted owned QNX8 lab','existing verified SSH alias/key/SFTP and ignored target metadata'],
           'facts':facts}
    (out/'index.json').write_bytes(canonical(value)+b'\n')
print('Clean source README/release/candidate workflow passed; target explicitly reused; individual red verdicts preserved')
