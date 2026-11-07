#!/usr/bin/env python3
"""Real, bounded QNX failure qualification. Explicitly labeled owned-lab controls."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import selectors
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import load,loads,canonical,text,RunStarted,RunStatus
from resmgrcheck.planning import expand
from resmgrcheck.evaluator import evaluate_persistent
from resmgrcheck.outcomes import infrastructure_error
from resmgrcheck.build_identity import source_hash

parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);parser.add_argument('--case',action='append');args=parser.parse_args()
text(args.prefix);text(args.prefix+'-readiness')
out=Path('.local/evidence')/('phase4-matrix-'+args.prefix);out.mkdir(exist_ok=False)
remote='/data/resmgrcheck/'+args.prefix;commands=[];cases=[];last_cleanup=None;last_ownership=None
storage=None;storage_lines=[]

def call(argv,expected=0,timeout=15):
    p=subprocess.run(argv,capture_output=True,timeout=timeout)
    commands.append({'argv':list(map(str,argv)),'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert p.returncode in expected if isinstance(expected,tuple) else p.returncode==expected,commands[-1]
    return p

def ssh(command,expected=0,timeout=15):return call(['ssh','-F','.local/ssh_config','resmgrcheck-qnx',command],expected,timeout)
def get(run,name,expected=0,timeout=6):return ssh('cat '+shlex.quote('/data/resmgrcheck/runs/'+run+'/'+name),expected,timeout).stdout

def wait_status(run):
    end=time.monotonic()+16
    while time.monotonic()<end:
        raw=get(run,'status.json',timeout=min(6,max(.1,end-time.monotonic())))
        status=RunStatus.parse(loads(raw)).data
        if status['state']!='running':return raw,status
        time.sleep(.03)
    raise TimeoutError('target completion unestablished; do not relaunch')

matrix=[
 ('normal','none','job','corrected','PASS',{'all_obligations_satisfied'}),
 ('normal_read','none','sensor','corrected','PASS',{'all_obligations_satisfied'}),
 ('stuck','worker_stuck','job','corrected','ERROR',{'worker_timeout'}),
 ('crash','worker_crash','sensor','corrected','ERROR',{'worker_crashed'}),
 ('start','worker_start_failed','job','corrected','ERROR',{'worker_start_failed'}),
 ('unavailable','service_unavailable','sensor','corrected','ERROR',{'service_unavailable'}),
 ('readiness','readiness_blocked','job','corrected','ERROR',{'probe_timeout'}),
 ('health','health_blocked','sensor','corrected','ERROR',{'probe_timeout'}),
 ('malformed','malformed','job','corrected','ERROR',{'evidence_invalid','evidence_incomplete'}),
 ('truncated','truncated','sensor','corrected','ERROR',{'evidence_incomplete'}),
 ('oversize','oversize','job','corrected','ERROR',{'evidence_invalid','evidence_incomplete'}),
 ('capacity','event_overflow','sensor','corrected','ERROR',{'evidence_capacity_exceeded','evidence_incomplete'}),
 ('channel','channel_full','job','corrected','ERROR',{'evidence_loss','evidence_capacity_exceeded','evidence_incomplete'}),
 ('sink','sink_unavailable','sensor','corrected','ERROR',{'event_sink_failed','evidence_incomplete'}),
 ('quota','sink_quota','job','ignore-unblock','ERROR',{'event_sink_failed','cancellation_not_completed','evidence_incomplete'}),
 ('manager','manager_interference','sensor','corrected','ERROR',{'service_interference'}),
 ('manager_pending','manager_pending','job','corrected','ERROR',{'service_interference','worker_close_failed'}),
 ('fixture_sink','fixture_evidence_loss','job','corrected','ERROR',{'service_interference','evidence_loss','evidence_incomplete'}),
 ('late','late_malformed','job','ignore-unblock','ERROR',{'evidence_invalid','cancellation_not_completed','evidence_incomplete'}),
 ('cleanup','cleanup_failure','sensor','ignore-unblock','ERROR',{'cleanup_failed','cancellation_not_completed','pending_state_not_released'}),
 ('dependent','none','sensor','corrected','NOT_RUN',{'prior_cleanup_failed'}),
 ('ownership','ownership_lost','job','corrected','ERROR',{'ownership_unknown','cleanup_failed','evidence_incomplete'}),
 ('owned_dep','none','job','corrected','NOT_RUN',{'prior_cleanup_failed'}),
 ('unsupported','none','sensor','corrected','UNSUPPORTED',{'required_capability_missing'}),
]
if args.case:matrix=[c for c in matrix if c[0] in args.case]
try:
    ssh('mkdir '+shlex.quote(remote))
    binaries=[Path('build/qnx-x86_64')/n for n in ('runner','worker','sensor-v1-fixture','job-v1-fixture')]
    call(['scp','-F','.local/ssh_config',*map(str,binaries),'resmgrcheck-qnx:'+remote+'/'])
    rb=out/'readback';rb.mkdir();hashes={}
    for path in binaries:
        call(['scp','-F','.local/ssh_config','resmgrcheck-qnx:'+remote+'/'+path.name,str(rb/path.name)])
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256((rb/path.name).read_bytes()).hexdigest()==hashes[path.name]
    ssh('cd '+shlex.quote(remote)+' && chmod 755 runner worker sensor-v1-fixture job-v1-fixture')
    (out/'pre-inventory.txt').write_bytes(ssh('pidin ar').stdout)
    if any(c[0]=='quota' for c in matrix):
        call(['bash','-c','source /home/mignon/qnx800/qnxsdp-env.sh && qcc -Vgcc_ntox86_64 -std=c11 -D_QNX_SOURCE -Wall -Wextra -Werror tests/qnx/fill-storage.c -o .local/fill-storage'])
        support=remote+'/storage';ssh('mkdir '+shlex.quote(support))
        call(['scp','-F','.local/ssh_config','.local/fill-storage','tests/qnx/full-storage.sh','/home/mignon/qnx800/target/qnx/x86_64/sbin/mkqnx6fs','resmgrcheck-qnx:'+support+'/'])
        ssh('chmod 755 '+support+'/fill-storage '+support+'/mkqnx6fs')
        (out/'storage-preflight.txt').write_bytes(ssh(support+'/fill-storage --preflight').stdout)
        storage=subprocess.Popen(['ssh','-F','.local/ssh_config','resmgrcheck-qnx','sh '+support+'/full-storage.sh '+support],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        sel=selectors.DefaultSelector();sel.register(storage.stdout,selectors.EVENT_READ)
        end=time.monotonic()+10;buffer=b''
        while b'STORAGE_READY\n' not in buffer:
            assert time.monotonic()<end,'storage setup timed out'
            if sel.select(.1):
                chunk=os.read(storage.stdout.fileno(),4096)
                assert chunk,'storage setup exited early'
                storage_lines.append(chunk)
                buffer+=chunk
        sel.close()
        filled=next(loads(line) for line in buffer.splitlines() if line.startswith(b'{'))
        assert filled['write_errno']==filled['enospc']==28
    for tag,control,service,mode,verdict,reasons in matrix:
        profile=load('profiles/'+service+'.json')
        if tag=='unsupported':profile['capabilities']['required'].append('error-probe')
        plan=expand(profile,args.prefix+'-'+tag,mode).data;run=plan['run_id']
        assert plan['builds']['source_tree_sha256']==source_hash()
        path=out/(tag+'-plan.json');path.write_bytes(canonical(plan)+b'\n')
        call(['scp','-F','.local/ssh_config',str(path),'resmgrcheck-qnx:'+remote+'/'])
        options=['--persist']
        if control!='none':options+=['--lab='+control]
        if tag=='dependent':assert last_cleanup;options+=['--after='+last_cleanup]
        if tag=='owned_dep':assert last_ownership;options+=['--after='+last_ownership]
        command='cd '+shlex.quote(remote)+' && '+shlex.join(['./runner',path.name,*options])
        started=time.monotonic();ack=ssh(command).stdout
        RunStarted.parse(loads(ack));(out/(tag+'-start.json')).write_bytes(ack)
        raw_status,status=wait_status(run)
        elapsed=time.monotonic()-started
        assert elapsed<16
        (out/(tag+'-status.json')).write_bytes(raw_status)
        event_file=status.get('event_file','events.jsonl')
        assert event_file in ('events.jsonl','recovery.jsonl')
        raw=get(run,event_file);(out/(tag+'-events.jsonl')).write_bytes(raw)
        (out/(tag+'-stderr.txt')).write_bytes(get(run,'stderr.log'))
        primary=get(run,'events.jsonl');(out/(tag+'-primary.jsonl')).write_bytes(primary)
        if event_file=='recovery.jsonl':assert raw.startswith(primary),'recovery must preserve original written prefix'
        result=evaluate_persistent(plan,raw,status).data
        (out/(tag+'-result.json')).write_bytes(canonical(result)+b'\n')
        print(tag,result['verdict'],result['reasons'],flush=True)
        assert result['verdict']==verdict and reasons==set(result['reasons']),result
        records=[loads(s) for s in raw.splitlines()]
        if tag=='quota':assert any(r.get('event')=='problem' and r['data']['reason']=='event_sink_failed' and r['data']['error']==28 for r in records),'actual ENOSPC required'
        assert len({r['pid'] for r in records if r.get('producer')=='supervisor'})==1
        spawned={r['data']['child_pid'] for r in records if r.get('event')=='spawned'}
        reaped={r['data']['child_pid'] for r in records if r.get('event')=='reaped'}
        for r in records:
            if r.get('event')=='signal_sent':assert r['data']['child_pid'] in spawned
            if r.get('event')=='wait_bound' and r['data']['timed_out']:assert int(r['ns'])>=int(r['data']['deadline_ns'])
        if status['cleanup_ok']:assert spawned==reaped and not status['unresolved']
        if tag in ('dependent','owned_dep','unsupported'):assert not spawned
        if tag=='cleanup':
            last_cleanup=run
            end=time.monotonic()+4
            while True:
                p=ssh('cat '+shlex.quote('/data/resmgrcheck/runs/'+run+'/recovery.json'),expected=(0,1))
                if p.returncode:
                    if time.monotonic()>end:raise TimeoutError('owned recovery not observed')
                    time.sleep(.03);continue
                recovery=loads(p.stdout)
                if recovery['all_reaped']:break
                if time.monotonic()>end:raise TimeoutError('owned recovery failed')
                time.sleep(.03)
            (out/'cleanup-lab-recovery.json').write_bytes(p.stdout)
            assert recovery['all_reaped']==1 and int(recovery['finished_ns'])-int(recovery['started_ns'])<=2000000000+100000000
            assert get(run,'status.json')==raw_status,'recovery must not erase original cleanup failure'
        if tag=='ownership':
            last_ownership=run
            unknown={r['data']['child_pid'] for r in records if r.get('event')=='problem' and r['data']['reason']=='ownership_unknown'}
            assert unknown and not any(r.get('event')=='signal_sent' and r['data']['child_pid'] in unknown for r in records)
        cases.append({'case':tag,'lab_control':control,'verdict':result['verdict'],'reasons':result['reasons'],
          'host_elapsed_s':elapsed,'event_count':len(records),'event_file':event_file,'cleanup_ok':status['cleanup_ok'],
          'spawned':sorted(spawned),'reaped':sorted(reaped),'source_builds':plan['builds'],
          'event_sha256':hashlib.sha256(raw).hexdigest()})
    inventory=ssh('pidin ar').stdout;(out/'post-inventory.txt').write_bytes(inventory)
    for line in inventory.decode().splitlines():
        tokens=line.split()
        if len(tokens)>1:assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'}
    (out/'index.json').write_text(json.dumps({'kind':'phase4-native-matrix','binary_readback_sha256':hashes,'cases':cases},indent=2)+'\n')
finally:
    try:
        if storage:
            stdout,stderr=storage.communicate(b'finish\n',timeout=10)
            storage_lines.extend([stdout,stderr]);(out/'storage-lifecycle.txt').write_bytes(b''.join(storage_lines))
    finally:
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        (out/'partial-index.json').write_text(json.dumps(cases,indent=2)+'\n')
    if storage:
        assert storage.returncode==0,'isolated storage cleanup failed'
        assert b'storage_driver_reaped=' in stdout,'driver reaping not recorded'
print('Native failure matrix saved in',out)
