"""Persistent host requests, one-shot launches, and collection by exact run ID."""
import copy
import os
from dataclasses import dataclass
from pathlib import Path
import re
import secrets
import time

from .artifacts import atomic_write, bounded_read, create_bundle, evaluator_identity, inspect_bundle, sha256
from .contracts import (HASH, IDENTITY, EvaluatedResult, Invalid, Plan, Profile, ReplayInput,
                        RunStarted, RunStatus, canonical, digest, enum, integer, load, loads,
                        obj, require, text, version)
from .deployment import Deployment, active_path, bootstrap, engine_info, load_deployment, native_builds, verify_remote
from .evaluator import Evidence
from .exports import execution_exit
from .outcomes import infrastructure_error
from .transport import Transport, TransportError, Unsupported

FAMILIES = ('timeout', 'signal', 'departure', 'repeat', 'complete-first', 'cancel-first')


def fixture_mode(value):
    return 'corrected' if value == 'fixed' else value


def suite_profiles(profile, suite):
    if not isinstance(profile, Profile): profile = Profile.parse(profile)
    if suite == 'profile': return [profile]
    if suite == 'health':
        require(profile.data['suite']['required'] == ['external-health'], 'suite health requires an explicit external-health profile')
        return [profile]
    require(suite == 'lifecycle', 'suite: expected lifecycle, profile or health')
    profiles = []
    for family in FAMILIES:
        p = copy.deepcopy(profile.data)
        p['id'] = p['id'][:32] + '-' + family
        p['suite'] = {'required': [family], 'optional': [], 'cycles': 20 if family == 'repeat' else 1,
                      'reset': 'same-instance' if family == 'repeat' else 'new-instance'}
        if family == 'signal': p['suite']['signal_mode'] = 'non-restart-no-retry'
        p['expectations'].pop('next_health', None)
        p['expectations'].update(cancel_error='PROCESS_EXIT' if family == 'departure' else 'ETIMEDOUT' if family in {'timeout', 'repeat'} else 'EINTR', require_unblock=True)
        required = set(p['capabilities']['required']) | {'pending', 'unblock', 'state', 'release', 'health'}
        required |= {'timeout', 'repeat'} if family == 'repeat' else {'signal', 'ordering'} if family in {'complete-first', 'cancel-first'} else {family}
        p['capabilities']['required'] = sorted(required)
        p['capabilities']['optional'] = sorted(set(p['capabilities']['optional']) - required)
        if family in {'complete-first', 'cancel-first'}:
            p['expectations']['state_after'].update(profile.registration.ordering_state)
            next_result = copy.deepcopy(p['expectations']['health'])
            for key, delta in profile.registration.next_deltas: next_result[key] += delta
            p['expectations']['next_health'] = next_result
        profiles.append(Profile.parse(p))
    return profiles


def run_id(value=None):
    value = value or 'r-' + time.strftime('%Y%m%d%H%M%S', time.gmtime()) + '-' + secrets.token_hex(6)
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', value), 'run-id: expected 1..40 letters, digits, underscore or hyphen')
    return value


def make_plan(profile, identifier, deployment, mode, attempt='attempt1'):
    p = profile.data if isinstance(profile, Profile) else profile
    return Plan.parse({'kind': 'scenario-plan', 'schema_version': 1, 'run_id': identifier,
                      'case_id': p['suite']['required'][0], 'attempt_id': attempt, 'cycle': 1,
                      'service_instance_id': identifier, 'profile': p, 'profile_sha256': digest(p),
                      'suite_sha256': digest(p['suite']), 'fixture_mode': mode,
                      'builds': native_builds(deployment.data, p['adapter']['id'])})


@dataclass(frozen=True)
class Request:
    data: dict

    @classmethod
    def parse(cls, d):
        obj(d, 'kind schema_version run_id target target_identity suite mode deployment cases origin', 'execution request')
        version(d, 'execution-request'); run_id(d['run_id']); text(d['target'])
        enum(d['suite'], {'lifecycle', 'profile', 'health', 'replay'})
        deployment = Deployment.parse(d['deployment'])
        obj(d['target_identity'], 'uid processor machine release recipe_id root')
        require(d['target_identity']['processor'] == deployment.data['architecture'] and
                d['target_identity']['recipe_id'] == deployment.data['recipe_id'] and
                d['target_identity']['uid'] == deployment.data['uid'] and
                d['target_identity']['machine'] == deployment.data['machine'] and
                d['target_identity']['release'] == deployment.data['release'] and
                d['target_identity']['root'] == '/data/resmgrcheck', 'request target/deployment binding')
        require(type(d['cases']) is list and 1 <= len(d['cases']) <= 6, 'request cases')
        names = []
        for raw in d['cases']:
            p = Plan.parse(raw); names.append(p.data['case_id'])
            require(p.data['run_id'] == d['run_id'] + '-' + p.data['case_id'] and p.data['fixture_mode'] == d['mode'], 'request case identity')
            require(p.data['builds'] == native_builds(deployment.data, p.profile.data['adapter']['id']), 'request case build')
        require(len(set(names)) == len(names), 'duplicate request case')
        if d['suite'] == 'lifecycle': require(names == list(FAMILIES), 'lifecycle coverage')
        if d['suite'] == 'health': require(names == ['external-health'], 'health scope')
        if d['origin'] is not None:
            obj(d['origin'], 'request_sha256 mode_changed candidate_changed attempt source')
            text(d['origin']['request_sha256'], HASH); integer(d['origin']['attempt'], 2, 1000000)
            require(type(d['origin']['mode_changed']) is bool and type(d['origin']['candidate_changed']) is bool, 'replay change flags')
            require(type(d['origin']['source']) is str and d['origin']['source'].isascii() and '\x00' not in d['origin']['source'] and len(d['origin']['source']) <= 4096, 'replay source location must be bounded ASCII')
        return cls(copy.deepcopy(d))


def make_request(target, profile, suite, mode, deployment, identifier=None):
    identifier = run_id(identifier); mode = fixture_mode(mode)
    profiles = suite_profiles(profile, suite)
    cases = [make_plan(p, identifier + '-' + p.data['suite']['required'][0], deployment, mode).data for p in profiles]
    return Request.parse({'kind': 'execution-request', 'schema_version': 1, 'run_id': identifier,
                          'target': target.name, 'target_identity': target.public(), 'suite': suite, 'mode': mode,
                          'deployment': deployment.data, 'cases': cases, 'origin': None})


def _helper(request): return request.data['deployment']['directory'] + '/targetctl'


def remote_request(target, identifier, transport):
    run_id(identifier)
    if active_path(target).is_file():
        deployment = load_deployment(target)
        helper = deployment.data['directory'] + '/targetctl'
    else:
        # Recovery needs the target configuration and a trusted locally built
        # controller, not remembered service PIDs or manually reconstructed plans.
        helper = bootstrap(transport)
    owner = loads(transport.command(helper, 'read-session', identifier, 'owner.json'))
    obj(owner, 'kind schema_version id binding uid'); version(owner, 'owned-session')
    require(owner['id'] == identifier and owner['uid'] == target.data['uid'], 'remote session ownership binding')
    raw = transport.command(helper, 'read-session', identifier, 'request.json')
    request = Request.parse(loads(raw))
    require(digest(request.data) == owner['binding'], 'remote request hash mismatch')
    require(request.data['target'] == target.name and request.data['target_identity'] == target.public(), 'remote request target mismatch')
    return request


def initialize(path, request):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()  # Exclusive output reservation before any target mutation.
    (path / 'cases').mkdir(); (path / 'diagnostics').mkdir()
    atomic_write(path / 'request.json', canonical(request.data) + b'\n')
    atomic_write(path / 'replay.json', canonical({'kind': 'suite-replay', 'schema_version': 1,
                                                'request_sha256': digest(request.data), 'request_file': 'request.json'}) + b'\n')
    state = {'kind': 'host-run-state', 'schema_version': 1, 'run_id': request.data['run_id'],
             'request_sha256': digest(request.data), 'state': 'preflight', 'error': None,
             'cases': {p['case_id']: 'not-requested' for p in request.data['cases']}}
    atomic_write(path / 'state.json', canonical(state) + b'\n')
    return state


def _state(path, state): atomic_write(Path(path) / 'state.json', canonical(state) + b'\n')


def validate_state(state, request):
    obj(state, 'kind schema_version run_id request_sha256 state error cases', 'host state')
    version(state, 'host-run-state')
    require(state['run_id'] == request.data['run_id'] and state['request_sha256'] == digest(request.data), 'host state identity')
    enum(state['state'], {'preflight', 'running', 'collected', 'incomplete'})
    if state['error'] is not None: text(state['error'])
    require(type(state['cases']) is dict and set(state['cases']) == {p['case_id'] for p in request.data['cases']}, 'host state required cases')
    for value in state['cases'].values():
        enum(value, {'not-requested', 'withheld', 'launch-requested', 'acknowledged', 'status-observed', 'collected', 'launch-uncertain', 'running'})
    return state


def validate_summary(summary, request):
    obj(summary, 'kind schema_version run_id request_sha256 execution_exit completion cases host_error', 'execution summary')
    version(summary, 'execution-summary')
    require(summary['run_id'] == request.data['run_id'] and summary['request_sha256'] == digest(request.data), 'summary identity')
    require(type(summary['execution_exit']) is int and summary['execution_exit'] in {0, 1, 2, 3, 130}, 'summary exit')
    enum(summary['completion'], {'complete', 'incomplete'})
    if summary['host_error'] is not None: text(summary['host_error'])
    require(type(summary['cases']) is list and len(summary['cases']) == len(request.data['cases']), 'summary case coverage')
    for row in summary['cases']:
        obj(row, 'case_id run_id verdict reasons completion bundle_id', 'case summary')
        text(row['case_id']); text(row['run_id']); enum(row['verdict'], {'PASS', 'FAIL', 'ERROR', 'UNSUPPORTED', 'NOT_RUN'})
        enum(row['completion'], {'complete', 'incomplete', 'aborted'})
        require(type(row['reasons']) is list and 1 <= len(row['reasons']) <= 32, 'case reasons')
        for code in row['reasons']: text(code)
        if row['bundle_id'] is not None: text(row['bundle_id'], HASH)
    return summary


def _read_status(transport, helper, plan):
    raw = transport.command(helper, 'read-run', plan.data['run_id'], 'status.json', exits=(0, 2))
    if transport.record[-1]['exit'] == 2: return None, None
    parsed = RunStatus.parse(loads(raw)).data
    require(all(parsed[k] == plan.data[k] for k in IDENTITY.split()), 'status identity mismatch')
    require(parsed['profile_sha256'] == plan.data['profile_sha256'] and parsed['source_tree_sha256'] == plan.data['builds']['source_tree_sha256'], 'status source/profile mismatch')
    return raw, parsed


def _save_partial(path, transport, helper, plan):
    try:
        raw = transport.command(helper, 'read-run', plan.data['run_id'], 'events.jsonl', exits=(0, 2))
        if transport.record[-1]['exit'] == 0: atomic_write(path / 'partial-events.jsonl', raw)
    except (Invalid, OSError): pass


def collect_case(path, transport, request, plan, wait=False):
    path.mkdir(exist_ok=True)
    helper = _helper(request)
    end = time.monotonic() + plan.profile.timing.execution_ms / 1000 * (plan.profile.data['suite']['cycles'] + 1) + plan.profile.timing.cleanup_ms / 1000 + 10
    while True:
        raw_status, status = _read_status(transport, helper, plan)
        if status is None:
            _save_partial(path, transport, helper, plan)
            raise TransportError('launch uncertain: no bound status for ' + plan.data['run_id'] + '; use status/collect, never relaunch')
        atomic_write(path / 'status.json', raw_status)
        if status['state'] != 'running': break
        if not wait:
            _save_partial(path, transport, helper, plan)
            return None
        if time.monotonic() >= end:
            _save_partial(path, transport, helper, plan)
            raise TransportError('target completion unestablished: ' + plan.data['run_id'])
        time.sleep(.15)
    raw = transport.command(helper, 'read-run', plan.data['run_id'], status.get('event_file', 'events.jsonl'))
    atomic_write(path / 'events.jsonl', raw)
    atomic_write(path / 'stderr.txt', transport.command(helper, 'read-run', plan.data['run_id'], 'stderr.log'))
    if (path / 'bundle').exists():
        bundle = inspect_bundle(path / 'bundle')
        require(bundle.raw == raw and bundle.status == status and bundle.plan.data == plan.data, 'collected bundle differs from existing evidence')
        return bundle
    return create_bundle(path / 'bundle', canonical(plan.data) + b'\n', raw, raw_status)


def uncollected_result(plan, reason, raw=b'', error=False):
    if error: return infrastructure_error(plan, 'target_completion_unestablished', raw)
    from .assertions import explain
    value = {'kind': 'evaluated-result', 'schema_version': 1, **{k: plan.data[k] for k in IDENTITY.split()},
             'fixture_mode': plan.data['fixture_mode'], 'profile_sha256': plan.data['profile_sha256'],
             'event_sha256': sha256(raw), 'verdict': 'UNSUPPORTED' if reason=='required_capability_unavailable' else 'NOT_RUN',
             'completion': 'complete' if reason=='required_capability_unavailable' else 'aborted', 'reasons': [reason],
             'assertions': [{'id': reason, 'verdict': 'UNSUPPORTED' if reason=='required_capability_unavailable' else 'NOT_RUN', 'event_refs': []}]}
    return EvaluatedResult.parse(explain(value, plan, raw))


def finalize(path, request, state):
    rows = []
    for raw_plan in request.data['cases']:
        plan = Plan.parse(raw_plan); name = plan.data['case_id']; location = path / 'cases' / name
        if (location / 'bundle/bundle.json').exists():
            bundle = inspect_bundle(location / 'bundle'); result = bundle.result
            require(bundle.plan.data == plan.data, 'collected case plan mismatch')
            identity = bundle.manifest.data['bundle_id']
        else:
            partial = (location / 'partial-events.jsonl').read_bytes() if (location / 'partial-events.jsonl').exists() else b''
            uncertain = state['cases'][name] not in {'not-requested', 'withheld'}
            result = uncollected_result(plan, 'required_capability_unavailable' if state['error']=='Unsupported' else 'host_sequence_interrupted' if state['error'] else 'prior_cleanup_failed', partial, uncertain)
            identity = None
        location.mkdir(exist_ok=True)
        atomic_write(location / 'result.json', canonical(result.data) + b'\n')
        rows.append({'case_id': name, 'run_id': plan.data['run_id'], 'verdict': result.data['verdict'],
                     'reasons': result.data['reasons'], 'completion': result.data['completion'], 'bundle_id': identity})
    results = [EvaluatedResult.parse(load(path / 'cases' / row['case_id'] / 'result.json')) for row in rows]
    code = execution_exit(results, interrupted=state['error'] == 'KeyboardInterrupt')
    if state['error']=='Unsupported': code = 3
    elif state['error'] and code != 130: code = 2
    summary = {'kind': 'execution-summary', 'schema_version': 1, 'run_id': request.data['run_id'],
               'request_sha256': digest(request.data), 'execution_exit': code,
               'completion': 'complete' if all(r['completion'] == 'complete' for r in rows) and not state['error'] else 'incomplete',
               'cases': rows, 'host_error': state['error']}
    atomic_write(path / 'result.json', canonical(summary) + b'\n')
    state['state'] = 'collected' if not state['error'] else 'incomplete'; _state(path, state)
    return summary


def execute(target, request, output, progress=print):
    path = Path(output); state = initialize(path, request); transport = Transport(target)
    helper = _helper(request)
    current = None
    try:
        verify_remote(transport, Deployment.parse(request.data['deployment']), evidence_path=path / 'diagnostics/deployment-hashes.json')
        if any(p['case_id']=='external-health' for p in request.data['cases']):
            raw = transport.command(request.data['deployment']['directory'] + '/worker', '--describe', exits=(0, 2))
            if raw: atomic_write(path / 'diagnostics/engine-info.json', raw)
            capabilities = engine_info(raw) if transport.record[-1]['exit']==0 else {}
            if any('external-health' not in capabilities.get(p['profile']['adapter']['id'], []) for p in request.data['cases']):
                raise Unsupported('required_capability_unavailable: external health cannot be verified with the selected engine')
        transport.command(helper, 'create-session', request.data['run_id'], digest(request.data))
        transport.command(helper, 'put-session', request.data['run_id'], 'request.json', data=canonical(request.data) + b'\n')
        state['state'] = 'running'; _state(path, state)
        predecessor = None
        for raw_plan in request.data['cases']:
            plan = Plan.parse(raw_plan); name = plan.data['case_id']; current = plan
            progress(name + ': starting; baseline pending')
            location = path / 'cases' / name; location.mkdir()
            atomic_write(location / 'plan.json', canonical(plan.data) + b'\n')
            transport.command(helper, 'put-session', request.data['run_id'], name + '-plan.json', data=canonical(plan.data) + b'\n')
            staged = transport.command(helper, 'read-session', request.data['run_id'], name + '-plan.json')
            require(staged == canonical(plan.data) + b'\n', 'remote plan readback mismatch')
            receipt = {'kind': 'launch-receipt', 'schema_version': 1, 'run_id': plan.data['run_id'], 'plan_sha256': digest(plan.data), 'requested': True}
            transport.command(helper, 'put-session', request.data['run_id'], name + '-launch.json', data=canonical(receipt) + b'\n')
            state['cases'][name] = 'launch-requested'; _state(path, state)
            argv = [request.data['deployment']['directory'] + '/runner',
                    target.data['root'] + '/sessions/' + request.data['run_id'] + '/' + name + '-plan.json', '--persist']
            if predecessor: argv.append('--after=' + predecessor)
            started = time.monotonic()
            ack = transport.command(*argv)
            acknowledgement = RunStarted.parse(loads(ack)).data
            require(all(acknowledgement[k] == plan.data[k] for k in IDENTITY.split()), 'launch acknowledgement identity mismatch')
            atomic_write(location / 'ack.json', ack)
            transport.command(helper, 'put-session', request.data['run_id'], name + '-ack.json', data=ack)
            state['cases'][name] = 'acknowledged'; _state(path, state)
            bundle = collect_case(location, transport, request, plan, wait=True)
            state['cases'][name] = 'collected'; _state(path, state)
            baseline = next((a['verdict'] for a in bundle.result.data['assertions'] if a['id'] == 'baseline_validity'), 'not established')
            progress(name + ': baseline ' + baseline + '; ' + bundle.result.data['verdict'] + ' (' + str(round(time.monotonic() - started, 1)) + 's)')
            predecessor = plan.data['run_id']
        state['error'] = None
    except BaseException as error:
        state['error'] = type(error).__name__
        if current:
            _save_partial(path / 'cases' / current.data['case_id'], transport, helper, current)
        raise
    finally:
        transport.save(path / 'diagnostics/commands.json')
        finalize(path, request, state)
    return load(path / 'result.json')


def status(target, identifier):
    transport = Transport(target); request = remote_request(target, identifier, transport)
    rows = []
    for raw_plan in request.data['cases']:
        plan = Plan.parse(raw_plan)
        _, observed = _read_status(transport, _helper(request), plan)
        if observed is None:
            receipt = transport.command(_helper(request), 'read-session', identifier, plan.data['case_id'] + '-launch.json', exits=(0, 2))
            state = 'launch-uncertain' if receipt else 'not-requested'
        else: state = observed['state']
        rows.append({'case_id': plan.data['case_id'], 'run_id': plan.data['run_id'], 'state': state, 'status': observed})
    return request, rows


def collect(target, identifier, output, wait=False):
    transport = Transport(target); request = remote_request(target, identifier, transport)
    path = Path(output)
    if path.exists():
        require((path / 'request.json').is_file() and load(path / 'request.json') == request.data, 'occupied output directory is not this execution')
        state = validate_state(load(path / 'state.json'), request)
        history = path / 'history'; history.mkdir(exist_ok=True)
        number = len(list(history.iterdir())) + 1
        snapshot = history / ('collection-' + str(number).zfill(6)); snapshot.mkdir()
        for name in ('state.json', 'result.json'):
            if (path / name).is_file(): atomic_write(snapshot / name, bounded_read(path / name))
        for p in request.data['cases']:
            before = path / 'cases' / p['case_id']
            if before.is_dir():
                saved = snapshot / p['case_id']; saved.mkdir()
                for name in ('result.json', 'status.json', 'partial-events.jsonl'):
                    if (before / name).is_file(): atomic_write(saved / name, bounded_read(before / name, 32 * 1024 * 1024))
    else: state = initialize(path, request)
    state['error'] = None
    try:
        for raw_plan in request.data['cases']:
            plan = Plan.parse(raw_plan); name = plan.data['case_id']; location = path / 'cases' / name
            _, observed = _read_status(transport, _helper(request), plan)
            if observed is None:
                receipt = transport.command(_helper(request), 'read-session', identifier, name + '-launch.json', exits=(0, 2))
                state['cases'][name] = 'launch-uncertain' if receipt else 'withheld'
                if receipt: state['error'] = 'target_completion_unestablished'
                continue
            state['cases'][name] = 'status-observed'
            bundle = collect_case(location, transport, request, plan, wait=wait)
            state['cases'][name] = 'collected' if bundle else 'running'
            if not bundle: state['error'] = 'target_completion_unestablished'
    except BaseException as error:
        state['error'] = type(error).__name__
        raise
    finally:
        transport.save(path / 'diagnostics/collection-commands.json')
        summary = finalize(path, request, state)
    return summary


def inspect_execution(path):
    path = Path(path)
    request = Request.parse(load(path / 'request.json'))
    replay = load(path / 'replay.json'); obj(replay, 'kind schema_version request_sha256 request_file')
    version(replay, 'suite-replay'); require(replay['request_file'] == 'request.json' and replay['request_sha256'] == digest(request.data), 'replay request binding')
    summary = validate_summary(load(path / 'result.json'), request)
    require([r['case_id'] for r in summary['cases']] == [p['case_id'] for p in request.data['cases']], 'summary required coverage')
    results = []
    for raw_plan, row in zip(request.data['cases'], summary['cases']):
        name = raw_plan['case_id']; result = EvaluatedResult.parse(load(path / 'cases' / name / 'result.json'))
        if row['bundle_id']:
            bundle = inspect_bundle(path / 'cases' / name / 'bundle')
            require(bundle.manifest.data['bundle_id'] == row['bundle_id'] and bundle.result.data == result.data and bundle.plan.data == raw_plan, 'summary bundle binding')
        else:
            require(result.data['verdict'] in {'ERROR', 'NOT_RUN', 'UNSUPPORTED'}, 'uncollected case cannot pass')
        require(all(row[k] == result.data[k] for k in ('case_id', 'run_id', 'verdict', 'reasons', 'completion')), 'case outcome binding')
        results.append(result)
    expected_exit = execution_exit(results, interrupted=summary['execution_exit'] == 130)
    if summary['host_error']=='Unsupported': expected_exit = 3
    elif summary['host_error'] and expected_exit != 130: expected_exit = 2
    require(summary['execution_exit'] == expected_exit, 'summary exit precedence')
    expected_completion = 'complete' if all(r.data['completion']=='complete' for r in results) and not summary['host_error'] else 'incomplete'
    require(summary['completion']==expected_completion, 'summary completion binding')
    return request, summary, results


def replay_execution(source, target, output, mode=None, candidate_path=None, identifier=None, progress=print):
    source = Path(source)
    if source.is_file():
        pointer = load(source)
        require(pointer.get('kind') == 'suite-replay', 'replay: expected a workflow replay.json or execution directory')
        source = source.parent
    original, _, _ = inspect_execution(source)
    if any(p['profile']['service']['mode'] != 'managed-fixture' for p in original.data['cases']):
        raise Unsupported('external replay cannot verify the running service build; use the read-only health diagnostic')
    selected = load_deployment(target, candidate_path) if candidate_path else Deployment.parse(original.data['deployment'])
    identifier = run_id(identifier)
    history = Path('.local/state/replays') / digest(original.data)
    history.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in history.iterdir()]
    require(all(re.fullmatch(r'attempt[1-9][0-9]*\.json', name) for name in names), 'replay history contains unknown data')
    previous = []
    for name in names:
        saved = load(history / name)
        obj(saved, 'kind schema_version original_request_sha256 attempt run_id candidate_deployment output command_exit', 'replay receipt')
        version(saved, 'workflow-replay-attempt'); integer(saved['attempt'], 2, 1000000); run_id(saved['run_id']); text(saved['candidate_deployment'], HASH)
        require(saved['command_exit'] is None or type(saved['command_exit']) is int and saved['command_exit'] in {0,1,2,3,130}, 'replay command exit')
        require(type(saved['output']) is str and len(saved['output']) <= 4096, 'replay output path')
        require(saved['original_request_sha256'] == digest(original.data) and saved['attempt'] == int(name[7:-5]), 'replay history identity mismatch')
        previous.append(saved['attempt'])
    attempt = max([int(p['attempt_id'][7:]) for p in original.data['cases']] + previous) + 1
    integer(attempt, 2, 1000000)
    receipt_path = history / ('attempt' + str(attempt) + '.json')
    receipt = {'kind': 'workflow-replay-attempt', 'schema_version': 1, 'original_request_sha256': digest(original.data),
               'attempt': attempt, 'run_id': identifier, 'candidate_deployment': selected.data['deployment_id'],
               'output': str(output), 'command_exit': None}
    chosen_mode = fixture_mode(mode) if mode else original.data['mode']
    cases = [make_plan(Profile.parse(p['profile']), identifier + '-' + p['case_id'], selected, chosen_mode, 'attempt' + str(attempt)).data for p in original.data['cases']]
    request = Request.parse({'kind': 'execution-request', 'schema_version': 1, 'run_id': identifier,
                            'target': target.name, 'target_identity': target.public(), 'suite': 'replay',
                            'mode': chosen_mode, 'deployment': selected.data, 'cases': cases,
                            'origin': {'request_sha256': digest(original.data), 'mode_changed': chosen_mode != original.data['mode'],
                                       'candidate_changed': selected.data['deployment_id'] != original.data['deployment']['deployment_id'],
                                       'attempt': attempt, 'source': str(source)}})
    # Reserve this ordinal once. A concurrent reservation failure never retries
    # an execution under another number automatically.
    descriptor = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as file:
        file.write(canonical(receipt) + b'\n'); file.flush(); os.fsync(file.fileno())
    try:
        summary = execute(target, request, output, progress)
        comparison = compare_executions(source, output)
        atomic_write(Path(output) / 'comparison.json', canonical(comparison) + b'\n')
        receipt['command_exit'] = summary['execution_exit']
        return summary, comparison
    except BaseException as error:
        receipt['command_exit'] = 130 if isinstance(error, KeyboardInterrupt) else 2
        raise
    finally:
        atomic_write(receipt_path, canonical(receipt) + b'\n')


def compare_executions(original_path, candidate_path):
    from .exports import compare
    original, before, _ = inspect_execution(original_path)
    candidate, after, _ = inspect_execution(candidate_path)
    rows = []
    old = {r['case_id']: r for r in before['cases']}; new = {r['case_id']: r for r in after['cases']}
    for name in sorted(set(old) | set(new)):
        if name not in old or name not in new:
            rows.append({'case_id': name, 'label': 'incomparable', 'reason': 'required case set changed'})
        elif not old[name]['bundle_id'] or not new[name]['bundle_id']:
            rows.append({'case_id': name, 'label': 'incomplete', 'reason': 'required native evidence unavailable'})
        else:
            left = inspect_bundle(Path(original_path) / 'cases' / name / 'bundle')
            right = inspect_bundle(Path(candidate_path) / 'cases' / name / 'bundle')
            rows.append({'case_id': name, **compare(left, right)})
    labels = {r['label'] for r in rows}
    label = ('incomparable' if 'incomparable' in labels else 'incomplete' if 'incomplete' in labels else
             'unsupported' if 'unsupported' in labels else 'newly-failing' if 'newly-failing' in labels else
             'fixed' if 'fixed' in labels and labels <= {'fixed', 'still-passing'} else
             'still-failing' if 'still-failing' in labels else 'still-passing')
    return {'kind': 'execution-comparison', 'schema_version': 1, 'label': label,
            'original_request_sha256': digest(original.data), 'candidate_request_sha256': digest(candidate.data),
            'original_deployment': original.data['deployment']['deployment_id'], 'candidate_deployment': candidate.data['deployment']['deployment_id'],
            'fixture_mode_changed': original.data['mode'] != candidate.data['mode'],
            'original_mode': original.data['mode'], 'candidate_mode': candidate.data['mode'], 'cases': rows}
