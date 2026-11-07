#!/usr/bin/env python3
"""Real QNX Phase 5 qualification. Expected defect verdicts are never rewritten."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import canonical,load,loads,text,RunStatus,RunStarted
from resmgrcheck.planning import expand
from resmgrcheck.evaluator import evaluate_persistent

parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);parser.add_argument('--case',action='append');parser.add_argument('--raw',action='store_true');args=parser.parse_args()
text(args.prefix);text(args.prefix+'-job-complete-first-duplicate-terminal')
out=Path('.local/evidence')/('phase5-'+args.prefix);out.mkdir(exist_ok=False)
remote='/data/resmgrcheck/'+args.prefix;commands=[];cases=[]
def call(argv,expected=0,timeout=8):
    p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':list(map(str,argv)),'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert (p.returncode in expected if isinstance(expected,tuple) else p.returncode==expected),commands[-1]
    return p.stdout
def ssh(command,expected=0):return call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command],expected)
def get(run,name):return ssh('cat '+shlex.quote('/data/resmgrcheck/runs/'+run+'/'+name))
matrix=[]
for service in ('sensor','job'):
    for family,modes in [('timeout',('corrected','ignore-unblock','retain-waiter','duplicate-terminal')),('signal',('corrected','ignore-unblock')),
       ('departure',('corrected','retain-waiter','ignore-unblock')+(('drop-job',) if service=='job' else ())),
       ('repeat',('corrected','retain-third','ignore-unblock')),
       ('complete-first',('corrected','duplicate-terminal')),('cancel-first',('corrected','duplicate-terminal'))]:
        matrix.extend((service,family,mode,'none') for mode in modes)
    matrix.extend([(service,'repeat','corrected','cycle_probe_stuck'),(service,'repeat','ignore-unblock','cleanup_failure'),(service,'unsupported-signal','corrected','none')])
matrix.append(('sensor','unsupported-capability','corrected','none'))
def tag_of(case):
    service,family,mode,control=case
    return '-'.join((service,family,mode))+('-probe' if control=='cycle_probe_stuck' else '-cleanup' if control=='cleanup_failure' else '')
if args.case:matrix=[c for c in matrix if tag_of(c) in args.case]
assert matrix,'no selected native cases'
try:
    plans={}
    for service,family,mode,control in matrix:
        tag=tag_of((service,family,mode,control));base_family='signal' if family=='unsupported-signal' else 'timeout' if family=='unsupported-capability' else family
        name=service+('' if base_family=='timeout' else '-'+base_family)
        profile=load('profiles/'+name+'.json')
        if family=='unsupported-signal':profile['suite']['signal_mode']='auto-restart'
        if family=='unsupported-capability':profile['capabilities']['required'].append('error-probe')
        plans[tag]=expand(profile,args.prefix+'-'+tag,mode).data
        (out/(tag+'-plan.json')).write_bytes(canonical(plans[tag])+b'\n')
    ssh('mkdir '+remote)
    binaries=[Path('build/qnx-x86_64')/n for n in ('runner','worker','sensor-v1-fixture','job-v1-fixture')]
    call(['scp','-F','.local/ssh_config',*map(str,binaries),'resmgrcheck-qnx:'+remote+'/'])
    rb=out/'readback';rb.mkdir();hashes={}
    for p in binaries:
        call(['scp','-F','.local/ssh_config','resmgrcheck-qnx:'+remote+'/'+p.name,str(rb/p.name)])
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256((rb/p.name).read_bytes()).hexdigest()==hashes[p.name]
    ssh('cd '+remote+' && chmod 755 runner worker sensor-v1-fixture job-v1-fixture')
    (out/'pre-inventory.txt').write_bytes(ssh('pidin ar'));(out/'storage-before.txt').write_bytes(ssh('df /data'))
    for service,family,mode,control in matrix:
        tag=tag_of((service,family,mode,control));plan=plans[tag];run=plan['run_id'];path=out/(tag+'-plan.json')
        call(['scp','-F','.local/ssh_config',str(path),'resmgrcheck-qnx:'+remote+'/'])
        start=time.monotonic();ack=ssh('cd '+remote+' && ./runner '+path.name+' --persist'+(' --lab='+control if control!='none' else ''))
        RunStarted.parse(loads(ack));(out/(tag+'-start.json')).write_bytes(ack)
        limit=plan['profile']['timing']['execution_ms']/1000*(plan['profile']['suite']['cycles']+1)+10
        while time.monotonic()-start<limit:
            status_raw=get(run,'status.json');status=RunStatus.parse(loads(status_raw)).data
            if status['state']!='running':break
            time.sleep(.1)
        else:raise TimeoutError('completion unestablished; preserve original run ID')
        raw=get(run,status['event_file']);elapsed=time.monotonic()-start
        for suffix,value in [('events.jsonl',raw),('status.json',status_raw),('stderr.txt',get(run,'stderr.log'))]:
            (out/(tag+'-'+suffix)).write_bytes(value)
        if args.raw:
            print(tag,'raw',status['state'],'cleanup',status['cleanup_ok'],flush=True)
            cases.append({'case':tag,'source_builds':plan['builds'],'status':status,'event_sha256':hashlib.sha256(raw).hexdigest()});continue
        result=evaluate_persistent(plan,raw,status).data
        (out/(tag+'-result.json')).write_bytes(canonical(result)+b'\n')
        expected='UNSUPPORTED' if family.startswith('unsupported-') else 'ERROR' if control!='none' or family=='departure' and mode=='ignore-unblock' else 'PASS' if mode=='corrected' else 'FAIL'
        reasons={'all_obligations_satisfied'} if mode=='corrected' else {'duplicate_terminal_attempt'} if mode=='duplicate-terminal' else {'unexpected_service_state','unexpected_operation_result'} if mode=='drop-job' else {'pending_state_not_released'} if mode in ('retain-waiter','retain-third') else {'cancellation_not_completed','pending_state_not_released'}
        if family.startswith('unsupported-'):reasons={'signal_mode_unsupported' if family=='unsupported-signal' else 'required_capability_missing'}
        if family=='departure' and mode=='ignore-unblock':reasons={'departure_unobserved'}
        if control=='cycle_probe_stuck':reasons={'probe_timeout','repetition_incomplete'}
        if family=='repeat' and mode!='corrected':reasons.add('repetition_incomplete')
        if control=='cleanup_failure':reasons.add('cleanup_failed')
        print(tag,result['verdict'],result['reasons'],flush=True)
        assert result['verdict']==expected and set(result['reasons'])==reasons,result
        records=[loads(s) for s in raw.splitlines()]
        spawned={r['data']['child_pid'] for r in records if r.get('event')=='spawned'};reaped={r['data']['child_pid'] for r in records if r.get('event')=='reaped'}
        assert elapsed<limit
        if control!='cleanup_failure':assert spawned==reaped and status['cleanup_ok'] and not status['unresolved']
        else:
            assert not status['cleanup_ok'] and len(status['unresolved'])==2 and reaped<spawned
            end=time.monotonic()+4
            while True:
                recovery=ssh('cat /data/resmgrcheck/runs/'+run+'/recovery.json',expected=(0,1))
                if recovery:break
                assert time.monotonic()<end,'owned recovery unestablished';time.sleep(.05)
            restored=loads(recovery);assert restored['all_reaped']==1
            (out/(tag+'-recovery.json')).write_bytes(recovery)
            assert get(run,'status.json')==status_raw,'recovery must not erase original cleanup failure'
        if family=='repeat':
            assert len(result['cycles'])==20
            if control=='cycle_probe_stuck':assert [c['verdict'] for c in result['cycles']]==['PASS','ERROR']+['NOT_RUN']*18
            elif mode=='corrected':assert all(c['verdict']=='PASS' for c in result['cycles'])
            elif mode=='retain-third':assert [c['verdict'] for c in result['cycles']]==['PASS','PASS','FAIL']+['NOT_RUN']*17
            else:assert [c['verdict'] for c in result['cycles']]==['FAIL']+['NOT_RUN']*19
            assert len([r for r in records if r.get('event')=='ready'])==1
        cases.append({'case':tag,'lab_control':control,'verdict':result['verdict'],'reasons':result['reasons'],'completion':result['completion'],
          'source_builds':plan['builds'],'host_elapsed_s':elapsed,'event_count':len(records),'event_sha256':hashlib.sha256(raw).hexdigest()})
    rejected=[]
    import copy
    from resmgrcheck.contracts import digest
    reference=plans[next(k for k in plans if k.endswith('repeat-corrected'))] if any(k.endswith('repeat-corrected') for k in plans) else None
    if reference and not args.raw:
        for name,change in [('cycles',lambda p:p['profile']['suite'].update(cycles=21)),('reset',lambda p:p['profile']['suite'].update(reset='new-instance')),('cycle-id',lambda p:p.update(cycle=2)),('case',lambda p:p.update(case_id='departure'))]:
            p=copy.deepcopy(reference);p['run_id']=p['service_instance_id']=args.prefix+'-reject-'+name;change(p)
            p['profile_sha256']=digest(p['profile']);p['suite_sha256']=digest(p['profile']['suite'])
            path=out/('reject-'+name+'-plan.json');path.write_bytes(canonical(p)+b'\n')
            call(['scp','-F','.local/ssh_config',str(path),'resmgrcheck-qnx:'+remote+'/'])
            assert not call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx','cd '+remote+' && ./runner '+path.name+' --persist'],expected=2)
            ssh('test ! -e /data/resmgrcheck/runs/'+p['run_id'])
            rejected.append({'case':name,'exit':2,'empty_stdout':True,'no_run_storage':True})
    (out/'native-rejections.json').write_text(json.dumps(rejected,indent=2)+'\n')
    inventory=ssh('pidin ar');(out/'post-inventory.txt').write_bytes(inventory);(out/'storage-after.txt').write_bytes(ssh('df /data'))
    for line in inventory.decode().splitlines():
        tokens=line.split()
        if len(tokens)>1:assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'}
    (out/'index.json').write_text(json.dumps({'kind':'phase5-native-matrix','raw_debug_only':args.raw,'binary_readback_sha256':hashes,'cases':cases},indent=2)+'\n')
finally:
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'partial-index.json').write_text(json.dumps(cases,indent=2)+'\n')
print('Native Phase 5 observations saved in',out)
