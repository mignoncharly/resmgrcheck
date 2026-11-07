"""Contract tools, immutable evidence and explicit deployed-build replay."""
import argparse
from pathlib import Path
import subprocess
import sys

from .artifacts import atomic_write, bounded_read, create_bundle, inspect_bundle
from .contracts import FIXTURE_MODES, Invalid, Plan, Profile, canonical, load, require
from .evaluator import evaluate, evaluate_persistent
from .exports import compare, execution_exit, junit
from .planning import expand
from .replay import candidate_manifest, replay


def derived_output(path, data, bundles=()):
    path = Path(path)
    for bundle in bundles:
        require(bundle.path.resolve() not in path.resolve().parents, 'derived output must be outside the source bundle')
    atomic_write(path, data)


def main():
    parser = argparse.ArgumentParser(prog='python3 -m resmgrcheck')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('validate'); p.add_argument('profile')
    p = sub.add_parser('plan'); p.add_argument('profile'); p.add_argument('--run-id', required=True)
    p.add_argument('--fixture-mode', choices=sorted(FIXTURE_MODES), default='corrected'); p.add_argument('--output', required=True)
    p = sub.add_parser('evaluate'); p.add_argument('plan'); p.add_argument('events')
    p.add_argument('--output', required=True); p.add_argument('--status')
    p = sub.add_parser('bundle'); p.add_argument('plan'); p.add_argument('events')
    p.add_argument('--status', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('inspect'); p.add_argument('bundle')
    p = sub.add_parser('junit'); p.add_argument('bundles', nargs='+'); p.add_argument('--output', required=True)
    p = sub.add_parser('compare'); p.add_argument('original'); p.add_argument('candidate'); p.add_argument('--output')
    p = sub.add_parser('candidate'); p.add_argument('plan'); p.add_argument('--directory', required=True)
    p.add_argument('--build-record'); p.add_argument('--output', required=True)
    p = sub.add_parser('replay'); p.add_argument('bundle'); p.add_argument('--candidate-manifest', required=True)
    p.add_argument('--attempts', required=True); p.add_argument('--run-id', required=True)
    p.add_argument('--ssh-config', default='.local/ssh_config')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            Profile.parse(load(args.profile)); print('profile valid'); return 0
        if args.command == 'inspect':
            bundle = inspect_bundle(args.bundle)
            print(bundle.result.data['verdict'] + ': ' + ', '.join(bundle.result.data['reasons']))
            print('bundle ' + bundle.manifest.data['bundle_id'])
            return 0  # Offline processing success does not change the test verdict.
        if args.command == 'bundle':
            bundle = create_bundle(args.output, bounded_read(args.plan), bounded_read(args.events, 32 * 1024 * 1024), bounded_read(args.status))
            print('bundle ' + bundle.manifest.data['bundle_id'] + ': ' + bundle.result.data['verdict'])
            return 0
        if args.command == 'junit':
            bundles = [inspect_bundle(path) for path in args.bundles]
            derived_output(args.output, junit(bundles), bundles)
            return 0
        if args.command == 'compare':
            original, candidate = inspect_bundle(args.original), inspect_bundle(args.candidate)
            value = compare(original, candidate)
            if args.output:
                derived_output(args.output, canonical(value) + b'\n', (original, candidate))
            else:
                print(canonical(value).decode('ascii'))
            return 0
        if args.command == 'replay':
            path, bundle, comparison, code = replay(args.bundle, args.candidate_manifest, args.attempts, args.run_id, args.ssh_config)
            print(str(path) + ': ' + bundle.result.data['verdict'] + ' / ' + comparison['label'])
            return code
        if args.command == 'candidate':
            plan = Plan.parse(load(args.plan))
            import copy
            build = copy.deepcopy(plan.data['builds'])
            if args.build_record:
                native = load(args.build_record)
                require(native['kind'] == 'native-build-record' and native['schema_version'] == 1, 'build record version')
                for key in ('source_revision', 'dirty', 'source_tree_sha256', 'compiler_variant'):
                    build[key] = native[key]
                registration = plan.profile.registration
                build['binaries'] = {k: native['binaries'][name] for k, name in {
                    'runner': 'runner', 'worker': 'worker', 'adapter': 'worker', 'fixture': registration.fixture}.items()}
            value = candidate_manifest(build, plan.data['profile']['adapter'], args.directory).data
            require(not Path(args.output).exists(), 'candidate output already exists')
            derived_output(args.output, canonical(value) + b'\n')
            return 0
        if args.command == 'plan':
            value = expand(Profile.parse(load(args.profile)), args.run_id, args.fixture_mode).data
            code = 0
        else:
            raw = bounded_read(args.events, 32 * 1024 * 1024)
            plan = Plan.parse(load(args.plan))
            result = evaluate_persistent(plan, raw, load(args.status)) if args.status else evaluate(plan, raw)
            value = result.data
            code = execution_exit([result])
        require(not Path(args.output).exists(), 'output already exists')
        derived_output(args.output, canonical(value) + b'\n')
        if args.command == 'evaluate':
            print(value['verdict'] + ': ' + ', '.join(value['reasons']))
        return code
    except KeyboardInterrupt:
        print('Interrupted; preserve the attempt and collect its original run ID.', file=sys.stderr)
        return 130
    except (Invalid, OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
