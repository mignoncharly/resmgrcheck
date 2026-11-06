#!/usr/bin/env python3
"""Real QNX Phase 4 transport-loss subgate; manual qualified lab only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shlex
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import load, loads, canonical, text, RunStarted, RunStatus
from resmgrcheck.planning import expand
from resmgrcheck.evaluator import evaluate_persistent

parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);args=parser.parse_args()
text(args.prefix);text(args.prefix+'-disconnect')
out=Path('.local/evidence')/('phase4-'+args.prefix);out.mkdir(exist_ok=False)
remote='/data/resmgrcheck/'+args.prefix
commands=[];transport=None

def call(argv,expected=0,timeout=15):
    p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':argv,'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert p.returncode==expected,commands[-1]
    return p

def ssh(command,expected=0,timeout=15):return call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command],expected,timeout)
def upload(paths):call(['scp','-F','.local/ssh_config',*map(str,paths),'resmgrcheck-qnx:'+remote+'/'])
def remote_file(run,name,timeout=6):
    return ssh('cat '+shlex.quote('/data/resmgrcheck/runs/'+run+'/'+name),timeout=timeout).stdout

def final_status(run):
    end=time.monotonic()+16
    while time.monotonic()<end:
        raw=remote_file(run,'status.json',min(6,max(.1,end-time.monotonic())))
        d=RunStatus.parse(loads(raw)).data
        if d['state']!='running':return raw,d
        time.sleep(.04)
    raise TimeoutError('target completion not established; preserve partial data, do not restart')

def ack_line(process):
    fd=process.stdout.fileno();os.set_blocking(fd,False)
    selector=selectors.DefaultSelector();selector.register(fd,selectors.EVENT_READ)
    end=time.monotonic()+5;data=b''
    try:
        while time.monotonic()<end and len(data)<16384:
            if selector.select(max(0,end-time.monotonic())):
                chunk=os.read(fd,4096)
                if not chunk:break
                data+=chunk
                if b'\n' in data:return data.split(b'\n',1)[0]+b'\n'
    finally:selector.close()
    raise TimeoutError('missing bounded start acknowledgement')

try:
    plans={}
    for tag,profile,mode in [('normal','job','corrected'),('disconnect','sensor','ignore-unblock')]:
        plans[tag]=expand(load('profiles/'+profile+'.json'),args.prefix+'-'+tag,mode).data
        (out/(tag+'-plan.json')).write_bytes(canonical(plans[tag])+b'\n')
    ssh('mkdir '+shlex.quote(remote))
    binaries=[Path('build/qnx-x86_64')/n for n in ('runner','worker','sensor-v1-fixture','job-v1-fixture')]
    upload(binaries+[out/(tag+'-plan.json') for tag in plans])
    readback=out/'readback';readback.mkdir();hashes={}
    for path in binaries:
        dest=readback/path.name
        call(['scp','-F','.local/ssh_config','resmgrcheck-qnx:'+remote+'/'+path.name,str(dest)])
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==hashes[path.name]
    ssh('cd '+shlex.quote(remote)+' && chmod 755 runner worker sensor-v1-fixture job-v1-fixture')
    start=ssh('cd '+shlex.quote(remote)+' && ./runner normal-plan.json --persist').stdout
    (out/'normal-start.json').write_bytes(start);RunStarted.parse(loads(start))
    cases=[]
    for tag in ('normal','disconnect'):
        plan=plans[tag];run=plan['run_id']
        if tag=='disconnect':
            command='cd '+shlex.quote(remote)+' && ./runner disconnect-plan.json --persist && cat'
            argv=['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command]
            transport=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            start=ack_line(transport);ack=RunStarted.parse(loads(start)).data
            (out/'disconnect-start.json').write_bytes(start)
            # Observe the real deferred timed request before deliberately closing SSH.
            end=time.monotonic()+4
            while time.monotonic()<end:
                partial=remote_file(run,'events.jsonl')
                records=[loads(line) for line in partial.splitlines(keepends=True) if line.endswith(b'\n')]
                deadlines=[x for x in records if x.get('event')=='deadline']
                if deadlines and any(x.get('event')=='pending' and x['data']['client_pid']==deadlines[0]['pid'] for x in records):break
                time.sleep(.02)
            else:raise TimeoutError('pending barrier not established for disconnect test')
            before_raw=remote_file(run,'status.json');before=RunStatus.parse(loads(before_raw)).data
            assert before['state']=='running' and before['supervisor_pid']==ack['supervisor_pid']
            (out/'disconnect-running-status.json').write_bytes(before_raw)
            (out/'disconnect-partial-events.jsonl').write_bytes(partial)
            transport.terminate();tail,stderr=transport.communicate(timeout=3)
            commands.append({'argv':argv,'exit':transport.returncode,'intentional_host_ssh_termination':True,'stdout_tail':tail.decode(errors='replace'),'stderr':stderr.decode(errors='replace')})
            assert transport.returncode!=0
            transport=None
            duplicate=ssh('cd '+shlex.quote(remote)+' && ./runner disconnect-plan.json --persist',expected=2)
            assert not duplicate.stdout
        status_raw,status=final_status(run)
        events=remote_file(run,'events.jsonl');diagnostic=remote_file(run,'stderr.log')
        (out/(tag+'-status.json')).write_bytes(status_raw)
        (out/(tag+'-events.jsonl')).write_bytes(events)
        (out/(tag+'-stderr.txt')).write_bytes(diagnostic)
        result=evaluate_persistent(plan,events,status).data
        (out/(tag+'-result.json')).write_bytes(canonical(result)+b'\n')
        expected='PASS' if tag=='normal' else 'FAIL'
        assert result['verdict']==expected,result
        assert status['state']=='complete' and status['cleanup_ok'] and not status['unresolved']
        # Duplicate launch after completion must preserve both sealed artifacts.
        duplicate=ssh('cd '+shlex.quote(remote)+' && ./runner '+shlex.quote(tag+'-plan.json')+' --persist',expected=2)
        assert not duplicate.stdout
        assert remote_file(run,'events.jsonl')==events and remote_file(run,'status.json')==status_raw
        cases.append({'case':tag,'verdict':result['verdict'],'target_status':status['state'],
                      'declared_collector_exit':status['exit_code'],'cleanup_ok':status['cleanup_ok'],
                      'event_sha256':hashlib.sha256(events).hexdigest(),'duplicate_launch_exit':2})
        print(tag,result['verdict'],'status/cleanup and duplicate guard verified',flush=True)
    inventory=ssh('pidin ar').stdout;(out/'post-inventory.txt').write_bytes(inventory)
    for line in inventory.decode().splitlines():
        tokens=line.split()
        if len(tokens)>1:
            assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'}
        assert 'sensor-v1-fixture' not in line and 'job-v1-fixture' not in line
        assert remote+'/runner' not in line and remote+'/worker' not in line
    (out/'index.json').write_text(json.dumps({'kind':'phase4-persistence-subgate','builds':plans['normal']['builds'],
                                           'binary_readback_sha256':hashes,'cases':cases},indent=2)+'\n')
finally:
    if transport is not None:
        transport.terminate()
        try:transport.communicate(timeout=3)
        except subprocess.TimeoutExpired:transport.kill();transport.communicate()
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print('Persistence subgate saved in',out)
