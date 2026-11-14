"""Bounded exhaustive cycle-count reduction; uncertainty stops all further launches."""
import copy
from pathlib import Path
from .artifacts import atomic_write, inspect_bundle, guard_derived_output
from .contracts import canonical, digest, integer, Profile, require
from .deployment import Deployment
from .workflow import execute, inspect_execution, make_request


def failure_signature(result):
    return sorted({a.get('reason', a['id']) for entry in [result] + result.get('cycles', [])
                   for a in entry['assertions'] if a['verdict'] == 'FAIL'})


def admissible(bundle):
    result = bundle.result.data
    return (bundle.status['cleanup_ok'] and not bundle.status['unresolved']
            and all(a['verdict'] != 'ERROR' for entry in [result] + result.get('cycles', [])
                    for a in entry['assertions'])
            and result['verdict'] in {'PASS', 'FAIL'}
            and any(a['id'] == 'evidence_completeness' and a['verdict'] == 'PASS'
                    for a in result['assertions']))


def reduce_cycles(source, target, output, max_attempts=20, progress=print):
    integer(max_attempts, 1, 20)
    request, summary, _ = inspect_execution(source)
    require(len(request.data['cases']) == 1 and request.data['cases'][0]['case_id'] == 'repeat',
            'reduction requires one repeat case')
    original = inspect_bundle(Path(source) / 'cases/repeat/bundle')
    require(original.plan.profile.data['service']['mode'] == 'managed-fixture', 'reduction requires a managed owned service')
    require(request.data['target_identity'] == target.public(), 'reduction target/recipe differs')
    require(summary['host_error'] is None and admissible(original), 'original evidence or cleanup is uncertain')
    signature = failure_signature(original.result.data)
    require(original.result.data['verdict'] == 'FAIL' and signature, 'reduction requires an established service failure')
    profile = original.plan.profile.data
    upper = profile['suite']['cycles']
    path = Path(output); guard_derived_output(path, [source])
    require(path.resolve() != Path(source).resolve() and Path(source).resolve() not in path.resolve().parents
            and path.resolve() not in Path(source).resolve().parents,
            'reduction output must be outside the original execution')
    path.parent.mkdir(parents=True, exist_ok=True); path.mkdir()
    result = {'kind': 'cycle-reduction', 'schema_version': 1, 'state': 'searching',
              'original_request_sha256': digest(request.data), 'original_bundle_id': original.manifest.data['bundle_id'],
              'original_cycles': upper, 'failure_signature': signature, 'max_attempts': max_attempts,
              'changed_fields': ['profile.suite.cycles'], 'smallest_reproduced_cycles': None,
              'minimal_within_cycle_count_domain': False, 'attempts': [],
              'scope': 'Ascending exhaustive cycle counts on new managed instances. One recorded attempt per count; '
                       'not arbitrary sequence minimization, exhaustive scheduling, or unchanged-contract source-fix replay.'}
    def save(): atomic_write(path / 'reduction.json', canonical(result) + b'\n')
    save()
    try:
        deployment = Deployment.parse(request.data['deployment'])
        for count in range(1, min(upper, max_attempts) + 1):
            candidate = copy.deepcopy(profile); candidate['suite']['cycles'] = count
            candidate = Profile.parse(candidate)
            attempt = make_request(target, candidate, 'profile', request.data['mode'], deployment)
            row = {'cycles': count, 'run_id': attempt.data['run_id'], 'state': 'launch_intent',
                   'profile_sha256': attempt.data['cases'][0]['profile_sha256'], 'location': 'attempt-' + str(count)}
            result['attempts'].append(row); save()
            progress('reduce cycles=' + str(count) + ' run=' + row['run_id'])
            execute(target, attempt, path / row['location'], progress)
            actual_request, actual_summary, _ = inspect_execution(path / row['location'])
            bundle = inspect_bundle(path / row['location'] / 'cases/repeat/bundle')
            require(actual_request.data == attempt.data, 'reduction attempt identity differs')
            row.update(state='collected', bundle_id=bundle.manifest.data['bundle_id'],
                       verdict=bundle.result.data['verdict'], failure_signature=failure_signature(bundle.result.data),
                       cleanup_ok=bundle.status['cleanup_ok'])
            if actual_summary['host_error'] or not admissible(bundle):
                result['state'] = 'blocked_uncertain_attempt'; save(); return result
            if row['verdict'] == 'FAIL':
                if row['failure_signature'] == signature:
                    result.update(state='reproduced', smallest_reproduced_cycles=count,
                                  minimal_within_cycle_count_domain=True)
                else:
                    result['state'] = 'blocked_different_failure'
                save(); return result
            save()
        result['state'] = 'budget_exhausted' if max_attempts < upper else 'not_reproduced'
        save(); return result
    except BaseException as error:
        result.update(state='interrupted' if isinstance(error, KeyboardInterrupt) else 'blocked_error',
                      error_type=type(error).__name__)
        save()
        raise
