# Implementation status

Updated: 2026-11-07.

| Item | State |
| --- | --- |
| Current phase | Phase 6 gate passed E012; Phase 7 next |
| Phases 1–4 | Previously passed; only affected supervision prerequisites rechecked |
| Phase 5 | Full 40-case native matrix; 63 host tests |
| Qualified source | 9d4a10d, dirty=false; complete 40-case confirmation in evidence/phase5-clean-lifecycle |
| Target | Existing QNX 8.0.0 build 2026/06/05-16:26:03EDT, x86_64 KVM, one CPU / 1 GiB |
| Active blocker | None |
| Phase 6 | Immutable bundles, explicit changed-build replay on both services, comparison/JUnit passed |
| Phases 7–10 | Not started |

Both services use the same generic runner, worker, scenario machinery and Python
evaluator. Normal API/MsgSendv/duplicate-descriptor/deferred baselines, timeout,
non-restart SIGUSR1, forced departure, 20-cycle reconnect and both directed orders
have passed on real QNX. Every required observation is explicit. Deliberate defects
remain FAIL; harness faults remain ERROR; unavailable capabilities are UNSUPPORTED;
withheld cycles are NOT_RUN. The matrix checker succeeding does not turn planted
service failures into successful service runs.

Departure observes pending, exact owned SIGKILL, actual native wait/reap, two
close_dup/default callbacks and one final OCB/default callback, then state and
fresh-client health on the original instance. Job ownership survives waiter death.
Ignored unblocks can prevent the worker's observed death within the bound even
when kill succeeds; those cases are ERROR/departure_unobserved and health is withheld.

Repetition keeps one fixture, fresh clients and increasing generations/unblock
counters. Retain-third yields PASS/PASS/FAIL and 17 NOT_RUN; a cycle-two blocked
probe yields PASS/ERROR and 18 NOT_RUN. Failed final cleanup retains service FAIL
and separate recovery never rewrites original status. No memory-leak claim is made.

Directed fixture barriers record cancellation before completion and completion
winning over a queued real unblock. A separate normal-result-before-SIGUSR1 check
also passes. A distinct subsequent payload, current-owner checks, safe obsolete/
unmatched handling and targeted duplicate-terminal controls are verified. These
are directed checks, without exhaustive concurrency coverage.

Fourteen affected supervision checks passed: crash, blocked probes, malformed/
truncated/overfull evidence, primary sink failure, interference, failed cleanup,
unknown ownership and dependent quarantine. Existing legacy bounds stay fixed;
repeat runs have separately bounded larger ledgers/journals. See E011, the
supported-scenario matrix and reason-code documentation.

Phase6 now preserves immutable, hashed raw bundles and partial artifacts, with
atomic finalization, source/profile/build/replay snapshots and one canonical
evaluator exposing expected/observed assertion details. Explicit candidate manifests
select deployed executables; actual uname and SFTP readback hashes are checked
before one launch. All attempts, including failed preflight, are preserved.

E012 reproduces both saved failures against the original build, then PASSes the
identical contracts/settings against committed source-fixed fixtures c26365e with
changed binary hashes. Main retains its intentional negative controls. Mixed JUnit
contains32 tests /6 failures /4 errors /18 skipped and required-coverage errors;
regenerating views leaves raw bytes unchanged. Eighty host tests pass. Full Phase6
exit gate is passed; native/host source identities are recorded separately.

Next: Phase7 host workflow (target config/check/deploy/run/status/collect/inspect/
report), owned lab cleanup boundaries and help. Replay currently supports the
reviewed lab deployment route; full product transport commands are not complete.
Preserve SDK, images and local authentication. Use fresh run IDs; target records
remain /data/resmgrcheck/runs/RUN_ID.
