# Continue into Phase 5

Read AGENTS.md, STATUS.md, Phase 5 in IMPLEMENTATION_PLAN.md, E009 in
TEST_EVIDENCE.md, DECISIONS.md, KNOWN_LIMITATIONS.md and reason-codes.md first.
Preserve unrelated changes. Branch remains implementation/phase-1.

Phases 1–4 have passed. Phase 4's 22 native fault cases, actual paused-target
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
