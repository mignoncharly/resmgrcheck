#!/usr/bin/env python3
"""Pause only the exact owned, idle lab VM; never infer remote cleanup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.contracts import canonical,load,text
from resmgrcheck.planning import expand
from resmgrcheck.outcomes import infrastructure_error

parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);args=parser.parse_args();text(args.prefix)
out=Path('.local/evidence')/('phase4-target-'+args.prefix);out.mkdir(exist_ok=False)
argv=['ssh','-F','.local/ssh_config','resmgrcheck-qnx','pidin ar']
before=subprocess.run(argv,capture_output=True,timeout=5,check=True).stdout
(out/'pre-inventory.txt').write_bytes(before)
for line in before.decode().splitlines():
    tokens=line.split()
    if len(tokens)>1:assert Path(tokens[1]).name not in {'runner','worker','sensor-v1-fixture','job-v1-fixture'},'VM must be idle'
matches=[]
for proc in Path('/proc').glob('[0-9]*'):
    try:
        cmd=(proc/'cmdline').read_bytes().split(b'\0')
        if (proc.stat().st_uid==os.getuid() and cmd and b'qemu-system-x86_64' in cmd[0]
          and any(b'.local/qnx-lab/run.qcow2' in s for s in cmd)
          and any(b'hostfwd=tcp:127.0.0.1:22220-:22' in s for s in cmd)):
            matches.append((int(proc.name),(proc/'stat').read_text().split(') ',1)[1].split()[19]))
    except (FileNotFoundError,PermissionError):pass
assert len(matches)==1,'exact owned lab VM identity required'
pid,start=matches[0]
def current():return Path('/proc/'+str(pid)+'/stat').read_text().split(') ',1)[1].split()[19]==start
guardian_code="import pathlib,os,signal,sys,time;time.sleep(3);p=pathlib.Path('/proc/'+sys.argv[1]+'/stat');same=p.exists() and p.read_text().split(') ',1)[1].split()[19]==sys.argv[2];same and os.kill(int(sys.argv[1]),signal.SIGCONT)"
guardian=subprocess.Popen([sys.executable,'-c',guardian_code,str(pid),start])
record={'owned_qemu_pid':pid,'proc_start_ticks':start,'target_idle':True,'ssh_argv':argv,'timeout_s':.8}
plan=expand(load('profiles/job.json'),args.prefix+'-targetwide').data
(out/'plan.json').write_bytes(canonical(plan)+b'\n')
began=time.monotonic()
try:
    assert current();os.kill(pid,signal.SIGSTOP);record['pause_sent']=True
    try:
        p=subprocess.run(argv,capture_output=True,timeout=.8)
        record['ssh_exit']=p.returncode
        raise AssertionError('paused target unexpectedly responded')
    except subprocess.TimeoutExpired as error:
        record.update(host_timeout=True,elapsed_s=time.monotonic()-began)
        partial=error.stdout or b'';record['partial_stdout_sha256']=hashlib.sha256(partial).hexdigest()
        (out/'partial.txt').write_bytes(partial)
        result=infrastructure_error(plan,'target_unreachable',partial).data
        assert result['verdict']=='ERROR' and result['reasons']==['target_unreachable']
        assert next(a for a in result['assertions'] if a['id']=='remote_cleanup')['verdict']=='NOT_RUN'
        (out/'result.json').write_bytes(canonical(result)+b'\n')
finally:
    assert current();os.kill(pid,signal.SIGCONT);record['resume_sent']=True
    guardian.wait(timeout=4)
    (out/'commands.json').write_text(json.dumps(record,indent=2)+'\n')
after=subprocess.run(argv,capture_output=True,timeout=5,check=True).stdout
(out/'post-inventory.txt').write_bytes(after)
assert record['elapsed_s']<2
print('Actual paused QNX VM: ERROR target_unreachable; remote cleanup NOT_RUN; owned VM resumed')
