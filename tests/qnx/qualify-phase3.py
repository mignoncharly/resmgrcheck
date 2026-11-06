#!/usr/bin/env python3
"""Manual-lab qualification helper, not the Phase 7 application transport.
Run from the repository after SDK-enabled make qnx. Uses only the prequalified
.local SSH alias, owned /data/resmgrcheck directory and a fresh prefix.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import load, canonical, digest, text
from resmgrcheck.planning import expand
from resmgrcheck.evaluator import evaluate

parser=argparse.ArgumentParser()
parser.add_argument('--prefix',required=True)
args=parser.parse_args(); text(args.prefix)
text(args.prefix+'-sensor-corrected')
root=Path.cwd(); out=root/'.local/evidence'/('phase3-'+args.prefix)
out.mkdir(exist_ok=False)
remote='/data/resmgrcheck/'+args.prefix
commands=[]

def execute(argv,expected=0,timeout=20):
    p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':argv,'exit':p.returncode,'stdout':p.stdout.decode('ascii',errors='replace'),'stderr':p.stderr.decode('ascii',errors='replace')})
    if p.returncode!=expected: raise RuntimeError(commands[-1])
    return p

def ssh(command,expected=0): return execute(['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command],expected)
def upload(paths): execute(['scp','-F','.local/ssh_config',*map(str,paths),'resmgrcheck-qnx:'+remote+'/'])
def download(name,dest): execute(['scp','-F','.local/ssh_config','resmgrcheck-qnx:'+remote+'/'+name,str(dest)])

try:
    cases=[]
    for service in ('sensor','job'):
        profile=load(root/'profiles'/(service+'.json'))
        for mode,tag in [('corrected',service+'-corrected'),('ignore-unblock',service+'-defect')]:
            plan=expand(profile,args.prefix+'-'+tag,mode).data
            (out/(tag+'-plan.json')).write_bytes(canonical(plan)+b'\n')
            cases.append((tag,plan,0,'PASS' if mode=='corrected' else 'FAIL'))
    profile=load(root/'profiles/sensor.json');profile['capabilities']['required'].append('signal')
    plan=expand(profile,args.prefix+'-unsupported').data
    (out/'unsupported-plan.json').write_bytes(canonical(plan)+b'\n')
    cases.append(('unsupported',plan,3,'UNSUPPORTED'))
    ssh('mkdir '+shlex.quote(remote))
    binaries=[root/'build/qnx-x86_64'/name for name in ('runner','worker','sensor-v1-fixture','job-v1-fixture')]
    upload(binaries+[out/(tag+'-plan.json') for tag,*_ in cases])
    readback=out/'readback';readback.mkdir()
    hashes={}
    for path in binaries:
        dest=readback/path.name;download(path.name,dest)
        value=hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==value
        hashes[path.name]=value
    ssh('cd '+shlex.quote(remote)+' && chmod 755 runner worker sensor-v1-fixture job-v1-fixture')
    outcomes=[]
    for tag,plan,native_code,verdict in cases:
        ssh('cd '+shlex.quote(remote)+' && ./runner '+shlex.quote(tag+'-plan.json')+' > '+shlex.quote(tag+'-events.jsonl')+' 2> '+shlex.quote(tag+'-stderr.txt'),native_code)
        download(tag+'-events.jsonl',out/(tag+'-events.jsonl'));download(tag+'-stderr.txt',out/(tag+'-stderr.txt'))
        result=evaluate(plan,(out/(tag+'-events.jsonl')).read_bytes()).data
        (out/(tag+'-result.json')).write_bytes(canonical(result)+b'\n')
        assert result['verdict']==verdict, result
        outcomes.append({'case':tag,'native_exit':native_code,'verdict':result['verdict'],'reasons':result['reasons']})
        print(tag,result['verdict'],flush=True)
    original=copy.deepcopy(cases[0][1])
    bad=[]
    def variant(tag,mutate):
        value=copy.deepcopy(original);mutate(value)
        value['profile_sha256']=digest(value['profile'])
        value['suite_sha256']=digest(value['profile']['suite'])
        bad.append((tag,canonical(value)+b'\n'))
    variant('version',lambda d:d.update(schema_version=2))
    variant('boolean-timing',lambda d:d['profile']['timing'].update(operation_ms=True))
    variant('unknown-operation',lambda d:d['profile']['operation'].update(id='shell'))
    variant('unsafe-path',lambda d:d['profile']['service'].update(device='/etc/passwd'))
    variant('abi',lambda d:d['profile']['adapter'].update(abi=2))
    raw=canonical(original)
    bad.append(('duplicate',b'{"kind":"scenario-plan",'+raw[1:]))
    bad.append(('leading-zero',raw.replace(b'"operation_ms":500',b'"operation_ms":0500')))
    bad.append(('trailing-data',raw+b' []'))
    bad.append(('nesting',b'['*20+b'0'+b']'*20))
    rejections=[]
    for tag,raw in bad:
        name='invalid-'+tag+'.json';(out/name).write_bytes(raw);upload([out/name])
        ssh('cd '+shlex.quote(remote)+' && ./runner '+shlex.quote(name)+' > '+shlex.quote(name+'.stdout')+' 2> '+shlex.quote(name+'.stderr'),2)
        download(name+'.stdout',out/(name+'.stdout'));download(name+'.stderr',out/(name+'.stderr'))
        assert not (out/(name+'.stdout')).read_bytes(), 'invalid plan started event collection'
        rejections.append({'case':tag,'native_exit':2,'stdout_bytes':0})
    # Host validation occurs without importing/using any target transport.
    invalid=load(root/'profiles/job.json');invalid['operation']['parameters']['job_id']=True
    (out/'invalid-host-profile.json').write_bytes(canonical(invalid)+b'\n')
    execute([sys.executable,'-m','resmgrcheck','plan',str(out/'invalid-host-profile.json'),'--run-id','invalid','--output',str(out/'must-not-exist.json')],2)
    assert not (out/'must-not-exist.json').exists()
    inventory=ssh('pidin ar').stdout
    (out/'post-inventory.txt').write_bytes(inventory)
    for line in inventory.decode().splitlines():
        tokens=line.split()
        if len(tokens)>1:
            assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'}
        assert remote+'/runner' not in line and remote+'/worker' not in line
        assert 'sensor-v1-fixture' not in line and 'job-v1-fixture' not in line
    summary={'kind':'phase3-qualification-index','source_builds':original['builds'],'binary_readback_sha256':hashes,
             'cases':outcomes,'native_rejections':rejections,'host_invalid_profile_exit':2}
    (out/'index.json').write_text(json.dumps(summary,indent=2)+'\n')
finally:
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print('Qualification saved in',out)
