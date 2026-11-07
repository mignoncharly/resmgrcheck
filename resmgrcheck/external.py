"""Read-only external diagnostics; no unobserved lifecycle/build identity claims."""
from .contracts import EvaluatedResult
from .reasons import ASSERTION_REASONS


def evaluate_external(plan, ev, result):
    expected = plan.profile.data['expectations']
    def add(name, verdict, rows=()):
        result['assertions'].append({'id': name, 'verdict': verdict, 'event_refs': ev.refs(rows)})
    scope = ev.select('external_scope')
    opens = ev.select('external_open')
    valid = (len(scope) == 1 and scope[0]['data'] == {'path': plan.profile.data['service']['device'],
             'read_only': 1, 'service_build_verified': 0, 'instance_verified': 0}
             and set(ev.child_producers.values()) <= {'worker'} and not ev.select('fixture_stop')
             and all(role in {'ready', 'normal', 'message', 'health', 'state'} for role in ev.spawned.values())
             and len(opens)==len(ev.spawned) and {r['pid'] for r in opens}==set(ev.spawned)
             and all(r['data']=={'read_only':1,'error':0} for r in opens))
    add('external_scope', 'PASS' if valid else 'ERROR', scope + opens)
    rows = ev.select('result', operation='normal') + ev.select('result', operation='message')
    good = len(rows) == 2 and {r['data']['operation'] for r in rows} == {'normal', 'message'} and all(r['data']['normalized'] == 'OK' and r['data']['facts'] == expected['health'] for r in rows)
    add('baseline_validity', 'PASS' if good else 'NOT_RUN' if ev.problems else 'ERROR', rows)
    state = ev.select('control_result', operation='state')
    observed = len(state) == 1 and state[0]['data']['error'] == 0
    add('state_observation', 'PASS' if observed else 'ERROR', state)
    add('external_public_state', 'PASS' if observed and state[0]['data']['facts'] == expected['state_after'] and state[0]['data']['pending'] == expected['pending_after'] else 'FAIL' if observed else 'NOT_RUN', state)
    health = ev.select('result', operation='health')
    healthy = len(health) == 1 and health[0]['data']['normalized'] == 'OK' and health[0]['data']['facts'] == expected['health'] and all(health[0]['pid'] != r['pid'] for r in rows)
    add('fresh_client_health', 'PASS' if healthy else 'FAIL' if health else 'NOT_RUN', health)
    cleanup = ev.select('cleanup'); reaped = ev.select('reaped')
    clean = len(cleanup) == 1 and cleanup[0]['data']['all_reaped'] == 1 and {r['data']['child_pid'] for r in reaped} == set(ev.spawned)
    add('owned_process_cleanup', 'PASS' if clean else 'ERROR', cleanup + reaped)
    natural = {r['pid'] for r in ev.select('result') + ev.select('control_result')}
    complete = not ev.read_error and ev.final and ev.final['data']['evidence_error'] == 0 and ev.final['data']['flow_complete'] == 1
    for pid in natural:
        ended = [r for r in ev.select('worker_final', pid=pid)]
        closed = ev.select('closed', pid=pid)
        native = [r for r in ev.select('process_exit') if r['data']['child_pid'] == pid]
        complete = complete and len(ended) == len(closed) == len(native) == 1 and ended[0]['data']['exit_code'] == native[0]['data']['exit_code'] == 0 and closed[0]['data']['rc'] == 0
    add('evidence_completeness', 'PASS' if complete else 'ERROR', [ev.final] if ev.final else [])
    verdicts = {a['verdict'] for a in result['assertions']}
    result['verdict'] = next(v for v in ('ERROR', 'FAIL', 'NOT_RUN', 'PASS') if v in verdicts)
    result['reasons'] = list(dict.fromkeys(ASSERTION_REASONS.get(a['id'], a['id']) for a in result['assertions'] if a['verdict'] in {'ERROR', 'FAIL'})) or ['all_obligations_satisfied']
    result['completion'] = 'complete' if complete and clean else 'incomplete'
    return EvaluatedResult.parse(result)
