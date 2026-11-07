# Implementation status

Updated: 2026-11-07.

| Item | State |
| --- | --- |
| Current phase | Phase 5 gate passed E011; continue into Phase 6 |
| Phases 1–4 | Previously passed; only affected supervision prerequisites rechecked |
| Phase 5 | Full 40-case native matrix; 63 host tests |
| Qualified source | Base 26c3223 plus exact source digest in evidence/phase5/index.json; clean confirmation follows checkpoint |
| Target | Existing QNX 8.0.0 build 2026/06/05-16:26:03EDT, x86_64 KVM, one CPU / 1 GiB |
| Active blocker | None |
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

Next: Phase 6 immutable evidence bundles, atomic finalization, assertion details,
replay/candidate identity, comparison and JUnit. The changed-build replay exit gate
has not passed. Preserve the existing lab, SDK, images and local authentication.
Use fresh run IDs; target records remain /data/resmgrcheck/runs/RUN_ID.
