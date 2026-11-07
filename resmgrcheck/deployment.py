"""Stage, read back and publish immutable native builds in the owned lab."""
import copy
from dataclasses import dataclass
from pathlib import Path
import secrets
import shutil
import shlex
import tempfile

from .artifacts import atomic_write, bounded_read, evaluator_identity, sha256
from .build_identity import source_hash
from .contracts import (HASH, HEXREV, boolean, canonical, digest, enum, integer, load,
                        loads, obj, require, text, version)
from .registrations import CAPABILITIES, REGISTRY
from .replay import CandidateManifest, candidate_manifest
from .transport import Transport, compatible, target_identity

PAYLOAD = frozenset({'runner', 'worker'} | {r.fixture for r in REGISTRY.values()})
STATE = Path('.local/state')


def engine_info(raw):
    data = loads(raw)
    obj(data, 'kind schema_version adapter_abi adapters', 'engine description')
    version(data, 'engine-info'); integer(data['adapter_abi'], 1, 1)
    require(type(data['adapters']) is list and len(data['adapters']) == len(REGISTRY), 'engine registrations')
    result = {}
    for entry in data['adapters']:
        obj(entry, 'id fixture capabilities', 'engine adapter')
        require(entry['id'] in REGISTRY and entry['id'] not in result, 'unknown/duplicate engine adapter')
        require(entry['fixture'] == REGISTRY[entry['id']].fixture, 'engine fixture registration')
        require(type(entry['capabilities']) is list and len(entry['capabilities']) <= 16 and
                len(set(entry['capabilities'])) == len(entry['capabilities']) and set(entry['capabilities']) <= CAPABILITIES, 'engine capability declaration')
        result[entry['id']] = entry['capabilities']
    return result


def build_record(directory):
    directory = Path(directory)
    record = load(directory / 'build-info.json')
    obj(record, 'kind schema_version source_revision dirty source_tree_sha256 compiler_variant binaries', 'native build record')
    version(record, 'native-build-record'); text(record['source_revision'], HEXREV)
    boolean(record['dirty']); text(record['source_tree_sha256'], HASH)
    enum(record['compiler_variant'], {'gcc_ntox86_64'})
    require(type(record['binaries']) is dict and set(record['binaries']) in (PAYLOAD, PAYLOAD | {'targetctl'}), 'build binaries: unknown or missing artifacts')
    for name, expected in record['binaries'].items():
        text(expected, HASH)
        require(sha256(bounded_read(directory / name, 32 * 1024 * 1024)) == expected, 'build binary hash mismatch: ' + name)
    root = directory.resolve().parents[1]
    require((root / 'Makefile').is_file() and source_hash(root) == record['source_tree_sha256'], 'build source changed: run make qnx in its source checkout')
    return record


@dataclass(frozen=True)
class Deployment:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version deployment_id build recipe_id architecture machine release uid directory files manager candidates', 'deployment')
        version(d, 'deployed-build'); text(d['deployment_id'], HASH); text(d['recipe_id'], HASH)
        enum(d['architecture'], {'x86_64'}); enum(d['machine'], {'x86pc'}); enum(d['release'], {'8.0.0'}); integer(d['uid'], 0, 65535)
        require(d['directory'] == '/data/resmgrcheck/b-' + d['deployment_id'][:48], 'deployment directory/identity mismatch')
        require(type(d['files']) is dict and set(d['files']) == PAYLOAD | {'targetctl'}, 'deployment files')
        for name, entry in d['files'].items():
            obj(entry, 'sha256 bytes', 'deployment file'); text(entry['sha256'], HASH); integer(entry['bytes'], 1, 32 * 1024 * 1024)
        build = d['build']
        obj(build, 'kind schema_version source_revision dirty source_tree_sha256 compiler_variant binaries')
        version(build, 'native-build-record'); text(build['source_revision'], HEXREV); boolean(build['dirty'])
        text(build['source_tree_sha256'], HASH); enum(build['compiler_variant'], {'gcc_ntox86_64'})
        require(type(build['binaries']) is dict and set(build['binaries']) in (PAYLOAD, PAYLOAD | {'targetctl'}), 'native build artifact set')
        for name in build['binaries']:
            require(build['binaries'][name] == d['files'][name]['sha256'], 'native/deployment binary binding')
        obj(d['manager'], 'source_revision dirty source_tree_sha256 sha256')
        text(d['manager']['source_revision'], HEXREV); boolean(d['manager']['dirty']); text(d['manager']['source_tree_sha256'], HASH)
        require(d['manager']['sha256'] == d['files']['targetctl']['sha256'], 'management tool binding')
        require(type(d['candidates']) is dict and set(d['candidates']) == set(REGISTRY), 'candidate adapter set')
        for adapter, selected in d['candidates'].items():
            CandidateManifest.parse(selected)
            require(selected['adapter'] == {'id': adapter, 'abi': 1} and selected['directory'] == d['directory'], 'candidate deployment binding')
            expected = native_builds(d, adapter)
            require(selected['builds'] == expected, 'candidate source binding')
        descriptor = {k: v for k, v in d.items() if k not in ('deployment_id', 'directory', 'candidates')}
        require(digest(descriptor) == d['deployment_id'], 'deployment identity mismatch')
        return cls(copy.deepcopy(d))


def native_builds(deployment, adapter):
    source = deployment['build']
    return {**{k: source[k] for k in ('source_revision', 'dirty', 'source_tree_sha256', 'compiler_variant')},
            'recipe_id': deployment['recipe_id'], 'binaries': {key: source['binaries'][name] for key, name in {
                'runner': 'runner', 'worker': 'worker', 'adapter': 'worker', 'fixture': REGISTRY[adapter].fixture}.items()}}


def active_path(target):
    return STATE / target.name / 'deployment.json'


def load_deployment(target, path=None):
    try:
        deployment = Deployment.parse(load(path or active_path(target)))
    except FileNotFoundError as error:
        raise ValueError('deployment: none selected; run deploy --target ' + target.name) from error
    for key, target_key in [('architecture', 'processor'), ('machine', 'machine'), ('release', 'release'), ('recipe_id', 'recipe_id'), ('uid', 'uid')]:
        require(deployment.data[key] == target.data[target_key], 'deployment/target incompatible: ' + key)
    return deployment


def bootstrap(transport):
    """Bootstrap only in a fresh owned directory, then use the native file helper."""
    source = Path('build/qnx-x86_64/targetctl')
    require(source.is_file(), 'targetctl unavailable: source qnxsdp-env.sh and run make qnx')
    root = transport.target.data['root']
    transport.ssh('test -d ' + shlex.quote(root) + ' && test ! -L ' + shlex.quote(root) + ' && test -O ' + shlex.quote(root))
    directory = root + '/bootstrap-' + secrets.token_hex(8)
    transport.ssh('umask 077; mkdir ' + shlex.quote(directory))
    transport.upload(source, directory + '/targetctl')
    with tempfile.TemporaryDirectory() as temporary:
        readback = Path(temporary) / 'targetctl'
        transport.download(directory + '/targetctl', readback)
        require(sha256(source.read_bytes()) == sha256(readback.read_bytes()), 'bootstrap transfer hash mismatch')
    transport.ssh('chmod 700 ' + shlex.quote(directory + '/targetctl'))
    helper = directory + '/targetctl'
    info = loads(transport.command(helper, 'info'))
    require(info['kind'] == 'target-info' and info.get('management_protocol') == 1 and info['uid'] == transport.target.data['uid'], 'bootstrap protocol/owner mismatch')
    return helper


def verify_remote(transport, deployment, helper=None, evidence_path=None):
    d = deployment.data
    compatible(transport.target, target_identity(transport))
    helper = helper or d['directory'] + '/targetctl'
    info = loads(transport.command(helper, 'info'))
    require(info.get('management_protocol') == 1 and info['uid'] == transport.target.data['uid'], 'management protocol/owner mismatch')
    remote = Deployment.parse(loads(transport.command(helper, 'read-build', Path(d['directory']).name, 'manifest.json')))
    require(remote.data == d, 'remote deployment manifest mismatch')
    observed = {}
    with tempfile.TemporaryDirectory() as temporary:
        for name, identity in d['files'].items():
            path = Path(temporary) / name
            transport.download(d['directory'] + '/' + name, path)
            observed[name] = sha256(bounded_read(path, 32 * 1024 * 1024))
            if evidence_path:
                atomic_write(evidence_path, canonical({'deployment_id': d['deployment_id'],
                                                       'expected': d['files'], 'observed': observed}) + b'\n')
            require(path.stat().st_size == identity['bytes'] and observed[name] == identity['sha256'], 'deployed hash mismatch: ' + name)
    return observed


def deploy(target, directory):
    directory = Path(directory)
    record = build_record(directory)
    manager_record = build_record(Path('build/qnx-x86_64'))
    require('targetctl' in manager_record['binaries'], 'management tool build required')
    files = {name: directory / name for name in PAYLOAD}
    files['targetctl'] = Path('build/qnx-x86_64/targetctl')
    data = {'kind': 'deployed-build', 'schema_version': 1, 'build': record,
            'recipe_id': target.data['recipe_id'], 'architecture': 'x86_64', 'machine': 'x86pc',
            'release': '8.0.0', 'uid': target.data['uid'],
            'files': {name: {'sha256': sha256(path.read_bytes()), 'bytes': path.stat().st_size} for name, path in files.items()},
            'manager': {**{k: manager_record[k] for k in ('source_revision', 'dirty', 'source_tree_sha256')},
                        'sha256': manager_record['binaries']['targetctl']}}
    deployment_id = digest(data)
    data.update(deployment_id=deployment_id, directory=target.data['root'] + '/b-' + deployment_id[:48])
    data['candidates'] = {adapter: candidate_manifest(native_builds(data, adapter), {'id': adapter, 'abi': 1}, data['directory']).data for adapter in REGISTRY}
    deployment = Deployment.parse(data)
    transport = Transport(target)
    completed = False
    try:
        compatible(target, target_identity(transport))
        helper = bootstrap(transport)
        # Existing destinations are verified and reused, never replaced.
        existing = transport.command(helper, 'exists', Path(data['directory']).name, 'manifest.json', exits=(0, 2))
        # exists emits no bytes; its exact exit status determines presence.
        present = transport.record[-1]['exit'] == 0
        if not present:
            stage = 'stage-' + secrets.token_hex(10)
            transport.command(helper, 'create-stage', stage, deployment_id)
            for name, path in files.items():
                transport.upload(path, target.data['root'] + '/' + stage + '/' + name)
            with tempfile.TemporaryDirectory() as temporary:
                for name, expected in data['files'].items():
                    path = Path(temporary) / name
                    transport.download(target.data['root'] + '/' + stage + '/' + name, path)
                    require(path.stat().st_size == expected['bytes'] and sha256(path.read_bytes()) == expected['sha256'], 'staged transfer mismatch: ' + name)
                manifest = Path(temporary) / 'manifest.json'; manifest.write_bytes(canonical(data) + b'\n')
                transport.upload(manifest, target.data['root'] + '/' + stage + '/manifest.json')
            transport.command(helper, 'publish', stage, Path(data['directory']).name, deployment_id)
        hashes = verify_remote(transport, deployment, helper)
        state = active_path(target); state.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(state, canonical(data) + b'\n')
        atomic_write(state.parent / ('deploy-' + deployment_id + '.json'), canonical({'deployment': data, 'verified': hashes, 'commands': transport.record}) + b'\n')
        atomic_write(directory / 'manifest.json', canonical(data) + b'\n')
        completed = True
        return deployment
    finally:
        import sys
        diagnostic = STATE / target.name
        diagnostic.mkdir(parents=True, exist_ok=True)
        error = sys.exc_info()[0]
        atomic_write(diagnostic / ('deployment-attempt-' + secrets.token_hex(8) + '.json'),
                     canonical({'deployment_id': deployment_id, 'completed': completed,
                                'error': error.__name__ if error else None, 'commands': transport.record}) + b'\n')
