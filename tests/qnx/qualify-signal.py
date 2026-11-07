#!/usr/bin/env python3
"""Real QNX Phase 5 signal family, with affected timeout prerequisites only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import canonical,load,loads,text,digest,RunStatus,RunStarted
from resmgrcheck.planning import expand
from resmgrcheck.evaluator import evaluate_persistent

parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);args=parser.parse_args();text(args.prefix)
out=Path('.local/evidence')/('phase5-signal-'+args.prefix);out.mkdir(exist_ok=False)
remote='/data/resmgrcheck/'+args.prefix;commands=[];cases=[]
def call(argv,expected=0,timeout=8):
    p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':list(map(str,argv)),'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert p.returncode==expected,commands[-1]
    return p.stdout
def ssh(command):return call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command])
def get(run,name):return ssh('cat '+shlex.quote('/data/resmgrcheck/runs/'+run+'/'+name))
try:
    ssh('mkdir '+remote)
    binaries=[Path('build/qnx-x86_64')/n for n in ('runner','worker','sensor-v1-fixture','job-v1-fixture')]
    call(['scp','-F','.local/ssh_config',*map(str,binaries),'resmgrcheck-qnx:'+remote+'/'])
    rb=out/'readback';rb.mkdir();hashes={}
    for p in binaries:
        call(['scp','-F','.local/ssh_config','resmgrcheck-qnx:'+remote+'/'+p.name,str(rb/p.name)])
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        assert hashlib.sha256((rb/p.name).read_bytes()).hexdigest()==hashes[p.name]
    ssh('cd '+remote+' && chmod 755 runner worker sensor-v1-fixture job-v1-fixture')
    (out/'pre-inventory.txt').write_bytes(ssh('pidin ar'))
    matrix=[(s,f,m) for f in ('signal','timeout') for s in ('sensor','job') for m in ('corrected','ignore-unblock')]
    matrix += [('sensor','auto','corrected'),('job','auto','corrected'),('sensor','missing','corrected')]
    for service,family,mode in matrix:
        tag=service+'-'+family+'-'+('fixed' if mode=='corrected' else 'defect')
        profile=load('profiles/'+service+('-signal' if family in ('signal','auto') else '')+'.json')
        if family=='auto':profile['suite']['signal_mode']='auto-restart'
        if family=='missing':profile['capabilities']['required'].append('error-probe')
        plan=expand(profile,args.prefix+'-'+tag,mode).data;run=plan['run_id']
        path=out/(tag+'-plan.json');path.write_bytes(canonical(plan)+b'\n')
        call(['scp','-F','.local/ssh_config',str(path),'resmgrcheck-qnx:'+remote+'/'])
        start=time.monotonic();ack=ssh('cd '+remote+' && ./runner '+path.name+' --persist')
        RunStarted.parse(loads(ack));(out/(tag+'-start.json')).write_bytes(ack)
        while time.monotonic()-start<16:
            status_raw=get(run,'status.json');status=RunStatus.parse(loads(status_raw)).data
            if status['state']!='running':break
            time.sleep(.03)
        else:raise TimeoutError('completion unestablished; preserve original run ID')
        raw=get(run,status['event_file']);result=evaluate_persistent(plan,raw,status).data
        elapsed=time.monotonic()-start
        for suffix,value in [('events.jsonl',raw),('status.json',status_raw),('result.json',canonical(result)+b'\n'),('stderr.txt',get(run,'stderr.log'))]:
            (out/(tag+'-'+suffix)).write_bytes(value)
        expected='UNSUPPORTED' if family in ('auto','missing') else 'FAIL' if mode=='ignore-unblock' else 'PASS'
        reasons={'signal_mode_unsupported'} if family=='auto' else {'required_capability_missing'} if family=='missing' else {'cancellation_not_completed','pending_state_not_released'} if expected=='FAIL' else {'all_obligations_satisfied'}
        print(tag,result['verdict'],result['reasons'],flush=True)
        assert result['verdict']==expected and set(result['reasons'])==reasons,result
        records=[loads(s) for s in raw.splitlines()]
        spawned={r['data']['child_pid'] for r in records if r.get('event')=='spawned'}
        reaped={r['data']['child_pid'] for r in records if r.get('event')=='reaped'}
        assert spawned==reaped and status['cleanup_ok'] and not status['unresolved'] and elapsed<16
        if expected=='UNSUPPORTED':assert not spawned
        if family=='signal':
            assert not any(r.get('event')=='deadline' for r in records),'simultaneous timeout forbidden'
            trigger=next(r for r in records if r.get('event')=='trigger_requested')
            pending=next(r for r in records if r.get('event')=='pending' and r['data']['client_pid']==trigger['data']['child_pid'])
            assert int(pending['ns'])<=int(trigger['ns'])
            sent=next(r for r in records if r.get('event')=='signal_sent' and r['data']['signal']==trigger['data']['signal'])
            assert sent['data']['rc']==sent['data']['error']==0 and sent['data']['child_pid']==trigger['data']['child_pid']
            if expected=='PASS':
                handlers=[r for r in records if r.get('event')=='signal_handler_observed']
                assert len(handlers)==1 and handlers[0]['data']['seen']==1
        cases.append({'case':tag,'verdict':result['verdict'],'reasons':result['reasons'],'builds':plan['builds'],
                      'host_elapsed_s':elapsed,'event_sha256':hashlib.sha256(raw).hexdigest()})
    rejected=[]
    reference=load(out/'job-signal-fixed-plan.json')
    variants=[('mode',lambda p:p['profile']['suite'].update(signal_mode='unknown')),
      ('error',lambda p:p['profile']['expectations'].update(cancel_error='ETIMEDOUT')),
      ('case',lambda p:p.update(case_id='timeout')),
      ('observer',lambda p:p['profile']['capabilities']['required'].remove('signal')),
      ('retry',lambda p:p['profile']['suite'].update(retry=1))]
    for tag,mutate in variants:
        p=copy.deepcopy(reference);p['run_id']=p['service_instance_id']=args.prefix+'-reject-'+tag;mutate(p)
        p['profile_sha256']=digest(p['profile']);p['suite_sha256']=digest(p['profile']['suite'])
        path=out/('reject-'+tag+'-plan.json');path.write_bytes(canonical(p)+b'\n')
        call(['scp','-F','.local/ssh_config',str(path),'resmgrcheck-qnx:'+remote+'/'])
        raw=call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx','cd '+remote+' && ./runner '+path.name+' --persist'],expected=2)
        assert not raw;ssh('test ! -e /data/resmgrcheck/runs/'+p['run_id'])
        rejected.append({'case':tag,'exit':2,'empty_stdout':True,'no_run_storage':True})
    (out/'native-rejections.json').write_text(json.dumps(rejected,indent=2)+'\n')
    inventory=ssh('pidin ar');(out/'post-inventory.txt').write_bytes(inventory)
    for line in inventory.decode().splitlines():
        tokens=line.split()
        if len(tokens)>1:assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'}
    (out/'index.json').write_text(json.dumps({'kind':'phase5-signal-native-matrix','readback_sha256':hashes,'cases':cases},indent=2)+'\n')
finally:
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (out/'partial-index.json').write_text(json.dumps(cases,indent=2)+'\n')
print('Signal-family subgate saved in',out)
