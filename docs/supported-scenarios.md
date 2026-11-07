# Supported native scenarios

Phase 5 gate E011, QNX 8 x86_64 KVM, managed single-dispatch-thread fixtures.
Both services use one generic runner/worker/evaluator; only registered adapters and
fixtures know service names/message layouts. Profiles declare the corrected
contract; a plan's defect mode never relaxes it. Independent families start a new
fixture. Repetition keeps that original instance across all cycles.

| Required family | Sensor fixed | Job fixed | Deliberate controls / expected result |
| --- | --- | --- | --- |
| Normal/fresh baseline | read, MsgSendv, shared FD, deferred release; value42 | devctl, MsgSendv, shared FD, deferred release; job1/value420; ENOENT diagnostic | Baseline remains valid for lifecycle defects |
| Timeout | -1/ETIMEDOUT260; pending0; original fresh health | Same plus retained incomplete job and fresh result retrieval | ignore-unblock: FAIL cancellation/state; retain-waiter: FAIL pending; duplicate-terminal: FAIL attempt |
| Signal | SIGUSR1=16, flags0, unblocked, no retry/timer; -1/EINTR4, handler seen | Same; job remains | ignore-unblock: FAIL cancellation/state |
| Departure | Confirm pending; owned SIGKILL9; actual reap; close/default/final OCB; health | Same; job survives waiter departure and is completed/retrieved | retain-waiter: FAIL pending; drop-job: FAIL state and retrieval; ignored unblock: ERROR departure_unobserved |
| Repeat/reconnect | 20 timeout cycles, fresh clients, one instance, increasing generation/counter, per-cycle state/health/cleanup | Same; job presence is separate from pending waiters | retain-third: PASS/PASS/FAIL +17 NOT_RUN; ignored unblock: FAIL +19 NOT_RUN |
| Completion-first | Real unblock barrier; completion wins; normal result also observed before a later signal trigger | Same | duplicate-terminal: FAIL even when kernel rejects second call |
| Cancellation-first | Interrupted result observed before work release | Same | duplicate-terminal: FAIL |
| Obsolete/unmatched notification | Current-owner check; old notification inspected during distinct new generation; real parked control cancelled safely | Same | Any duplicate attempt remains FAIL; old payload cannot satisfy later contract |

All fixed rows PASS on actual QNX. Full matrix: 40 service runs, exactly
12 PASS / 19 FAIL / 6 ERROR / 3 UNSUPPORTED. Repeat runs contain 200 explicit cycle
results: 46 PASS, 6 FAIL, 2 ERROR, 146 NOT_RUN. The counts include containment controls:
cycle-two stuck probe yields PASS/ERROR +18 NOT_RUN; failed final cleanup retains
first-cycle FAIL +19 NOT_RUN and separate recovery. These controls qualify the
checker, not service correctness. Expected red service results remain red.

Reviewed profiles: sensor/job .json (timeout), and paired -signal, -departure,
-repeat, -complete-first, -cancel-first profiles. Repeat defaults20, allows1–20;
all others exactly1. Ordering requires distinct next_health facts. Automatic
restart, external attach and sensor error-probe are explicit UNSUPPORTED.
Optional names do not mean executed coverage. No randomized scheduler, multithread
close race, hardware timing, complete receive-ID reuse, or memory-leak proof is
claimed. See evidence/phase5/index.json for exact individual identities/reasons.

Run `python3 tests/qnx/qualify-phase5.py --prefix UNIQUE` after `make qnx` for the
terminal demonstration. The command succeeds only if every actual case matches
its expected verdict/reason set. It never substitutes PASS for a planted failure.
