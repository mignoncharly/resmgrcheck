# Reason codes

The shared Python evaluator issues verdicts. Native problem events describe
execution facts; they do not issue service verdicts. Overall ERROR takes precedence
over FAIL, while every independently established FAIL assertion remains in the
result. Cleanup, collection completion and recovery are separate observations.

| Code | Meaning / class |
| --- | --- |
| all_obligations_satisfied | PASS only after all required assertions and complete evidence |
| cancellation_not_completed | FAIL: valid baseline, observed pending/live cancellation, original completion bound expired without completion |
| unexpected_operation_result | FAIL: actual operation/health result violates the valid contract |
| pending_state_not_released | FAIL: observed pending count violates the post-cancellation contract |
| unexpected_service_state | FAIL: observed typed state facts violate the contract |
| baseline_invalid | ERROR: valid baseline cannot be established |
| precondition_not_established | ERROR: required pending/cancellation precondition cannot be established |
| worker_start_failed | ERROR: actual process creation/channel setup failed; raw spawn error retained |
| worker_close_failed | ERROR: worker close returned failure; raw errno retained separately from process cleanup and evidence completeness |
| worker_exit_failed | ERROR: observed nonzero worker exit not already explained by close failure |
| worker_crashed | ERROR: unexpected signal/death, with actual wait status |
| worker_timeout | ERROR: ordinary worker exceeds its supervisory bound |
| service_unavailable | ERROR: fixture readiness or real worker open failed |
| probe_timeout | ERROR: readiness/state/health worker exceeds its bound |
| case_deadline | ERROR: execution containment deadline reached |
| service_interference | ERROR: unexpected fixture termination, changed/multiple instance publication or equivalent interference; actor is unknown unless separately observed |
| evidence_invalid | ERROR: malformed, oversized, wrong identity/role/type/sequence or otherwise invalid required frame |
| evidence_incomplete | ERROR: truncated/missing required evidence; does not infer a service failure |
| evidence_loss | ERROR: failed producer channel/write or exit 120; raw status retained |
| evidence_capacity_exceeded | ERROR: bounded frame/event/journal capacity exceeded |
| event_sink_failed | ERROR: primary write/flush failed; raw target errno retained |
| status_write_failed | ERROR: persistent status could not be updated |
| ownership_unknown | ERROR: exact live-parent child ownership/wait status lost; never signal the uncertain PID |
| scenario_trigger_failed | ERROR: owned-worker scenario signal request failed; raw error retained |
| cleanup_signal_failed | ERROR: owned-child termination request failed; not a reaping result |
| cleanup_failed | ERROR: original bounded cleanup did not establish all owned children reaped |
| cleanup_unestablished | ERROR: required cleanup observation is missing; no assertion that cleanup actually failed or succeeded |
| target_unreachable | ERROR: host could not reach target within its outer bound; no inferred remote cleanup |
| transport_incomplete | ERROR: transport/collection did not establish complete evidence |
| target_completion_unestablished | ERROR: stale, running, absent or inconsistent final status/ownership/source binding |
| required_capability_missing | UNSUPPORTED: required compiled capability absent, before child launch |
| signal_mode_unsupported | UNSUPPORTED: automatic-restart signal mode has not been implemented/qualified |
| service_mode_unsupported | UNSUPPORTED: requested service mode is not implemented |
| prior_cleanup_failed | NOT_RUN: explicit predecessor remains quarantined after failed cleanup |
| predecessor_unestablished | NOT_RUN: predecessor status is missing, running, malformed or otherwise cannot establish a clean dependency |

Native exit 0 means the collector completed, including a fully observed service
FAIL. Native 2 declares execution/evidence/cleanup error, 3 unsupported, and 4 a
withheld dependent case. A detached status exit code is a declaration, not a host
wait of that process. Host evaluation exits PASS=0, FAIL=1, ERROR=2,
UNSUPPORTED=3, NOT_RUN=4.

An unavailable sink can also establish evidence_incomplete. A demonstrated service
failure followed by a sink or cleanup error retains both reasons. Successful
separate lab recovery never erases original cleanup failure, releases quarantine,
or supplies original-instance health. See E009 and the exact per-case reason sets
in evidence/phase4/index.json.
