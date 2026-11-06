# Implementation status

Updated: 2026-11-06.

| Item | State |
| --- | --- |
| Current phase | Phase 5: complete the native scenario suite |
| Phase 4 | Passed E009: complete native supervision/failure/transport matrix |
| Phases 1–3 | Previously passed; not repeated |
| Phase 4 qualified source | base 175a6af plus explicit dirty digest ee3f95b47f01f0d447c768f57f41f3a44cd3f386f3fef0b888b5fa8e2f409e9e |
| Target | Existing QNX 8.0.0 build 2026/06/05-16:26:03EDT, x86_64 KVM, one CPU / 1 GiB |
| Active blocker | None |
| Phases 6–10 | Not started |

Phase 4 now uses a bounded common state machine, per-child nonblocking framed
channels, strict producer validation, exact live-parent ownership and wait/reap
tracking, worker-only service-facing probes, independent execution/cleanup/host
bounds, persistent status and a bounded recovery journal. The complete 22-case
native matrix passed its exact expected verdict/reason sets. It includes actual
SIGSEGV, spawn/open/probe faults, malformed/truncated/overfull channels, unavailable
and genuinely full primary sinks, fixture interference, cleanup failure, unknown
ownership, dependent NOT_RUN and missing-capability UNSUPPORTED. Both normal
services PASSed through the same runner/worker.

A failed-cleanup case retained both service FAIL assertions and cleanup ERROR.
Separate same-parent lab recovery restored the test lab while original status
remained incomplete and its dependent stayed NOT_RUN. No unknown PID was signalled.
A temporarily paused owned VM produced target_unreachable with remote cleanup
NOT_RUN. The changed writer's actual SSH-loss/reconnect and duplicate-start
regression passed. Thirty-five host tests pass. See E009 in TEST_EVIDENCE.md and
reason-codes.md for precise outcomes and limits.

Next: commit the passed Phase 4 checkpoint, confirm its clean source identity, then
implement Phase 5 in plan order: normal/timeout, signal, client departure, 20-cycle
same-instance repetition and directed ordering on both fixtures. Signal/departure
remain UNSUPPORTED until actually implemented and qualified. No later gate is
claimed by the existing timeout results.

Preserve the running lab, ignored SDK/configuration and original images/keys.
Qualified matrix deployment is /data/resmgrcheck/p4gate3; persistence regression
is p4gate4. Persistent records are /data/resmgrcheck/runs/RUN_ID; use fresh run IDs.
