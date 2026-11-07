#!/usr/bin/env python3
"""Real QNX fixed-message input gate. Combined custom operations are unsupported."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from resmgrcheck.artifacts import evaluator_identity,sha256
from resmgrcheck.contracts import canonical,loads
from resmgrcheck.deployment import load_deployment,verify_remote
from resmgrcheck.transport import Target,Transport
from resmgrcheck.workflow import run_id

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix',required=True);p.add_argument('--out',required=True)
p.add_argument('--target',default='lab');p.add_argument('--config',default='config/target.local.json')
a=p.parse_args();run_id(a.prefix);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
source=evaluator_identity();t=Transport(Target.read(a.target,a.config));deployment=load_deployment(t.target)
entries=[];commands=[]
try:
    probe=out/'message-bounds';argv=['qcc','-Vgcc_ntox86_64','-std=c11','-Wall','-Wextra','-Werror','tests/qnx/message-bounds.c','-o',str(probe)]
    built=subprocess.run(argv,capture_output=True,timeout=90)
    (out/'build.txt').write_bytes(built.stdout+built.stderr);commands.append({'argv':argv,'exit':built.returncode});assert built.returncode==0
    verify_remote(t,deployment);helper=deployment.data['directory']+'/targetctl';remote='/data/resmgrcheck/'+a.prefix
    t.command(helper,'create-stage',a.prefix,sha256(probe.read_bytes()));t.upload(probe,remote+'/probe')
    readback=out/'readback';t.download(remote+'/probe',readback);assert sha256(probe.read_bytes())==sha256(readback.read_bytes())
    t.ssh('chmod 700 '+shlex.quote(remote+'/probe'))
    (out/'deployment.json').write_bytes(canonical(deployment.data)+b'\n')
    for service in ('sensor','job'):
        argv=[remote+'/probe',deployment.data['directory']+'/'+service+'-v1-fixture','/dev/resmgrcheck-'+a.prefix+'-'+service,service,remote+'/'+service+'-fixture.jsonl']
        command=' '.join(shlex.quote(v) for v in argv)
        process=subprocess.run(['ssh','-F',t.target.data['ssh_config'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',t.target.data['ssh_alias'],command],capture_output=True,timeout=15)
        (out/(service+'-stdout.jsonl')).write_bytes(process.stdout);(out/(service+'-stderr.txt')).write_bytes(process.stderr)
        t.download(remote+'/'+service+'-fixture.jsonl',out/(service+'-fixture.jsonl'))
        rows=[loads(line) for line in process.stdout.splitlines()]
        required={'state-baseline','wrong-declared-size','short-reply-buffer','truncated-control','surplus-control','readonly-control','unknown-control-action','readonly-mutation','combined-custom-framework-rejection','combined-prefix-framework-rejection'}
        required |= {'reserved-job-input','unknown-job','truncated-job-input'} if service=='job' else {'truncated-read-framework-rejection','short-read-buffer'}
        checks=[r for r in rows if 'matched' in r]
        fresh=[r for r in rows if r.get('case')=='same-instance-fresh-client']
        reaped=[r for r in rows if 'owned_probe_pid' in r]
        stopped=[r for r in rows if 'owned_fixture_pid' in r]
        passed=(process.returncode==0 and process.stdout.endswith(b'\n') and len(rows)==len(required)+5
                and rows[0].get('preflight_waitpid_observed') is True and rows[0]['preflight_status']==0
                and len(checks)==len(required) and {r['case'] for r in checks}==required
                and all(r['matched'] and r['error']==r['expected_error'] for r in checks)
                and len(fresh)==1 and fresh[0]['failures']==0 and fresh[0]['initial_generation']==fresh[0]['final_generation']==fresh[0]['fresh_generation']
                and len(reaped)==1 and reaped[0]['waitpid_observed'] and reaped[0]['status']==0
                and len(stopped)==1 and stopped[0]['rc']==0 and stopped[0]['owned_fixture_pid']!=reaped[0]['owned_probe_pid']
                and rows[-1].get('passed') is True and rows[-1]['fixture_waitpid_observed'] and rows[-1]['probe_waitpid_observed'])
        entries.append({'service':service,'exit':process.returncode,'passed':passed,'observations':rows})
        commands.append({'argv':argv,'exit':process.returncode})
        if not passed:break
    assert evaluator_identity()==source,'source changed during input qualification'
finally:
    t.save(out/'transport-commands.json');(out/'commands.json').write_bytes(canonical(commands)+b'\n')
    value={'kind':'native-input-bounds-qualification','schema_version':1,'source':source,'cases':entries,
           'driver_source_sha256':sha256(Path('tests/qnx/message-bounds.c').read_bytes()),
           'driver_binary_sha256':sha256(probe.read_bytes()) if probe.exists() else None,
           'combined_custom_operations':'unsupported; tested prefixes rejected before any claim of tail execution',
           'passed':len(entries)==2 and all(e['passed'] for e in entries)}
    (out/'index.json').write_bytes(canonical(value)+b'\n')
if not value['passed']:raise SystemExit(2)
print('Both real QNX services: exact rejection codes, unchanged state, fresh health and actual owned-child reaping passed')
