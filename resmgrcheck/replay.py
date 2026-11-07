"""Explicit deployed-build selection and one-attempt replay in the owned QNX lab."""
import copy
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import subprocess
import time

from .artifacts import atomic_write, bounded_read, create_bundle, inspect_bundle, sha256
from .contracts import (HASH, Invalid, Plan, RunStarted, RunStatus, builds, canonical,
                        digest, enum, integer, loads, obj, require, text, version)
from .evaluator import Evidence
from .exports import compare, execution_exit
from .registrations import REGISTRY


@dataclass(frozen=True)
class CandidateManifest:
    data: dict

    @classmethod
    def parse(cls, data):
        obj(data, 'kind schema_version build_id builds adapter architecture target_machine directory executables', 'candidate')
        version(data, 'candidate-build'); builds(data['builds'])
        obj(data['adapter'], 'id abi'); enum(data['adapter']['id'], REGISTRY)
        integer(data['adapter']['abi'], 1, 1)
        enum(data['architecture'], {'x86_64'}); enum(data['target_machine'], {'x86pc'})
        directory = data['directory']
        require(type(directory) is str and re.fullmatch(r'/data/resmgrcheck/[A-Za-z0-9][A-Za-z0-9_-]{0,63}', directory), 'unsafe deployment directory')
        obj(data['executables'], 'runner worker fixture adapter')
        names = {'runner': 'runner', 'worker': 'worker', 'adapter': 'worker',
                 'fixture': REGISTRY[data['adapter']['id']].fixture}
        require(data['executables'] == {k: directory + '/' + v for k, v in names.items()}, 'executable layout mismatch')
        text(data['build_id'], HASH)
        require(data['build_id'] == digest({k: data[k] for k in ('builds', 'adapter', 'architecture', 'target_machine')}), 'candidate build identity')
        return cls(copy.deepcopy(data))


def candidate_manifest(build, adapter, directory):
    """Describe a selected deployment; replay still verifies actual target bytes."""
    value = {'kind': 'candidate-build', 'schema_version': 1, 'builds': build,
             'adapter': adapter, 'architecture': 'x86_64', 'target_machine': 'x86pc',
             'directory': directory}
    value['build_id'] = digest({k: value[k] for k in ('builds', 'adapter', 'architecture', 'target_machine')})
    value['executables'] = {k: directory + '/' + name for k, name in {
        'runner': 'runner', 'worker': 'worker', 'adapter': 'worker',
        'fixture': REGISTRY[adapter['id']].fixture}.items()}
    return CandidateManifest.parse(value)


class LabTransport:
    """Reuse local authentication. No target/command/credential strings from profiles."""
    def __init__(self, configuration, record):
        self.configuration = str(configuration)
        self.record = record

    def call(self, argv, *, data=None, timeout=8, exits=(0,)):
        process = subprocess.run(argv, input=data, capture_output=True, timeout=timeout)
        self.record.append({'argv': argv, 'exit': process.returncode})
        require(process.returncode in exits, 'lab command failed (exit ' + str(process.returncode) + ')')
        require(len(process.stdout) <= 32 * 1024 * 1024, 'lab response exceeds bound')
        return process.stdout

    def ssh(self, command, **options):
        return self.call(['ssh', '-F', self.configuration, 'resmgrcheck-qnx', command], **options)

    def download(self, remote, local):
        self.call(['scp', '-F', self.configuration, 'resmgrcheck-qnx:' + remote, str(local)])


def replay(bundle_path, candidate_path, attempts, run_id, ssh_configuration):
    original = inspect_bundle(bundle_path)
    candidate = CandidateManifest.parse(loads(bounded_read(candidate_path))).data
    text(run_id)
    require(candidate['adapter'] == original.plan.data['profile']['adapter'], 'incompatible adapter')
    require(candidate['architecture'] == 'x86_64', 'incompatible target architecture')
    require(Evidence(original.raw, original.plan).lab_control == 'none', 'lab fault injection replay is unsupported')
    old_target = loads((original.path / 'target-manifest.json').read_bytes())['target']
    require(candidate['target_machine'] == old_target['machine'], 'incompatible target machine')
    require(candidate['builds']['recipe_id'] == original.plan.data['builds']['recipe_id'], 'incompatible target recipe')
    require(run_id != original.plan.data['run_id'], 'replay needs a fresh run ID')
    attempt_root = Path(attempts) / original.manifest.data['bundle_id']
    attempt_root.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in attempt_root.iterdir()]
    require(all(re.fullmatch(r'attempt[1-9][0-9]*', n) for n in names), 'unknown replay attempt entry')
    old_attempt = re.fullmatch(r'attempt([1-9][0-9]*)', original.plan.data['attempt_id'])
    require(old_attempt is not None, 'unsupported original attempt identity')
    number = max([int(old_attempt[1])] + [int(n[7:]) for n in names]) + 1
    integer(number, 2, 1000000)
    path = attempt_root / ('attempt' + str(number))
    path.mkdir()  # Exclusive reservation; concurrent callers do not rerun on collision.
    record = {'kind': 'replay-attempt', 'schema_version': 1, 'attempt_count': number,
              'original_bundle_id': original.manifest.data['bundle_id'],
              'candidate_build_id': candidate['build_id'], 'run_id': run_id, 'state': 'preflight',
              'launch_requested': False, 'acknowledged': False, 'execution_exit': None, 'bundle_id': None}
    commands = []
    transport = LabTransport(ssh_configuration, commands)
    atomic_write(path / 'attempt.json', canonical(record) + b'\n')
    atomic_write(path / 'candidate.json', canonical(candidate) + b'\n')
    plan = copy.deepcopy(original.plan.data)
    plan.update(run_id=run_id, service_instance_id=run_id, attempt_id='attempt' + str(number), builds=candidate['builds'])
    plan = Plan.parse(plan)
    atomic_write(path / 'plan.json', canonical(plan.data) + b'\n')
    remote_run = '/data/resmgrcheck/runs/' + run_id
    try:
        processor = transport.ssh('uname -p').decode('ascii').strip()
        machine = transport.ssh('uname -m').decode('ascii').strip()
        require(processor == candidate['architecture'] and machine == candidate['target_machine'], 'actual target architecture mismatch')
        readback = path / 'readback'
        readback.mkdir()
        verified = {}
        checks = []
        for role in ('runner', 'worker', 'fixture'):
            destination = readback / role
            transport.download(candidate['executables'][role], destination)
            require(destination.stat().st_size <= 32 * 1024 * 1024, 'binary readback exceeds bound')
            observed = sha256(destination.read_bytes())
            checks.append({'role': role, 'expected': candidate['builds']['binaries'][role], 'observed': observed})
            atomic_write(path / 'hash-checks.json', canonical(checks) + b'\n')
            require(observed == candidate['builds']['binaries'][role], 'deployed artifact hash mismatch: ' + role)
            verified[role] = observed
        require(candidate['builds']['binaries']['adapter'] == verified['worker'], 'static adapter identity mismatch')
        atomic_write(path / 'verified.json', canonical({'architecture': processor, 'machine': machine,
                                                       'binaries': verified}) + b'\n')
        transport.ssh('test ! -e ' + shlex.quote(remote_run))
        remote_plan = candidate['directory'] + '/' + run_id + '-plan.json'
        transport.ssh('umask 077; set -C; cat > ' + shlex.quote(remote_plan), data=canonical(plan.data) + b'\n')
        record.update(state='launch-requested', launch_requested=True)
        atomic_write(path / 'attempt.json', canonical(record) + b'\n')
        ack = transport.ssh('cd ' + shlex.quote(candidate['directory']) + ' && ./runner ' + shlex.quote(Path(remote_plan).name) + ' --persist')
        started = RunStarted.parse(loads(ack)).data
        require(all(started[k] == plan.data[k] for k in ('run_id', 'case_id', 'attempt_id', 'cycle', 'service_instance_id')), 'launch acknowledgement mismatch')
        atomic_write(path / 'start.json', ack)
        record.update(state='running', acknowledged=True)
        atomic_write(path / 'attempt.json', canonical(record) + b'\n')
        limit = plan.profile.timing.execution_ms / 1000 * (plan.profile.data['suite']['cycles'] + 1) + plan.profile.timing.cleanup_ms / 1000 + 10
        end = time.monotonic() + limit
        while True:
            remaining = end - time.monotonic()
            require(remaining > 0, 'target completion unestablished; collect by original run ID')
            status_raw = transport.ssh('cat ' + shlex.quote(remote_run + '/status.json'), timeout=min(8, remaining))
            status = RunStatus.parse(loads(status_raw)).data
            atomic_write(path / 'status.json', status_raw)
            if status['state'] != 'running':
                break
            time.sleep(min(.2, remaining))
        raw = transport.ssh('cat ' + shlex.quote(remote_run + '/' + status['event_file']))
        atomic_write(path / 'observations.jsonl', raw)
        atomic_write(path / 'stderr.txt', transport.ssh('cat ' + shlex.quote(remote_run + '/stderr.log')))
        result = create_bundle(path / 'bundle', canonical(plan.data) + b'\n', raw, status_raw)
        comparison = compare(original, result)
        # An explicitly selected changed build is visible even when non-reproduction occurs.
        comparison['candidate_build_id'] = candidate['build_id']
        atomic_write(path / 'comparison.json', canonical(comparison) + b'\n')
        code = execution_exit([result.result])
        record.update(state='collected', execution_exit=code, bundle_id=result.manifest.data['bundle_id'])
        return path, result, comparison, code
    except BaseException as error:
        record.update(state='incomplete', execution_exit=130 if isinstance(error, KeyboardInterrupt) else 2,
                      error_type=type(error).__name__)
        if record['launch_requested']:
            try:
                atomic_write(path / 'partial-observations.jsonl', transport.ssh('cat ' + shlex.quote(remote_run + '/events.jsonl')))
            except (Invalid, OSError, subprocess.SubprocessError):
                pass
        raise
    finally:
        atomic_write(path / 'attempt.json', canonical(record) + b'\n')
        atomic_write(path / 'commands.json', canonical(commands) + b'\n')
