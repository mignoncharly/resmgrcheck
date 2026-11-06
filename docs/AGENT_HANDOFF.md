# Continue into Phase 5

Read AGENTS.md, STATUS.md, Phase 5 in IMPLEMENTATION_PLAN.md, E009 in
TEST_EVIDENCE.md, DECISIONS.md, KNOWN_LIMITATIONS.md and reason-codes.md first.
Preserve unrelated changes. Branch remains implementation/phase-1.

Phases 1–4 have passed. Phase 4 checkpoint 1d49ad4 was requalified clean with all 22 cases (p4clean1). Phase 4's 22 native fault cases, actual paused-target
infrastructure bound and changed-writer SSH-loss/reconnect regression are retained
in docs/evidence/phase4*, against explicit source digest/artifact identities. The
same generic binaries normal-PASSed both profiles. Thirty-five host tests pass.
Signal/departure/repetition/ordering are Phase 5 work; no capability is added merely
to make required checks pass. Keep native evidence distinct from synthetic host
mutations and operator bootstrap logs.

Reuse source /home/mignon/qnx800/qnxsdp-env.sh; make qnx. Build metadata checks
source/binary freshness before expansion. No reinstall, keys or credentials needed.
Use ssh -F .local/ssh_config resmgrcheck-qnx and the existing SFTP route. VM uses
.local/qnx-lab/run.qcow2 and loopback 22220. Preserve /home/mignon/qnx-vm-resmgrcheck.
No monitor/slm was in the lab inventories; inspect again if changing the image.
The target pause test restored the same owned VM without rebooting anything.

Native implementation: runner.c owns processes, framed pipes and deadlines;
worker.c owns every service-facing adapter call; common/process.c never signals
unknown/reaped children. common/journal.c contains primary failures and seals
recovery observations. common/persistence.c creates exclusive run storage and
atomically publishes status. --after=RUN_ID withholds contaminated dependencies.
Stored PIDs are never cleanup authority. Adapter registration is outside generic
runner/evaluator, which contain no service-name conditions.

Explicit --lab controls are qualification-only, require --persist and cannot be
selected by a profile. tests/qnx/qualify-phase4.py uses fresh lab paths/run IDs,
readback hashes, exact expected outcomes, actual frame/channel faults and a small
isolated full filesystem. Its shell owns/reaps only that storage driver. The
cleanup-failure control seals original incomplete status before separate same-parent
lab recovery. Recovery never rewrites the result or releases dependent quarantine.
The ownership-loss control records a deliberately discarded wait; no signal is
sent to the uncertain child. No residual project process remained in inventory.

Reproduction: make qnx; python3 -m unittest discover -s tests/host -v;
python3 tests/qnx/qualify-phase4.py --prefix UNIQUE;
python3 tests/qnx/qualify-target-loss.py --prefix UNIQUE;
python3 tests/qnx/qualify-persistence.py --prefix UNIQUE.
Do not rerun passed phases without a specific changed prerequisite. Full host
application transport, product replay/export/report commands remain later phases.

Phase 5 must use a single-thread SIGUSR1 handler (sig_atomic_t only), no retry,
no simultaneous operation timeout, actual pending barrier and observed signal/error
behavior. Departure must observe actual reaping and preserve close_dup/default
bookkeeping and OCB lifetime. Repeat against one instance, 20 cycles by default;
stop after unknown contamination. Directed ordering must record the actual order,
not claim exhaustive concurrency coverage. Test both corrected and targeted
negative controls on real QNX before the Phase 5 gate.

## Phase 5 signal subgate completed

E010 / docs/evidence/phase5-signal records eleven real native cases and five new
native input rejections from p5signal6. New profiles sensor-signal.json and
job-signal.json select one explicit signal family, expected EINTR, required signal
capability and signal_mode non-restart-no-retry. Auto-restart is parsed as a known
request but becomes UNSUPPORTED before child launch. Required cycles still equal
one in this milestone. Existing timeout profiles keep their original expectations.

The worker's handler only changes volatile sig_atomic_t. Flags 0 and actual mask
are recorded outside the handler; no TimerTimeout is armed in signal role and no
retry occurs. The parent waits for operation_armed plus fixture pending, then records
trigger_requested and the separate actual signal-send result. Raw MsgSendv errno
is captured before logging the handler flag. Signal number is bound to the QNX
manifest signal_codes, rather than Python/Linux constants. Both corrected paths
PASSed; both ignored-unblock paths FAILed specifically. The affected timeout paths
also retained their outcomes. Forty-six host tests pass.

Continue with Phase 5 departure, repeated cancellation/reconnect and ordering.
Do not call this partial scenario milestone a Phase 5 gate. Generic runner/evaluator
still contain no service-name conditions. Existing close_dup code is not a native
proof of departure, duplicate-FD or OCB lifetime correctness. Use the installed
QNX documentation and actual callback/termination observations for that next step.

Phase 5 source checkpoint e78502f is committed and clean-source confirmed. The full
11-case signal/timeout/capability matrix, five native rejection checks and a focused
four-case normal/interference/evidence-loss check passed from that clean source.
See the two phase5-clean evidence bundles and the closing E010 confirmation.
The broader affected-path follow-up has 24 native supervision cases. Native
process_exit facts separate actual exit/signal observations from raw wait bits;
worker_close_failed and worker_exit_failed are execution ERRORs, not missing
logs. Preserve earlier independently returned bad payloads under later interference.
Forty-six host tests pass. Continue the remaining Phase 5 families from this state.
