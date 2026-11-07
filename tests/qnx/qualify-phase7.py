#!/usr/bin/env python3
"""Actual QNX CLI workflow qualification. Fault proxies drop real SSH responses."""
import argparse
import copy
import json
import os
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from resmgrcheck.artifacts import atomic_write, evaluator_identity, sha256
from resmgrcheck.contracts import canonical, digest, load, text
from resmgrcheck.deployment import Deployment, load_deployment, native_builds
from resmgrcheck.replay import candidate_manifest
from resmgrcheck.transport import Target, Transport
from resmgrcheck.workflow import inspect_execution

parser = argparse.ArgumentParser()
parser.add_argument('--prefix', required=True)
parser.add_argument('--fixed-source', default='.local/phase6-fixed-source')
parser.add_argument('--section', action='append', choices=('workflow', 'external', 'negative', 'candidate', 'release'))
args = parser.parse_args(); text(args.prefix)
assert len(args.prefix) <= 24
sections = set(args.section or ('workflow', 'external', 'negative', 'candidate', 'release'))
out = Path('.local/evidence') / ('phase7-' + args.prefix); out.mkdir(exist_ok=False)
runroot = Path('runs') / args.prefix; runroot.mkdir(parents=True, exist_ok=False)
start_source = evaluator_identity(); commands = []; facts = {}
target = Target.read('lab'); transport = Transport(target)

def call(argv, expected=0, timeout=300, env=None):
    process = subprocess.run(list(map(str, argv)), capture_output=True, timeout=timeout, env=env)
    entry = {'argv': list(map(str, argv)), 'exit': process.returncode,
             'stdout': process.stdout.decode(errors='replace'), 'stderr': process.stderr.decode(errors='replace')}
    commands.append(entry)
    assert process.returncode == expected, entry
    return process.stdout

def cli(*argv, expected=0, timeout=300, env=None):
    return call([sys.executable, '-m', 'resmgrcheck', *argv], expected, timeout, env)

def identifier(suffix): return args.prefix + '-' + suffix

def do_run(name, profile, suite='profile', mode='fixed', expected=0, extra=()):
    path = runroot / name
    cli('run', '--target', 'lab', '--profile', profile, '--suite', suite, '--fixture-mode', mode,
        '--out', path, '--run-id', identifier(name), *extra, expected=expected)
    request, summary, _ = inspect_execution(path)
    facts[name] = {'run_id': request.data['run_id'], 'execution_exit': summary['execution_exit'], 'cases': summary['cases']}
    return path

def absent_native(request):
    for plan in (request.data if hasattr(request, 'data') else request)['cases']:
        call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'test ! -e /data/resmgrcheck/runs/' + plan['run_id']])

try:
    call(['make', 'qnx', 'QNX_VARIANT=gcc_ntox86_64'])
    cli('validate', 'profiles/sensor.json')
    cli('deploy', '--target', 'lab', '--build', 'build/qnx-x86_64')
    main_manifest = out / 'main-deployment.json'; main_manifest.write_bytes(canonical(load_deployment(target).data) + b'\n')
    cli('doctor', '--target', 'lab', '--out', out / 'doctor.json')
    (out / 'pre-inventory.txt').write_bytes(call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'pidin ar']))
    (out / 'storage-before.txt').write_bytes(call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'df /data']))
    if 'workflow' in sections:
        fixed = do_run('sensor-fixed', 'profiles/sensor.json', 'lifecycle')
        broken = do_run('sensor-broken', 'profiles/sensor.json', 'lifecycle', 'ignore-unblock', 2)
        recovered = runroot / 'sensor-recovered'
        cli('status', '--target', 'lab', '--run-id', identifier('sensor-fixed'), '--json')
        cli('collect', '--target', 'lab', '--run-id', identifier('sensor-fixed'), '--out', recovered, '--wait')
        before, _, _ = inspect_execution(fixed); after, _, _ = inspect_execution(recovered)
        assert before.data == after.data
        for original, collected in zip(sorted(fixed.glob('cases/*/bundle/observations.jsonl')), sorted(recovered.glob('cases/*/bundle/observations.jsonl'))):
            assert original.read_bytes() == collected.read_bytes()
        replayed = runroot / 'sensor-replay'
        cli('replay', broken / 'replay.json', '--target', 'lab', '--fixture-mode', 'fixed', '--out', replayed, '--run-id', identifier('sensor-replay'))
        cli('compare', broken, replayed, '--out', runroot / 'control-comparison')
        comparison = load(runroot / 'control-comparison/comparison.json')
        assert comparison['label'] == 'incomparable' and comparison['fixture_mode_changed']
        cli('report', replayed, '--out', replayed / 'report.html')
        cli('junit', fixed, broken, replayed, '--output', out / 'workflow.xml')
        assert '<script src=' not in (replayed / 'report.html').read_text()
        assert 'No network assets' in (replayed / 'report.html').read_text()
        facts['workflow'] = {'control_contrast_label': comparison['label'], 'collection_raw_equal': True}
    if 'external' in sections:
        call(['qcc', '-Vgcc_ntox86_64', '-std=c11', '-Wall', '-Wextra', '-Werror', 'tests/qnx/external-owner.c', '-o', '.local/p7-external-owner'])
        deployment = load_deployment(target).data
        remote = target.data['root'] + '/' + identifier('external')
        call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'mkdir ' + remote])
        call(['scp', '-F', '.local/ssh_config', '.local/p7-external-owner', 'resmgrcheck-qnx:' + remote + '/owner'])
        observations = []
        for service in ('sensor', 'job'):
            device = '/dev/resmgrcheck-external-' + identifier(service)
            profile = load('profiles/' + service + '-external.json'); profile['service']['device'] = device
            profile_path = out / (service + '-external-profile.json'); profile_path.write_bytes(canonical(profile) + b'\n')
            process = subprocess.Popen(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx',
                         remote + '/owner ' + deployment['directory'] + '/' + service + '-v1-fixture ' + device + ' ' + remote + '/' + service + '-events.jsonl'],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            def receive():
                selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
                try:
                    assert selector.select(8), 'owner response missing within bound'
                    raw = process.stdout.readline(); value = json.loads(raw); observations.append(value); return value
                finally: selector.close()
            def send(command): process.stdin.write(command + '\n'); process.stdin.flush(); return receive()
            ready = receive(); assert ready['ready'] == 1
            try:
                path = do_run(service + '-external', profile_path, 'health')
                alive = send('STATUS'); assert alive['child_pid'] == ready['child_pid'] and alive['reaped'] == 0
                _, _, results = inspect_execution(path)
                assert results[0].data['verdict'] == 'PASS'
                raw = (path / 'cases/external-health/bundle/observations.jsonl').read_bytes()
                rows = [json.loads(line) for line in raw.splitlines()]
                assert not any(r.get('event') in {'fixture_stop', 'signal_sent'} for r in rows)
                assert all(r['data']['binary'] == 'worker' for r in rows if r.get('event') == 'spawned')
                scope = next(r for r in rows if r.get('event') == 'external_scope')
                assert scope['data']['instance_verified'] == scope['data']['service_build_verified'] == 0
                unsupported = do_run(service + '-external-lifecycle', profile_path, 'lifecycle', expected=3)
                _, _, unsupported_results = inspect_execution(unsupported)
                assert all(r.data['verdict'] == 'UNSUPPORTED' for r in unsupported_results)
                for p in unsupported.glob('cases/*/bundle/observations.jsonl'):
                    assert not any(json.loads(line).get('event') == 'spawned' for line in p.read_bytes().splitlines())
                alive = send('STATUS'); assert alive['reaped'] == 0 and alive['child_pid'] == ready['child_pid']
            finally:
                stopped = send('STOP'); assert stopped['reaped'] == 1
                process.stdin.close(); assert process.wait(timeout=5) == 0
            (out / (service + '-external-owner-events.jsonl')).write_bytes(call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'cat ' + remote + '/' + service + '-events.jsonl']))
        (out / 'external-owner.json').write_bytes(canonical(observations) + b'\n')
        facts['external_ownership'] = {'original_pids_preserved': True, 'read_only_health_passed': 2,
                                       'private_lifecycle_unsupported': 12, 'explicit_owner_cleanup_reaped': 2}
    if 'negative' in sections:
        # Parser/configuration failures are host-only unless an actual target
        # observation below establishes compatibility or execution facts.
        cli('doctor', '--target', 'missing', expected=2)
        # A reserved, non-listening loopback port establishes a real connection
        # refusal without touching another host service or inventing target state.
        import socket
        reservation = socket.socket(); reservation.bind(('127.0.0.1', 0))
        unreachable_route = out / 'unreachable-ssh.local.conf'
        unreachable_route.write_text('Host lab-unreachable\n HostName 127.0.0.1\n Port ' + str(reservation.getsockname()[1]) + '\n User root\n StrictHostKeyChecking yes\n')
        unreachable = load('config/target.local.json')
        unreachable['targets']['lab'].update(ssh_alias='lab-unreachable', ssh_config=str(unreachable_route))
        unreachable_path = out / 'unreachable-target.local.json'; unreachable_path.write_bytes(canonical(unreachable) + b'\n')
        try:
            cli('doctor', '--target', 'lab', '--config', unreachable_path, '--out', out / 'unreachable-doctor.json', expected=2)
            cli('run', '--target', 'lab', '--config', unreachable_path, '--profile', 'profiles/sensor.json', '--suite', 'profile',
                '--run-id', identifier('unreachable'), '--out', runroot / 'unreachable', expected=2)
            absent_native(load(runroot / 'unreachable/request.json'))
        finally: reservation.close()
        invalid = load('profiles/sensor.json'); invalid['timing']['operation_ms'] = True
        invalid_path = out / 'invalid-profile.json'; invalid_path.write_bytes(canonical(invalid) + b'\n')
        cli('run', '--target', 'lab', '--profile', invalid_path, '--out', runroot / 'invalid', expected=2)
        assert not (runroot / 'invalid').exists()
        occupied = runroot / 'occupied'; occupied.mkdir(); (occupied / 'unrelated').write_bytes(b'preserve exact bytes')
        cli('run', '--target', 'lab', '--profile', 'profiles/sensor.json', '--out', occupied, expected=2)
        assert (occupied / 'unrelated').read_bytes() == b'preserve exact bytes'
        configuration = load('config/target.local.json')
        for label, field, value in [('wrong-architecture', 'processor', 'aarch64'), ('incompatible-target', 'release', '7.1.0')]:
            altered = copy.deepcopy(configuration); altered['targets']['lab'][field] = value
            path = out / (label + '-target.local.json'); path.write_bytes(canonical(altered) + b'\n')
            cli('doctor', '--target', 'lab', '--config', path, '--out', out / (label + '-doctor.json'), expected=2)
            assert any(c['id'] == 'target_compatibility' and c['state'] == 'ERROR' for c in load(out / (label + '-doctor.json'))['checks'])
            cli('run', '--target', 'lab', '--config', path, '--profile', 'profiles/sensor.json', '--out', runroot / label, expected=2)
            assert not (runroot / label).exists()
        cli('doctor', '--target', 'lab', '--profile', 'profiles/sensor-unsupported-capability.json', '--out', out / 'unsupported-doctor.json', expected=3)
        unsupported = do_run('unsupported', 'profiles/sensor-unsupported-capability.json', expected=3)
        _, _, results = inspect_execution(unsupported); assert results[0].data['verdict'] == 'UNSUPPORTED'
        # Existing unknown session data must not be adopted, replaced or removed.
        collision_id = identifier('occupied-session'); remote = '/data/resmgrcheck/sessions/' + collision_id
        call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'mkdir ' + remote + ' && printf preserve > ' + remote + '/unrelated'])
        cli('run', '--target', 'lab', '--profile', 'profiles/sensor.json', '--suite', 'profile', '--run-id', collision_id, '--out', runroot / 'occupied-session', expected=2)
        assert call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'cat ' + remote + '/unrelated']) == b'preserve'
        absent_native(load(runroot / 'occupied-session/request.json'))
        # Actual OpenSSH forwarder: drop an already generated native launch ACK,
        # or pause an already returned native status while the owned CLI is interrupted.
        proxy = out / 'transport-proxy'; proxy.mkdir(); log = out / 'actual-dropped-ack.json'
        script = '''#!/usr/bin/env python3
import os,subprocess,sys,time
from pathlib import Path
args=sys.argv[1:]; command=args[-1] if args else ''
mode=os.environ.get('RMC_QUALIFY_TRANSPORT')
if mode=='drop-ack' and '/runner ' in command and '--persist' in command:
 p=subprocess.run(['/usr/bin/ssh',*args],capture_output=True)
 Path(os.environ['RMC_QUALIFY_OBSERVATION']).write_bytes(p.stdout)
 sys.stderr.write('qualification: actual launch response dropped\\n');sys.exit(255)
if mode=='pause-status' and 'read-run' in command and 'status.json' in command and not Path(os.environ['RMC_QUALIFY_OBSERVATION']).exists():
 p=subprocess.run(['/usr/bin/ssh',*args],capture_output=True)
 if p.returncode==0 and b'"running"' in p.stdout:
  Path(os.environ['RMC_QUALIFY_OBSERVATION']).write_bytes(p.stdout);time.sleep(3)
 sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);sys.exit(p.returncode)
os.execv('/usr/bin/ssh',['/usr/bin/ssh',*args])
'''
        (proxy / 'ssh').write_text(script); (proxy / 'ssh').chmod(0o700)
        env = dict(os.environ); env['PATH'] = str(proxy.resolve()) + os.pathsep + env['PATH']
        env.update(RMC_QUALIFY_TRANSPORT='drop-ack', RMC_QUALIFY_OBSERVATION=str(log.resolve()))
        uncertain = runroot / 'uncertain'; uncertain_id = identifier('uncertain')
        cli('run', '--target', 'lab', '--profile', 'profiles/sensor.json', '--suite', 'profile', '--out', uncertain, '--run-id', uncertain_id, expected=2, env=env)
        initial = load(uncertain / 'result.json'); assert initial['execution_exit'] == 2 and initial['cases'][0]['verdict'] == 'ERROR'
        dropped = load(log); assert dropped['kind'] == 'run-started' and dropped['run_id'] == uncertain_id + '-timeout'
        assert not (uncertain / 'cases/timeout/ack.json').exists()
        cli('status', '--target', 'lab', '--run-id', uncertain_id, '--json')
        cli('collect', '--target', 'lab', '--run-id', uncertain_id, '--out', uncertain, '--wait')
        _, _, results = inspect_execution(uncertain); assert results[0].data['verdict'] == 'PASS'
        assert load(uncertain / 'history/collection-000001/result.json')['execution_exit'] == 2
        prefix = uncertain / 'history/collection-000001/timeout/partial-events.jsonl'
        if prefix.exists(): assert (uncertain / 'cases/timeout/bundle/observations.jsonl').read_bytes().startswith(prefix.read_bytes())
        assert load(uncertain / 'cases/timeout/bundle/status.json')['supervisor_pid'] == dropped['supervisor_pid']
        assert not (uncertain / 'cases/timeout/ack.json').exists()
        paused = out / 'actual-paused-status.json'
        env.update(RMC_QUALIFY_TRANSPORT='pause-status', RMC_QUALIFY_OBSERVATION=str(paused.resolve()))
        interrupted = runroot / 'interrupted'; interrupted_id = identifier('interrupted')
        argv = [sys.executable, '-m', 'resmgrcheck', 'run', '--target', 'lab', '--profile', 'profiles/sensor-repeat.json', '--suite', 'profile', '--out', str(interrupted), '--run-id', interrupted_id]
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        end = time.monotonic() + 12
        while not paused.exists():
            assert process.poll() is None and time.monotonic() < end, 'actual running status not observed'
            time.sleep(.02)
        actual_running = load(paused); assert actual_running['state'] == 'running'
        process.send_signal(signal.SIGINT); stdout, stderr = process.communicate(timeout=12)
        commands.append({'argv': argv, 'exit': process.returncode, 'stdout': stdout.decode(), 'stderr': stderr.decode()})
        assert process.returncode == 130
        cli('status', '--target', 'lab', '--run-id', interrupted_id, '--json')
        cli('collect', '--target', 'lab', '--run-id', interrupted_id, '--out', interrupted, '--wait')
        _, _, results = inspect_execution(interrupted); assert results[0].data['verdict'] == 'PASS'
        assert load(interrupted / 'history/collection-000001/result.json')['execution_exit'] == 130
        prefix = interrupted / 'history/collection-000001/repeat/partial-events.jsonl'
        if prefix.exists(): assert (interrupted / 'cases/repeat/bundle/observations.jsonl').read_bytes().startswith(prefix.read_bytes())
        assert load(interrupted / 'cases/repeat/bundle/status.json')['supervisor_pid'] == actual_running['supervisor_pid']
        # Delete no state: temporarily move the exact local selection receipt,
        # recover solely from the remote request by ID, then restore its bytes.
        from resmgrcheck.deployment import active_path
        selection = active_path(target); backup = out / 'selection-backup.local.json'
        selected_bytes = selection.read_bytes(); selection.rename(backup)
        try:
            cli('status', '--target', 'lab', '--run-id', uncertain_id, '--json')
            cli('collect', '--target', 'lab', '--run-id', uncertain_id, '--out', runroot / 'receipt-recovered', '--wait')
            assert inspect_execution(runroot / 'receipt-recovered')[0].data == inspect_execution(uncertain)[0].data
        finally:
            backup.rename(selection); assert selection.read_bytes() == selected_bytes
        # Deliberately publish incorrect expected hashes through the isolated lab
        # injector. Product deploy itself always verifies hashes before publication.
        d = copy.deepcopy(load_deployment(target).data)
        d['files']['runner']['sha256'] = '0'*64; d['build']['binaries']['runner'] = '0'*64
        descriptor = {k: v for k, v in d.items() if k not in ('deployment_id', 'directory', 'candidates')}
        d['deployment_id'] = digest(descriptor); d['directory'] = '/data/resmgrcheck/b-' + d['deployment_id'][:48]
        d['candidates'] = {k: candidate_manifest(native_builds(d, k), {'id': k, 'abi': 1}, d['directory']).data for k in d['candidates']}
        Deployment.parse(d)
        good = load_deployment(target).data; helper = good['directory'] + '/targetctl'
        stage = identifier('hash-stage'); transport.command(helper, 'create-stage', stage, d['deployment_id'])
        fault_files = out / 'binary-readback'; fault_files.mkdir()
        for name in good['files']:
            local = fault_files / name; transport.download(good['directory'] + '/' + name, local)
            transport.upload(local, '/data/resmgrcheck/' + stage + '/' + name)
        wrong = out / 'wrong-hash-manifest.json'; wrong.write_bytes(canonical(d) + b'\n')
        transport.upload(wrong, '/data/resmgrcheck/' + stage + '/manifest.json')
        transport.command(helper, 'publish', stage, Path(d['directory']).name, d['deployment_id'])
        cli('run', '--target', 'lab', '--profile', 'profiles/sensor.json', '--suite', 'profile', '--candidate-manifest', wrong,
            '--out', runroot / 'wrong-hash', '--run-id', identifier('wrong-hash'), expected=2)
        hashes = load(runroot / 'wrong-hash/diagnostics/deployment-hashes.json')
        assert hashes['observed']['runner'] != hashes['expected']['runner']['sha256']
        absent_native(load(runroot / 'wrong-hash/request.json'))
        facts['negative'] = {'unknown_target': 2, 'unreachable_route': 2, 'invalid_profile': 2, 'occupied_output': 2, 'wrong_architecture': 2,
                             'incompatible_target': 2, 'required_capability': 3, 'unknown_session_preserved': True,
                             'ack_loss_recovered_same_supervisor': True, 'interrupted_exit': 130,
                             'interruption_recovered_same_supervisor': True, 'local_selection_loss_recovered': True, 'hash_mismatch_no_launch': True}
    if 'candidate' in sections:
        original_paths = {}
        for service in ('sensor', 'job'):
            original_paths[service] = do_run(service + '-source-before', 'profiles/' + service + '.json', mode='ignore-unblock', expected=1)
        fixed = Path(args.fixed_source).resolve()
        call(['make', '-C', fixed, 'qnx', 'QNX_VARIANT=gcc_ntox86_64'])
        cli('deploy', '--target', 'lab', '--build', fixed / 'build/qnx-x86_64')
        candidate = fixed / 'build/qnx-x86_64/manifest.json'
        (out / 'selected-source-candidate.json').write_bytes(candidate.read_bytes())
        (out / 'source-correction.patch').write_bytes(call(['git', '-C', fixed, 'show', '--format=fuller', '--no-ext-diff', 'HEAD', '--', 'native/fixtures/sensor.c', 'native/fixtures/job.c']))
        comparisons = []
        for service, original in original_paths.items():
            after = runroot / (service + '-source-after')
            cli('replay', original / 'replay.json', '--target', 'lab', '--candidate-manifest', candidate, '--out', after, '--run-id', identifier(service + '-source-after'))
            cli('compare', original, after, '--out', runroot / (service + '-source-comparison'))
            comparison = load(runroot / (service + '-source-comparison') / 'comparison.json')
            assert comparison['label'] == 'fixed' and not comparison['fixture_mode_changed']
            left, _, _ = inspect_execution(original); right, _, _ = inspect_execution(after)
            assert left.data['cases'][0]['profile'] == right.data['cases'][0]['profile']
            assert left.data['cases'][0]['builds']['binaries']['fixture'] != right.data['cases'][0]['builds']['binaries']['fixture']
            comparisons.append(comparison)
        facts['candidate_replay'] = comparisons
        cli('deploy', '--target', 'lab', '--build', 'build/qnx-x86_64')
    if 'release' in sections:
        cli('verify', '--target', 'lab', '--suite', 'release', '--out', runroot / 'release', timeout=300)
        verification = load(runroot / 'release/result.json')
        assert verification['qualification_passed'] and len(verification['cases']) == 36 and all(c['matched'] for c in verification['cases'])
        facts['release'] = verification
    inventory = call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'pidin ar'])
    (out / 'post-inventory.txt').write_bytes(inventory)
    for line in inventory.decode().splitlines():
        tokens = line.split()
        if len(tokens) > 1: assert Path(tokens[1]).name not in {'runner', 'worker', 'sensor-v1-fixture', 'job-v1-fixture', 'owner'}
    (out / 'storage-after.txt').write_bytes(call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'df /data']))
    end_source = evaluator_identity(); assert start_source == end_source, 'source changed during qualification; do not relabel these observations'
    (out / 'index.json').write_bytes(canonical({'kind': 'phase7-native-workflow-gate', 'schema_version': 1,
            'source': start_source, 'sections': sorted(sections), 'complete_gate': args.section is None,
            'runs': str(runroot), 'facts': facts}) + b'\n')
finally:
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    (out / 'partial-facts.json').write_bytes(canonical(facts) + b'\n')
    transport.save(out / 'injection-commands.json')
print('Actual QNX Phase7 records:', out, '; executions:', runroot)
