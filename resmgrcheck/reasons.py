"""Stable observed infrastructure failures; service assertions remain separate."""
NATIVE_ERRORS=frozenset({'worker_start_failed','worker_timeout','worker_crashed','service_unavailable',
 'probe_timeout','case_deadline','precondition_not_established','evidence_loss','evidence_invalid',
 'evidence_incomplete','evidence_capacity_exceeded','event_sink_failed','status_write_failed',
 'ownership_unknown','cleanup_failed','cleanup_signal_failed','service_interference'})
ASSERTION_REASONS={'pending_precondition':'precondition_not_established',
 'pending_state_cleanup':'pending_state_not_released','cancellation_completion':'unexpected_operation_result',
 'fresh_client_health':'unexpected_operation_result','owned_process_cleanup':'cleanup_failed',
 'terminal_reply_observation':'evidence_incomplete','state_observation':'evidence_incomplete',
 'evidence_completeness':'evidence_incomplete','baseline_validity':'baseline_invalid',
 'state_facts':'unexpected_service_state'}
