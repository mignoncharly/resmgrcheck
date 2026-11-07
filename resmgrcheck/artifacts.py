"""Immutable, integrity-checked run bundles. Reports never modify source evidence."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import subprocess

from .contracts import (IDENTITY, HASH, HEXREV, EvaluatedResult, Invalid, Plan, ReplayInput,
                        RunStatus, TargetManifest, canonical, digest, integer,
                        boolean, loads, obj, require, text, version)
from .evaluator import evaluate_persistent

FILES = frozenset({'observations.jsonl', 'plan.json', 'profile.json', 'builds.json',
                   'target-manifest.json', 'status.json', 'result.json', 'replay.json', 'notes.txt'})
RAW_LIMIT = 32 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    """Publish a finished file on the same filesystem; preserve its old value on error."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def bounded_read(path, limit=1024 * 1024):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'bundle member must be a regular file')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    require(len(data) <= limit, 'artifact exceeds size bound')
    return data


@dataclass(frozen=True)
class BundleManifest:
    data: dict

    @classmethod
    def parse(cls, data):
        obj(data, 'kind schema_version bundle_id ' + IDENTITY + ' evaluator files', 'bundle manifest')
        version(data, 'run-bundle')
        from .contracts import identity
        identity(data)
        text(data['bundle_id'], HASH)
        obj(data['evaluator'], 'source_revision dirty source_tree_sha256', 'evaluator identity')
        text(data['evaluator']['source_revision'], HEXREV); boolean(data['evaluator']['dirty'])
        text(data['evaluator']['source_tree_sha256'], HASH)
        require(type(data['files']) is dict and set(data['files']) == FILES, 'bundle files')
        for name, entry in data['files'].items():
            obj(entry, 'sha256 bytes', 'file identity')
            text(entry['sha256'], HASH)
            integer(entry['bytes'], 0, RAW_LIMIT)
        descriptor = {k: v for k, v in data.items() if k != 'bundle_id'}
        require(digest(descriptor) == data['bundle_id'], 'bundle identity mismatch')
        return cls(data)


def evaluator_identity():
    from .build_identity import source_hash
    root = Path(__file__).resolve().parents[1]
    return {'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)),
            'source_tree_sha256': source_hash(root)}


@dataclass(frozen=True)
class Bundle:
    path: Path
    manifest: BundleManifest
    plan: Plan
    result: EvaluatedResult
    raw: bytes
    status: dict


def create_bundle(output, plan_bytes, raw, status_bytes):
    """An exclusive directory preserves partial artifacts even if validation fails."""
    output = Path(output)
    output.mkdir()  # Never overwrite an earlier attempt or its partial evidence.
    atomic_write(output / 'partial.json', canonical({'kind': 'partial-run', 'schema_version': 1,
                                                     'state': 'collecting'}) + b'\n')
    try:
        require(type(raw) is bytes and len(raw) <= RAW_LIMIT, 'event stream exceeds 32 MiB')
        atomic_write(output / 'observations.jsonl', raw)
        atomic_write(output / 'plan.json', plan_bytes)
        atomic_write(output / 'status.json', status_bytes)
        plan = Plan.parse(loads(plan_bytes))
        status = RunStatus.parse(loads(status_bytes)).data
        first = raw.split(b'\n', 1)[0] + b'\n'
        native = TargetManifest.parse(loads(first)).data
        result = evaluate_persistent(plan, raw, status).data
        replay = ReplayInput.parse({'kind': 'replay-input', 'schema_version': 1,
                                   'original_plan': plan.data, 'original_event_sha256': sha256(raw),
                                   'selected_builds': plan.data['builds']}).data
        payload = {'profile.json': plan.data['profile'], 'builds.json': plan.data['builds'],
                   'target-manifest.json': native, 'result.json': result, 'replay.json': replay}
        for name, value in payload.items():
            atomic_write(output / name, canonical(value) + b'\n')
        note = (f"Run {plan.data['run_id']}, case {plan.data['case_id']}, {plan.data['attempt_id']}.\n"
                f"{result['verdict']} / {result['completion']}: {', '.join(result['reasons'])}.\n"
                'Raw observations and status are preserved bytes. The final bundle marker seals\n'
                'artifact integrity; it does not assert a passing service or successful cleanup.\n')
        atomic_write(output / 'notes.txt', note.encode('ascii'))
        descriptor = {'kind': 'run-bundle', 'schema_version': 1,
                      **{k: plan.data[k] for k in IDENTITY.split()},
                      'evaluator': evaluator_identity(),
                      'files': {name: {'sha256': sha256((output / name).read_bytes()),
                                       'bytes': (output / name).stat().st_size} for name in sorted(FILES)}}
        manifest = BundleManifest.parse({**descriptor, 'bundle_id': digest(descriptor)}).data
        # Validate every written member before publishing the final marker.
        _validate_payload(output, manifest)
        (output / 'partial.json').unlink()
        atomic_write(output / 'bundle.json', canonical(manifest) + b'\n')
        for name in FILES | {'bundle.json'}:
            (output / name).chmod(0o444)
        output.chmod(0o555)
        return inspect_bundle(output)
    except BaseException as error:
        # No final marker means incomplete collection, regardless of any result file.
        if not (output / 'bundle.json').exists():
            atomic_write(output / 'partial.json', canonical({'kind': 'partial-run', 'schema_version': 1,
                                                             'state': 'incomplete', 'error_type': type(error).__name__}) + b'\n')
        raise


def _validate_payload(path, manifest):
    members = {}
    for name, entry in manifest['files'].items():
        raw = bounded_read(path / name, RAW_LIMIT if name == 'observations.jsonl' else 1024 * 1024)
        require(len(raw) == entry['bytes'] and sha256(raw) == entry['sha256'], 'bundle member integrity failure: ' + name)
        members[name] = raw
    plan = Plan.parse(loads(members['plan.json']))
    require(all(manifest[k] == plan.data[k] for k in IDENTITY.split()), 'bundle/plan identity')
    require(loads(members['profile.json']) == plan.data['profile'], 'profile snapshot mismatch')
    require(loads(members['builds.json']) == plan.data['builds'], 'build snapshot mismatch')
    native = TargetManifest.parse(loads(members['target-manifest.json'])).data
    require(native == loads(members['observations.jsonl'].split(b'\n', 1)[0]), 'native manifest snapshot mismatch')
    status = RunStatus.parse(loads(members['status.json'])).data
    result = EvaluatedResult.parse(loads(members['result.json']))
    replay = ReplayInput.parse(loads(members['replay.json'])).data
    require(replay['original_plan'] == plan.data and replay['original_event_sha256'] == sha256(members['observations.jsonl'])
            and replay['selected_builds'] == plan.data['builds'], 'replay snapshot mismatch')
    evaluated = evaluate_persistent(plan, members['observations.jsonl'], status)
    require(evaluated.data == result.data, 'canonical evaluation mismatch')
    return Bundle(path, BundleManifest.parse(manifest), plan, result, members['observations.jsonl'], status)


def inspect_bundle(path):
    path = Path(path)
    require(not (path / 'partial.json').exists(), 'partial bundle is not finalized')
    manifest = BundleManifest.parse(loads(bounded_read(path / 'bundle.json'))).data
    require({p.name for p in path.iterdir()} == FILES | {'bundle.json'}, 'unknown or missing bundle member')
    return _validate_payload(path, manifest)


def guard_derived_output(destination, sources):
    """Reports may live beside evidence, never overwrite its inputs or records."""
    destination = Path(destination).resolve()
    for source in sources:
        source = Path(source).resolve()
        if (source / 'bundle.json').exists():
            require(destination != source and source not in destination.parents, 'derived output must be outside the immutable bundle')
        if (source / 'request.json').exists():
            protected = {source / n for n in ('request.json', 'replay.json', 'state.json', 'result.json')}
            for case in (source / 'cases').iterdir():
                if not case.is_dir(): continue
                protected.update(case / n for n in ('plan.json', 'ack.json', 'status.json', 'events.jsonl', 'partial-events.jsonl', 'stderr.txt', 'result.json'))
                bundle = case / 'bundle'
                require(destination != bundle and bundle not in destination.parents, 'derived output must be outside immutable case bundles')
            require(destination not in protected and source / 'history' not in destination.parents, 'derived output cannot overwrite execution evidence or history')
