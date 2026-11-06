# Implementation status

Updated: 2026-11-06.

| Item | State |
| --- | --- |
| Current phase | Phase 5: in progress; signal-interruption subgate passed E010 |
| Phase 4 | Passed E009: complete native supervision/failure/transport matrix |
| Phases 1–3 | Previously passed; not repeated |
| Phase 4 qualified source | 1d49ad4, dirty=false; complete 22-case confirmation in evidence/phase4-clean |
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
regression passed. Forty-six host tests pass, including the new Phase 5 signal rules. See E009 in TEST_EVIDENCE.md and
reason-codes.md for precise outcomes and limits.

Phase 5 now has explicit reviewed signal profiles, a single-thread SIGUSR1 worker,
minimal sig_atomic_t handler, flags 0, verified unblocked mask, no application retry
and no armed operation timer. The supervisor signals only after actual pending
confirmation. Both corrected services PASSed with actual MsgSendv -1/EINTR 4 and
handler observation; both ignore-unblock controls retained the expected service
FAILs. Target SIGUSR1=16 is bound through native manifest metadata. Automatic-restart
mode is UNSUPPORTED before launch. The affected timeout baselines/controls were
specifically rechecked. Eleven native cases and five new native input rejections
passed, with exact ownership/reaping and no residual project process (E010). The
shared producer follow-up also passed 24 supervision cases, preserving both fixture
death and evidence loss for the same actual write failure.

Next: implement client departure with real close_dup/final OCB ordering proof,
20-cycle same-instance repetition with contamination stopping, and directed
completion/cancel ordering on both services. These remain required Phase 5 gates;
Phase 5 is not complete. No Phase 6 work has started.

Preserve the running lab, ignored SDK/configuration and original images/keys.
Qualified matrix deployment is /data/resmgrcheck/p4gate3; persistence regression
is p4gate4. Phase 5 signal deployment is p5signal6. Persistent records are /data/resmgrcheck/runs/RUN_ID; use fresh run IDs.
