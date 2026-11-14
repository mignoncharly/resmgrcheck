"""Repository CLI for the owned QNX lab and immutable offline evidence."""
import argparse
from pathlib import Path
import subprocess
import sys

from .artifacts import atomic_write, bounded_read, create_bundle, guard_derived_output, inspect_bundle
from .contracts import FIXTURE_MODES, Invalid, Plan, Profile, canonical, load, require
from .evaluator import evaluate, evaluate_persistent
from .exports import compare, execution_exit, junit, junit_runs
from .planning import expand
from .replay import candidate_manifest, replay


def derived_output(path, data, bundles=()):
    path = Path(path)
    for bundle in bundles:
        require(bundle.path.resolve() not in path.resolve().parents, 'derived output must be outside the source bundle')
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, data)


def parser():
    root = argparse.ArgumentParser(prog='python3 -m resmgrcheck', description='Check QNX resource-manager lifecycle contracts; preserve exact evidence and run IDs.')
    sub = root.add_subparsers(dest='command', required=True)
    def command(name, help_text, target=False):
        p = sub.add_parser(name, help=help_text)
        p.add_argument('--verbose', action='store_true', help='show detailed diagnostics')
        p.add_argument('--debug', action='store_true', help='show an exception traceback')
        if target:
            p.add_argument('--target', required=True, help='local configured target name')
            p.add_argument('--config', default='config/target.local.json', help='local target configuration (never authentication material)')
        return p
    p = command('doctor', 'observe host, SDK, SSH, transfer and target readiness', True)
    p.add_argument('--profile', help='check this profile against actual compiled adapter capabilities'); p.add_argument('--out', help='save readiness JSON')
    p = command('validate', 'strictly validate a profile'); p.add_argument('profile')
    p = command('deploy', 'stage, read back and publish an immutable native build', True); p.add_argument('--build', required=True)
    p = command('run', 'execute a required suite once; retain evidence and recovery identity', True)
    p.add_argument('--profile', required=True); p.add_argument('--suite', choices=('lifecycle', 'profile', 'health'), default='lifecycle')
    p.add_argument('--fixture-mode', choices=('fixed', *sorted(FIXTURE_MODES)), default='fixed')
    p.add_argument('--out', required=True); p.add_argument('--run-id', help='optional strict ID; otherwise a new ID is reserved')
    p.add_argument('--candidate-manifest', help='explicit existing deployment instead of the selected deployment')
    for name in ('status', 'collect'):
        p = command(name, 'observe an existing run by ID' if name == 'status' else 'collect existing evidence without launching anything', True)
        p.add_argument('--run-id', required=True)
        if name == 'collect': p.add_argument('--out', required=True); p.add_argument('--wait', action='store_true', help='wait within the original execution bound')
        else: p.add_argument('--json', action='store_true')
    p = command('verify', 'qualify expected outcomes; planted service defects remain FAIL', True)
    p.add_argument('--suite', choices=('release',), required=True); p.add_argument('--out')
    p = command('report', 'render an offline report from saved outcomes'); p.add_argument('source'); p.add_argument('--out', required=True)
    p = command('return-check', 'compare an explicit return-code predicate with canonical native obligations')
    p.add_argument('bundle'); p.add_argument('--out', required=True)
    p = command('reduce', 'find the smallest reproduced failing cycle count within a bounded search', True)
    p.add_argument('execution'); p.add_argument('--out', required=True)
    p.add_argument('--max-attempts', type=int, default=20)
    p = command('plan', 'expand one validated native case'); p.add_argument('profile'); p.add_argument('--run-id', required=True)
    p.add_argument('--fixture-mode', choices=sorted(FIXTURE_MODES), default='corrected'); p.add_argument('--output', required=True)
    p = command('evaluate', 'evaluate collected native bytes'); p.add_argument('plan'); p.add_argument('events'); p.add_argument('--output', required=True); p.add_argument('--status')
    p = command('bundle', 'seal collected persistent evidence'); p.add_argument('plan'); p.add_argument('events'); p.add_argument('--status', required=True); p.add_argument('--output', required=True)
    p = command('inspect', 'inspect valid evidence without changing its verdict'); p.add_argument('bundle')
    p = command('junit', 'export saved outcomes as JUnit XML'); p.add_argument('bundles', nargs='+'); p.add_argument('--output', required=True)
    p = command('compare', 'compare contracts/builds and complete saved outcomes'); p.add_argument('original'); p.add_argument('candidate')
    output = p.add_mutually_exclusive_group(); output.add_argument('--output', help='JSON file'); output.add_argument('--out', help='new comparison directory')
    p = command('candidate', 'describe a legacy explicit deployment'); p.add_argument('plan'); p.add_argument('--directory', required=True)
    p.add_argument('--build-record'); p.add_argument('--output', required=True)
    p = command('replay', 'replay one saved contract; changed builds need explicit selection')
    p.add_argument('bundle'); p.add_argument('--target'); p.add_argument('--config', default='config/target.local.json')
    p.add_argument('--candidate-manifest', help='explicit deployed build; original deployment is used otherwise')
    p.add_argument('--fixture-mode', choices=('fixed', *sorted(FIXTURE_MODES)), help='disclosed fixture-control contrast, not a source fix')
    p.add_argument('--out'); p.add_argument('--run-id')
    p.add_argument('--attempts', help='legacy Phase6 attempt history'); p.add_argument('--ssh-config', default='.local/ssh_config', help=argparse.SUPPRESS)
    return root


def main():
    args = parser().parse_args()
    try:
        if args.command in {'doctor', 'deploy', 'run', 'status', 'collect', 'verify', 'reduce'} or args.command == 'replay' and args.target:
            from .transport import Target
            target = Target.read(args.target, args.config)
        if args.command == 'return-check':
            from .return_check import return_check
            value = return_check(args.bundle, args.out)
            print('Return-code predicate: ' + value['limited_predicate'] + '; canonical verdict: ' + value['canonical_verdict'])
            return 0
        if args.command == 'reduce':
            from .reduction import reduce_cycles
            value = reduce_cycles(args.execution, target, args.out, args.max_attempts)
            print('Reduction: ' + value['state'] + '; result ' + str(Path(args.out) / 'reduction.json'))
            return 0 if value['state'] == 'reproduced' else 3 if value['state'] in {'budget_exhausted', 'not_reproduced'} else 2
        if args.command == 'doctor':
            from .doctor import doctor
            value, _ = doctor(target, Profile.parse(load(args.profile)) if args.profile else None)
            if args.out: derived_output(args.out, canonical(value) + b'\n')
            for check in value['checks']:
                detail = check['detail']
                if not args.verbose and type(detail) is dict and 'compiled_adapter_capabilities' in detail:
                    detail = str(len(detail['compiled_adapter_capabilities'])) + ' actual compiled adapter declarations; missing required: ' + (', '.join(detail['missing_required']) or 'none')
                detail = str(detail) if args.verbose else str(detail)[:180]
                print(check['id'] + ': ' + check['state'] + ' - ' + detail)
            return value['execution_exit']
        if args.command == 'validate':
            Profile.parse(load(args.profile)); print('profile valid'); return 0
        if args.command == 'deploy':
            from .deployment import deploy
            selected = deploy(target, args.build)
            print('deployed ' + selected.data['deployment_id'] + '; target ' + target.name)
            print('candidate manifest: ' + str(Path(args.build) / 'manifest.json'))
            return 0
        if args.command == 'run':
            from .deployment import load_deployment
            from .workflow import execute, make_request
            require(not Path(args.out).exists(), 'out: directory already exists; preserve it and choose a new output')
            profile = Profile.parse(load(args.profile))
            request = make_request(target, profile, args.suite, args.fixture_mode, load_deployment(target, args.candidate_manifest), args.run_id)
            print('run ' + request.data['run_id'] + '; target ' + target.name + '; output ' + args.out, flush=True)
            result = execute(target, request, args.out, lambda text: print(text, flush=True))
            print('result: ' + str(Path(args.out) / 'result.json'))
            return result['execution_exit']
        if args.command == 'status':
            from .workflow import status
            request, rows = status(target, args.run_id)
            if args.json: print(canonical({'run_id': args.run_id, 'cases': rows}).decode('ascii'))
            else:
                print('run ' + args.run_id + '; status is collection progress, not a service verdict')
                for row in rows: print(row['case_id'] + ': ' + row['state'])
            return 0
        if args.command == 'collect':
            from .workflow import collect
            value = collect(target, args.run_id, args.out, args.wait)
            print('collected ' + args.run_id + '; result ' + str(Path(args.out) / 'result.json'))
            return value['execution_exit']
        if args.command == 'verify':
            from .verification import verify
            from .workflow import run_id
            output = args.out or 'runs/release-' + run_id()
            value = verify(target, output, lambda text: print(text, flush=True))
            print('verification ' + ('PASS' if value['qualification_passed'] else 'INCOMPLETE OR MISMATCH') + '; individual verdicts unchanged; ' + output)
            return value['execution_exit']
        if args.command == 'report':
            from .reports import report
            report(args.source, args.out); print('report: ' + args.out); return 0
        if args.command == 'inspect':
            if (Path(args.bundle) / 'request.json').exists():
                from .workflow import inspect_execution
                _, summary, _ = inspect_execution(args.bundle)
                print('execution ' + summary['run_id'] + ': ' + summary['completion'] + '; test exit ' + str(summary['execution_exit']))
                for row in summary['cases']: print(row['case_id'] + ': ' + row['verdict'] + ' - ' + ', '.join(row['reasons']))
            else:
                bundle = inspect_bundle(args.bundle)
                print(bundle.result.data['verdict'] + ': ' + ', '.join(bundle.result.data['reasons']))
                print('bundle ' + bundle.manifest.data['bundle_id'])
            return 0
        if args.command == 'bundle':
            bundle = create_bundle(args.output, bounded_read(args.plan), bounded_read(args.events, 32 * 1024 * 1024), bounded_read(args.status))
            print('bundle ' + bundle.manifest.data['bundle_id'] + ': ' + bundle.result.data['verdict']); return 0
        if args.command == 'junit':
            guard_derived_output(args.output, args.bundles)
            runs = []; bundles = []
            for path in args.bundles:
                if (Path(path) / 'request.json').exists():
                    from .workflow import inspect_execution
                    request, summary, results = inspect_execution(path)
                    for plan, row, result in zip(request.data['cases'], summary['cases'], results):
                        runs.append((plan, result.data, row['bundle_id'], str(Path(path) / 'cases' / row['case_id'])))
                        if row['bundle_id']: bundles.append(inspect_bundle(Path(path) / 'cases' / row['case_id'] / 'bundle'))
                else:
                    b = inspect_bundle(path); bundles.append(b); runs.append((b.plan.data, b.result.data, b.manifest.data['bundle_id'], str(b.path)))
            derived_output(args.output, junit_runs(runs), bundles); return 0
        if args.command == 'compare':
            if args.output: guard_derived_output(args.output, [args.original, args.candidate])
            if args.out: guard_derived_output(args.out, [args.original, args.candidate])
            if (Path(args.original) / 'request.json').exists():
                from .workflow import compare_executions
                value = compare_executions(args.original, args.candidate); bundles = []
                for root in (args.original, args.candidate): bundles.extend(inspect_bundle(p) for p in Path(root).glob('cases/*/bundle'))
            else:
                original, candidate = inspect_bundle(args.original), inspect_bundle(args.candidate)
                value = compare(original, candidate); bundles = [original, candidate]
            if args.out:
                path = Path(args.out); path.parent.mkdir(parents=True, exist_ok=True); path.mkdir()
                derived_output(path / 'comparison.json', canonical(value) + b'\n', bundles)
            elif args.output: derived_output(args.output, canonical(value) + b'\n', bundles)
            else: print(canonical(value).decode('ascii'))
            print('comparison: ' + value['label'], file=sys.stderr)
            return 0
        if args.command == 'replay':
            if args.target:
                from .workflow import replay_execution
                require(args.out, 'replay.out: required for a configured workflow replay')
                require(not Path(args.out).exists(), 'replay.out: output directory already exists')
                value, comparison = replay_execution(args.bundle, target, args.out, args.fixture_mode, args.candidate_manifest, args.run_id, lambda text: print(text, flush=True))
                print('replay: ' + comparison['label'] + '; result ' + str(Path(args.out) / 'result.json'))
                return value['execution_exit']
            require(args.candidate_manifest and args.attempts and args.run_id, 'legacy replay requires --candidate-manifest, --attempts and --run-id; use --target for the host workflow')
            path, bundle, comparison, code = replay(args.bundle, args.candidate_manifest, args.attempts, args.run_id, args.ssh_config)
            print(str(path) + ': ' + bundle.result.data['verdict'] + ' / ' + comparison['label']); return code
        if args.command == 'candidate':
            plan = Plan.parse(load(args.plan)); import copy
            build = copy.deepcopy(plan.data['builds'])
            if args.build_record:
                native = load(args.build_record)
                require(native['kind'] == 'native-build-record' and native['schema_version'] == 1, 'build record version')
                for key in ('source_revision', 'dirty', 'source_tree_sha256', 'compiler_variant'): build[key] = native[key]
                registration = plan.profile.registration
                build['binaries'] = {k: native['binaries'][name] for k, name in {'runner': 'runner', 'worker': 'worker', 'adapter': 'worker', 'fixture': registration.fixture}.items()}
            value = candidate_manifest(build, plan.data['profile']['adapter'], args.directory).data
            require(not Path(args.output).exists(), 'candidate output already exists')
            derived_output(args.output, canonical(value) + b'\n'); return 0
        if args.command == 'plan':
            value = expand(Profile.parse(load(args.profile)), args.run_id, args.fixture_mode).data; code = 0
        else:
            raw = bounded_read(args.events, 32 * 1024 * 1024); plan = Plan.parse(load(args.plan))
            result = evaluate_persistent(plan, raw, load(args.status)) if args.status else evaluate(plan, raw)
            value = result.data; code = execution_exit([result])
        require(not Path(args.output).exists(), 'output already exists')
        derived_output(args.output, canonical(value) + b'\n')
        if args.command == 'evaluate': print(value['verdict'] + ': ' + ', '.join(value['reasons']))
        return code
    except KeyboardInterrupt:
        print('Interrupted. Preserve this output and recover its existing run ID with status/collect.', file=sys.stderr); return 130
    except (Invalid, OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
        from .transport import Unsupported
        if args.debug:
            import traceback
            traceback.print_exc()
        message = str(error) if args.verbose else str(error).splitlines()[0][:300]
        print(('UNSUPPORTED: ' if isinstance(error, Unsupported) else 'ERROR: ') + message, file=sys.stderr)
        return 3 if isinstance(error, Unsupported) else 2


if __name__ == '__main__': sys.exit(main())
