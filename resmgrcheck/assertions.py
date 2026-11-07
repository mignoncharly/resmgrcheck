"""Canonical assertion explanations; values come from the contract or raw records."""
from .contracts import MAX_FRAME, Invalid, loads
from .reasons import ASSERTION_REASONS

REASONS = {
    **ASSERTION_REASONS,
    'client_departure': 'departure_unobserved',
    'ocb_lifetime': 'ocb_lifetime_unestablished',
    'single_instance': 'service_interference',
    'ordering_result': 'unexpected_operation_result',
    'terminal_ownership': 'duplicate_terminal_attempt',
    'stale_notification': 'stale_notification_unsafe',
    'fresh_result': 'stale_result',
    'unmatched_notification': 'unmatched_notification_unsafe',
    'completion_before_trigger': 'ordering_unestablished',
    'directed_order': 'ordering_unestablished',
    'repeat_coverage': 'repetition_incomplete',
    'worker_cleanup': 'cycle_cleanup_unestablished',
    'cycle_boundary': 'evidence_incomplete',
    'completion_control': 'unexpected_operation_result',
    'control_contract': 'unexpected_operation_result',
    'counter_continuity': 'counter_reset',
    'ordering_coverage': 'ordering_incomplete',
}


def expected_value(name, plan, cycle):
    profile = plan.data['profile']
    expectation = profile['expectations']
    family = plan.data['case_id']
    health = expectation.get('next_health', expectation['health'])
    values = {
        'baseline_validity': {'normal': 2, 'message': 1, 'facts': expectation['health'],
                              'deferred_release': True},
        'pending_precondition': {'pending': 1, 'confirmed_before_trigger': True,
                                 'live_unblock_required': expectation['require_unblock']},
        'cancellation_completion': {'api': 'MsgSendv', 'raw_return': -1,
                                    'error_name': expectation['cancel_error'],
                                    'allowance_ms': profile['timing']['cancellation_ms']},
        'cancellation_not_completed': {'completed_within_allowance_ms': profile['timing']['cancellation_ms']},
        'pending_state_cleanup': {'pending': expectation['pending_after']},
        'state_facts': expectation['state_after'],
        'state_observation': {'error': 0, 'same_generation': True},
        'fresh_client_health': {'normalized': 'OK', 'facts': health, 'original_instance': True},
        'client_departure': {'signal': 'SIGKILL', 'observed_reap': True,
                             'allowance_ms': profile['timing']['cancellation_ms']},
        'ocb_lifetime': {'close_dup': 2, 'close_dup_default': 2, 'close_ocb': 1,
                         'close_ocb_default': 1, 'default_status': 0, 'final_after_last_close': True},
        'single_instance': {'fixture_count': 1, 'ready_count': 1},
        'counter_continuity': {'unblocks': cycle},
        'repeat_coverage': {'cycles': profile['suite']['cycles'], 'reset': 'same-instance',
                             'all_required_cycles_complete': True},
        'worker_cleanup': {'all_cycle_workers_reaped': True},
        'owned_process_cleanup': {'all_owned_children_reaped': True},
        'cycle_boundary': {'known_state': True, 'clean': True},
        'terminal_ownership': {'terminal_attempts_per_request': 1},
        'duplicate_terminal_attempt': {'terminal_attempts_per_request': 1},
        'terminal_reply_observation': {'primary_reply_rc': 0, 'primary_reply_error': 0},
        'signal_handler_observation': {'name': 'SIGUSR1', 'seen': 1},
        'stale_notification': {'matched': 0, 'checked_after_terminal': True},
        'fresh_result': {'normalized': 'OK', 'facts': health, 'new_logical_and_generation': True},
        'unmatched_notification': {'current_owner_checked': True, 'error_name': 'EINTR'},
        'ordering_result': {'api': 'MsgSendv', 'normalized': 'OK' if family == 'complete-first' else 'INTERRUPTED',
                             'facts': expectation['health'] if family == 'complete-first' else {}},
        'directed_order': {'order': family, 'explicit_barrier': True},
        'completion_before_trigger': {'normal_result_before_signal_request': True},
        'ordering_coverage': {'directed_order_complete': True},
        'target_completion_status': {'finalized': True, 'identity_and_ownership_bound': True},
        'evidence_completeness': {'complete_required_evidence': True},
        'completion_control': {'error': 0},
        'control_contract': {'error': 0},
        'scenario_execution': {'flow_complete': 1},
        'remote_cleanup': {'cleanup_observed': True},
    }
    if family == 'external-health':
        values.update(external_scope={'path': profile['service']['device'], 'read_only': 1,
                                     'service_build_verified': 0, 'instance_verified': 0},
                      baseline_validity={'normal': 1, 'message': 1, 'facts': expectation['health']},
                      state_observation={'error': 0},
                      external_public_state={'pending': expectation['pending_after'], 'facts': expectation['state_after']},
                      fresh_client_health={'normalized': 'OK', 'facts': expectation['health'],
                                           'instance_identity': 'unverified', 'path': profile['service']['device']})
    return values.get(name, {'absent_problem': REASONS.get(name, name)})


def explain(result, plan, raw, status=None):
    """Add details without changing decisions or inventing unobserved private state."""
    records = {}
    for index, line in enumerate(raw.splitlines(keepends=True)):
        try:
            if not line.endswith(b'\n'):
                break
            records[index] = loads(line, MAX_FRAME)
        except Invalid:
            break

    def fill(assertions, cycle):
        for assertion in assertions:
            name, verdict = assertion['id'], assertion['verdict']
            reason = REASONS.get(name, name)
            if verdict == 'PASS':
                reason = 'all_obligations_satisfied'
            elif verdict == 'NOT_RUN' and not name.startswith(('prior_', 'baseline_unestablished', 'predecessor_')):
                reason = 'prerequisite_unavailable'
            assertion.update(reason=reason, expected=expected_value(name, plan, cycle),
                             observed={'events': [records[r] for r in assertion['event_refs'] if r in records],
                                       'status': status if name == 'target_completion_status' else None})
    fill(result['assertions'], plan.data['cycle'])
    for cycle in result.get('cycles', []):
        fill(cycle['assertions'], cycle['cycle'])
    return result
