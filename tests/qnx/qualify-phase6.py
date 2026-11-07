#!/usr/bin/env python3
"""Real same-build and explicitly selected changed-build replay; no retries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from resmgrcheck.artifacts import create_bundle, inspect_bundle
from resmgrcheck.artifacts import evaluator_identity
from resmgrcheck.contracts import canonical, load
from resmgrcheck.exports import junit

parser = argparse.ArgumentParser()
parser.add_argument('--prefix', required=True)
parser.add_argument('--fixed-source', required=True)
args = parser.parse_args()
from resmgrcheck.contracts import text
text(args.prefix)
fixed = Path(args.fixed_source).resolve()
record = load(fixed / 'build/qnx-x86_64/build-info.json')
assert not record['dirty'], 'qualification candidate must have a committed source revision'
out = Path('.local/evidence') / ('phase6-' + args.prefix)
out.mkdir(exist_ok=False)
commands = []
def call(argv, expected=0):
    value = subprocess.run(list(map(str, argv)), capture_output=True, timeout=50)
    commands.append({'argv': list(map(str, argv)), 'exit': value.returncode,
                     'stdout': value.stdout.decode(errors='replace'), 'stderr': value.stderr.decode(errors='replace')})
    assert value.returncode == expected, commands[-1]
    return value.stdout

def cli(*argv, expected=0):
    return call([sys.executable, '-m', 'resmgrcheck', *argv], expected)

source = Path('docs/evidence/phase5-clean-lifecycle')
remote = '/data/resmgrcheck/' + args.prefix + '-fixed'
originals = []
replays = []
try:
    call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'mkdir ' + remote])
    binaries = [fixed / 'build/qnx-x86_64' / n for n in ('runner', 'worker', 'sensor-v1-fixture', 'job-v1-fixture')]
    call(['scp', '-F', '.local/ssh_config', *binaries, 'resmgrcheck-qnx:' + remote + '/'])
    call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'chmod 755 ' + remote + '/*'])
    (out / 'candidate-build-record.json').write_bytes(canonical(record) + b'\n')
    (out / 'candidate-source.patch').write_bytes(call(['git', '-C', fixed, 'show', '--format=fuller', '--no-ext-diff', 'HEAD', '--', 'native/fixtures/sensor.c', 'native/fixtures/job.c']))
    for service in ('sensor', 'job'):
        tag = service + '-timeout-ignore-unblock'
        original = create_bundle(out / (service + '-original'), (source / (tag + '-plan.json')).read_bytes(),
                                 (source / (tag + '-events.jsonl')).read_bytes(), (source / (tag + '-status.json')).read_bytes())
        assert original.result.data['verdict'] == 'FAIL'
        originals.append(original)
        same_manifest = out / (service + '-same-manifest.json')
        fixed_manifest = out / (service + '-fixed-manifest.json')
        cli('candidate', original.path / 'plan.json', '--directory', '/data/resmgrcheck/p5life-clean1', '--output', same_manifest)
        cli('candidate', original.path / 'plan.json', '--directory', remote, '--build-record', fixed / 'build/qnx-x86_64/build-info.json', '--output', fixed_manifest)
        for mode, selected, expected, label, number in [('same', same_manifest, 1, 'still-failing', 2), ('fixed', fixed_manifest, 0, 'fixed', 3)]:
            run_id = args.prefix + '-' + service + '-' + mode
            cli('replay', original.path, '--candidate-manifest', selected, '--attempts', out / 'attempts', '--run-id', run_id, expected=expected)
            attempt = out / 'attempts' / original.manifest.data['bundle_id'] / ('attempt' + str(number))
            bundle = inspect_bundle(attempt / 'bundle')
            comparison = load(attempt / 'comparison.json')
            attempt_record = load(attempt / 'attempt.json')
            assert attempt_record['state'] == 'collected' and attempt_record['attempt_count'] == number
            assert comparison['label'] == label and comparison['same_contract']
            assert bundle.plan.data['profile'] == original.plan.data['profile']
            assert bundle.plan.data['fixture_mode'] == original.plan.data['fixture_mode'] == 'ignore-unblock'
            assert (bundle.plan.data['builds']['binaries']['fixture'] != original.plan.data['builds']['binaries']['fixture']) == (mode == 'fixed')
            verified = load(attempt / 'verified.json')
            assert verified['architecture'] == 'x86_64'
            replays.append({'service': service, 'selection': mode, 'attempt': number, 'run_id': run_id,
                            'verdict': bundle.result.data['verdict'], 'label': label, 'execution_exit': expected,
                            'bundle_id': bundle.manifest.data['bundle_id'], 'candidate_build_id': comparison['candidate_build_id'],
                            'original_builds': original.plan.data['builds'], 'selected_builds': bundle.plan.data['builds']})
        # The selected manifest is internally consistent, but its fixture bytes
        # deliberately mismatch the target. The actual SFTP readback must prevent launch.
        from resmgrcheck.replay import candidate_manifest
        import copy
        wrong = copy.deepcopy(load(fixed_manifest)['builds']); wrong['binaries']['fixture'] = '0' * 64
        bad = candidate_manifest(wrong, original.plan.data['profile']['adapter'], remote).data
        bad_path = out / (service + '-wrong-hash-manifest.json'); bad_path.write_bytes(canonical(bad) + b'\n')
        cli('replay', original.path, '--candidate-manifest', bad_path, '--attempts', out / 'attempts', '--run-id', args.prefix + '-' + service + '-bad-hash', expected=2)
        attempt = out / 'attempts' / original.manifest.data['bundle_id'] / 'attempt4'
        assert load(attempt / 'attempt.json')['launch_requested'] is False
        assert load(attempt / 'attempt.json')['state'] == 'incomplete'
        hashes = load(attempt / 'hash-checks.json')
        assert hashes[-1]['role'] == 'fixture' and hashes[-1]['observed'] != hashes[-1]['expected']
        call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'test ! -e /data/resmgrcheck/runs/' + args.prefix + '-' + service + '-bad-hash'])
    extras = []
    for tag in ('sensor-unsupported-capability-corrected', 'job-departure-ignore-unblock', 'job-repeat-retain-third'):
        extras.append(create_bundle(out / tag, (source / (tag + '-plan.json')).read_bytes(),
                                    (source / (tag + '-events.jsonl')).read_bytes(), (source / (tag + '-status.json')).read_bytes()))
    bundles = originals + extras + [inspect_bundle(p / 'bundle') for p in (out / 'attempts').glob('*/attempt[23]')]
    before = {str(b.path): {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in b.path.iterdir()} for b in bundles}
    (out / 'mixed.xml').write_bytes(junit(bundles))
    root = ET.fromstring((out / 'mixed.xml').read_bytes())
    assert all(int(root.get(k)) > 0 for k in ('failures', 'errors', 'skipped'))
    for b in bundles:
        cli('inspect', b.path)
        assert before[str(b.path)] == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in b.path.iterdir()}
    (out / 'post-inventory.txt').write_bytes(call(['ssh', '-F', '.local/ssh_config', 'resmgrcheck-qnx', 'pidin ar']))
    for line in (out / 'post-inventory.txt').read_text().splitlines():
        tokens = line.split()
        if len(tokens) > 1: assert Path(tokens[1]).name not in {'runner', 'worker', 'sensor-v1-fixture', 'job-v1-fixture'}
    (out / 'index.json').write_bytes(canonical({'kind': 'phase6-native-replay-gate', 'schema_version': 1,
                                              'host_evaluator': evaluator_identity(),
                                              'candidate_source': record, 'replays': replays,
                                              'junit': {k: int(root.get(k)) for k in ('tests', 'failures', 'errors', 'skipped')},
                                              'hash_mismatch_rejections': 2, 'raw_unchanged': True}) + b'\n')
finally:
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    (out / 'partial-index.json').write_bytes(canonical(replays) + b'\n')
print('Native Phase6 observations saved in', out)
