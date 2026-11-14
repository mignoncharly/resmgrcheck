#!/usr/bin/env python3
"""Execute one owned external-backend probe; preserve bytes and never auto-retry."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from resmgrcheck.contracts import canonical, require
from resmgrcheck.artifacts import guard_derived_output
from resmgrcheck.transport import Target, Transport, target_identity, compatible
from check import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True); parser.add_argument('--config', required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--signal', action='store_true')
    args = parser.parse_args()
    target = Target.read(args.target, args.config)
    require(target.data['uid'] == 0, 'QFuse public admin channel requires the root lab target')
    binary = ROOT / 'build/qfuse-integration/probe'; data = binary.read_bytes()
    require(data.startswith(b'\x7fELF') and data[4:6] == b'\x02\x01', 'build the QNX x86_64 probe with qcc first')
    build = json.loads(binary.with_name('build.json').read_text())
    require(build['compiler'] == 'qcc' and build['variant'] == 'gcc_ntox86_64', 'unqualified native compiler variant')
    for field, path in [('binary_sha256', binary), ('probe_source_sha256', Path(__file__).with_name('probe.c')),
                        ('sources_lock_sha256', Path(__file__).with_name('sources.lock.json'))]:
        require(build[field] == hashlib.sha256(path.read_bytes()).hexdigest(), 'native build/source identity differs: ' + field)
    guard_derived_output(args.out, [])
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.mkdir()
    transport = Transport(target)
    identifier = 'qfuse-' + uuid.uuid4().hex
    remote = '/data/resmgrcheck-' + identifier
    record = {'kind': 'external-backend-integration', 'schema_version': 1, 'run_id': identifier,
              'target_identity': target.public(), 'remote_directory': remote,
              'binary_sha256': hashlib.sha256(data).hexdigest(),
              'probe_source_sha256': hashlib.sha256(Path(__file__).with_name('probe.c').read_bytes()).hexdigest(),
              'sources_lock_sha256': hashlib.sha256(Path(__file__).with_name('sources.lock.json').read_bytes()).hexdigest(),
              'source_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'mode': 'signal' if args.signal else 'timeout', 'state': 'prepared'}
    record['build'] = build
    def save(): (args.out / 'execution.json').write_bytes(canonical(record) + b'\n')
    save()
    try:
        compatible(target, target_identity(transport))
        transport.ssh('test -d /data && test ! -L /data && mkdir ' + shlex.quote(remote))
        transport.upload(binary, remote + '/probe')
        transport.download(remote + '/probe', args.out / 'binary-readback')
        require((args.out / 'binary-readback').read_bytes() == data, 'transferred QNX binary differs')
        (args.out / 'binary-readback').unlink()
        transport.command('chmod', '700', remote + '/probe')
        record['state'] = 'launch_intent'; save()
        invocation = shlex.quote(remote + '/probe') + (' --signal' if args.signal else '')
        command = invocation + ' > ' + shlex.quote(remote + '/events.jsonl') + ' 2> ' + shlex.quote(remote + '/stderr.txt')
        transport.ssh(command, timeout=35, exits=(0, 2, 124))
        record['native_exit'] = transport.record[-1]['exit']
        transport.download(remote + '/events.jsonl', args.out / 'events.jsonl')
        transport.download(remote + '/stderr.txt', args.out / 'stderr.txt')
        raw = (args.out / 'events.jsonl').read_bytes()
        record['events_sha256'] = hashlib.sha256(raw).hexdigest()
        result = evaluate(raw, record['native_exit'])
        (args.out / 'result.json').write_bytes(canonical(result) + b'\n')
        record.update(state='collected', verdict=result['verdict']); save()
        print(json.dumps({'run_id': identifier, 'verdict': result['verdict'], 'output': str(args.out)}))
        return 0 if result['verdict'] == 'PASS' else 1 if result['verdict'] == 'FAIL' else 2
    finally:
        transport.save(args.out / 'transport.json')


if __name__ == '__main__':
    sys.exit(main())
