# Continue into Phase 7

Read AGENTS.md, STATUS.md, Phase 7 in IMPLEMENTATION_PLAN.md, E011/E012 in
TEST_EVIDENCE.md, DECISIONS.md, KNOWN_LIMITATIONS.md, formats-v1.md and reason-codes.md.
Branch remains implementation/phase-1. Preserve unrelated changes.

Phases 1–6 have passed their native gates. Do not repeat passed phases without a
specific changed prerequisite. E011 retains the full 40-case Phase 5 matrix and
14 affected supervision cases, with exact source digests and SFTP artifact readback
hashes. Sixty-three host tests include actual QNX vectors and explicitly synthetic
negative mutations. Clean source checkpoint9d4a10d passed the full40-case confirmation in evidence/phase5-clean-lifecycle (p5life-clean1).

Reuse source /home/mignon/qnx800/qnxsdp-env.sh; make qnx. No reinstall or credential
creation is needed. The existing route is ssh -F .local/ssh_config resmgrcheck-qnx
and SFTP. Guest: .local/qnx-lab/run.qcow2, loopback 22220. Preserve the original
/home/mignon/qnx-vm-resmgrcheck. Do not expose local configuration or keys.

Native runner.c and common/scenario_v1.h own exact processes, framed pipes and
bounds. Worker.c owns every service-facing call. No supervisor service open/probe;
no unknown/reaped PID signal or broad kill. Persistence status is not cleanup
authority. Failed cleanup quarantines dependents; same-parent lab recovery records
separately and never changes original status or supplies original-instance health.

The lifecycle helper serializes callbacks in one dispatch thread, always delegates
close_dup/default bookkeeping, removes OCB references before final free and retains
only immutable identifiers for saved notifications. Departure duplicates/closes
one FD before pending, kills the exact worker, then proves native reap and final
close before fresh-client use. Native observed close IDs were nonzero; synthetic
rcvid 0 is guarded but was not seen in this lab. No multithread concurrency proof.

Repeated plans have aggregate cycle1 and 1–20 child cycles (default20), same fixture,
no intercycle reset, fresh workers. Stop on unknown/dirty state. Explicit cycle
results preserve earlier outcomes and later NOT_RUN. Public job_exists/job_ready
are separate from waiter count; no memory measurements exist.

Ordering uses typed fixture control packets, never script strings or supplied
rcvids. Save a real kernel unblock at a barrier; let completion win or commit
cancellation first; inspect the obsolete notification while a fresh generation is
pending. Distinct payloads expose stale results. A parked real control request
exercises unmatched unblock safely. Complete-first also proves normal response
before signal trigger to a still-live worker. No exhaustive scheduling claim.

To qualify this checkpoint: make qnx; python3 -m unittest discover -s tests/host -q;
python3 tests/qnx/qualify-phase5.py --prefix UNIQUE. Its successful command checks
expected red results; it does not reclassify those service runs PASS. Four binaries
are uploaded/read back and verified; all 40 cases retain raw/status/result evidence.
Native rejection cases create no run storage. Use --case for focused checks.
--raw is debugging only and cannot establish a gate.

Phase6 implemented immutable bundle identities, atomic final marker/partial
artifacts, one evaluator with expected/observed values and event references, exact
replay inputs and attempt preservation, explicit --candidate-manifest selection,
architecture/version rejection, comparison, JUnit and execution exit precedence.
Saved PIDs/rcvids are observations, never replay commands. E012 passed both before/after replay gates with real source fixes, changed fixture
hashes and unchanged contracts; changing defect switches within one binary is insufficient. Product
transport automation is Phase 7. No frontend before its phase.


## Phase6 checkpoint

E012 records actual same-build FAIL replay and explicitly selected changed-build
PASS replay for both services. Candidate source c26365e removes the ignored-unblock
early return; same profile/settings/timing/inputs remain. Fixed-source worktree is
.local/phase6-fixed-source, branch qualification/phase6-fixed-unblock. Keep main's
intentional defect controls. qcc build metadata and exact source patch are retained
in evidence/phase6; binaries/readbacks stay local. No push was performed.

New host modules: artifacts.py (atomic/sealed bundles), assertions.py (canonical
expected/observed details), exports.py (JUnit/exit precedence/comparison), replay.py
(explicit candidate manifest, actual hash verification, preserved attempts). CLI:
python3 -m resmgrcheck --help. Every current expanded case/cycle is required; never
waive coverage in exports. Offline processing success is distinct from test outcome.
Eighty host tests pass. Phase6 current qualified host/source digest is in index.json;
clean host checkpoint a96c627 passed the full replay gate again as p6clean-life1
(evidence/phase6-clean).

For Phase7, reuse/refactor the tested replay lab transport without weakening
native owned-process rules. Add full target config/check/deploy/run/status/collect/
inspect/replay/report workflow, clear help and bounded cancellation/SSH recovery.
Read the exact Phase7 gate before editing. Do not add a frontend until Phase8.
