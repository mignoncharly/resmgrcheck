"""Readiness observations with explicit unknown and unsupported states."""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile

from .contracts import Profile, canonical, digest, loads, require
from .deployment import active_path, bootstrap, engine_info, load_deployment, verify_remote
from .registrations import CAPABILITIES, REGISTRY
from .transport import Transport, compatible, target_identity


def doctor(target, profile=None):
    checks = []
    def add(name, state, detail): checks.append({'id': name, 'state': state, 'detail': detail})
    host = sys.version_info >= (3, 10) and all(shutil.which(n) for n in ('ssh', 'scp')) and Path(target.data['ssh_config']).is_file()
    add('host', 'PASS' if host else 'ERROR', 'Python >=3.10 and OpenSSH with local routing available' if host else 'Python/OpenSSH or configured SSH file unavailable')
    sdk = all(os.environ.get(n) and Path(os.environ[n]).is_dir() for n in ('QNX_HOST', 'QNX_TARGET'))
    add('sdk', 'PASS' if sdk else 'ERROR', 'installed SDK environment available' if sdk else 'source the installed qnxsdp-env.sh')
    compiler = shutil.which('qcc')
    if compiler:
        p = subprocess.run([compiler, '-V'], capture_output=True, timeout=8)
        available = b'gcc_ntox86_64' in p.stdout + p.stderr
        add('compiler_variant', 'PASS' if available else 'ERROR', 'gcc_ntox86_64 available' if available else 'gcc_ntox86_64 unavailable')
    else: add('compiler_variant', 'UNKNOWN', 'qcc unavailable in this shell; compiler licensing has not been tested')
    transport = Transport(target)
    try:
        identity = target_identity(transport)
        add('target_reachable', 'PASS', 'OpenSSH reached the configured alias')
        try:
            compatible(target, identity)
            add('target_compatibility', 'PASS', str(identity))
        except ValueError as error: add('target_compatibility', 'ERROR', str(error))
        shell = transport.ssh('command -v sh').decode('ascii').strip()
        add('ssh_command_path', 'PASS' if shell.startswith('/') else 'ERROR', shell)
        if Path('build/qnx-x86_64/targetctl').is_file():
            helper = bootstrap(transport)
            stage = 'probe-' + secrets.token_hex(10); token = secrets.token_hex(32).encode('ascii')
            transport.command(helper, 'create-stage', stage, digest({'token': token.decode('ascii')}))
            with tempfile.TemporaryDirectory() as temporary:
                sent = Path(temporary) / 'sent'; received = Path(temporary) / 'received'; sent.write_bytes(token)
                remote = target.data['root'] + '/' + stage + '/probe'
                transport.upload(sent, remote); transport.download(remote, received)
                require(received.read_bytes() == token, 'SFTP roundtrip mismatch')
            add('transfer', 'PASS', 'actual SFTP roundtrip bytes matched in an exclusive owned probe directory')
        else: add('transfer', 'UNKNOWN', 'build targetctl with make qnx to qualify file transfer/ownership')
        if active_path(target).is_file():
            deployment = load_deployment(target)
            verify_remote(transport, deployment)
            raw = transport.command(deployment.data['directory'] + '/worker', '--describe', exits=(0, 2))
            if transport.record[-1]['exit'] == 2:
                add('target_capabilities', 'UNKNOWN', 'selected older engine has no capability discovery command')
            else:
                capabilities = engine_info(raw)
                missing = []
                if profile:
                    p = profile if isinstance(profile, Profile) else Profile.parse(profile)
                    missing = sorted(set(p.data['capabilities']['required']) - set(capabilities.get(p.data['adapter']['id'],[])))
                add('target_capabilities', 'UNSUPPORTED' if missing else 'PASS', {'compiled_adapter_capabilities': capabilities, 'missing_required': missing})
                add('service_instance_capabilities', 'UNKNOWN', 'no service instance was launched; private observers are qualified during run, not inferred here')
        else: add('target_capabilities', 'UNKNOWN', 'no immutable deployment selected; run deploy then doctor again')
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        if not any(c['id'] == 'target_reachable' for c in checks): add('target_reachable', 'ERROR', str(error).splitlines()[0])
        else: add('target_probe', 'ERROR', str(error).splitlines()[0])
    names = {c['id'] for c in checks}
    for name in ('target_compatibility', 'ssh_command_path', 'transfer', 'target_capabilities'):
        if name not in names: add(name, 'UNKNOWN', 'not established after an earlier prerequisite failure')
    required = [c for c in checks if c['id'] != 'service_instance_capabilities']
    code = 2 if any(c['state'] == 'ERROR' for c in required) else 3 if any(c['state'] != 'PASS' for c in required) else 0
    return {'kind': 'doctor-result', 'schema_version': 1, 'target': target.name, 'checks': checks,
            'execution_exit': code, 'capability_scope': 'compiled engine declarations; service instance remains unverified'}, transport.record
