# Implementation status

Updated: 2026-11-06.

## Current checkpoint

| Item | State |
| --- | --- |
| Current gate | Phase 3 passed; Phase 4 is next |
| Phase 3 source | Qualification at base 55b6d3232d436234c4503af53e2c175435493733 plus the exact source digest in E007/index; checkpoint commit follows passing gate |
| Phase 1 / Phase 2 | Previously passed; not repeated except the affected sensor path through the new generic adapter regression |
| Target | Same qualified QNX 8.0.0 build 2026/06/05-16:26:03EDT, x86pc x86_64, KVM, one CPU / 1 GiB |
| Active blocker | None |
| Phases 4–10 | Not passed |

## Phase 3 deliverables and evidence

- Explicit versioned profile/plan/event/manifest/result/replay contracts, typed Python records and strict bounded validation. Profiles cannot execute commands or relax the planted-defect expectations.
- Pinned cJSON 1.7.19 / c859b25 with original license, file hashes and review scope. Compiled with actual qcc, C11/QNX extensions, warnings as errors, nesting limit 12 and libm.
- Public adapter ABI 1, capability vocabulary, typed results/facts, generic worker command roles and registration outside core files.
- Sensor integrated behind the adapter with the proven pending/unblock/default-handler semantics and 500/2000 ms timeout/allowance retained.
- Original job fixture: one bounded lab job slot and eight waiters; SUBMIT/COMPLETE/WAIT_RESULT, waiter-only cancellation, non-consuming retrieval by a fresh client. Ordinary devctl and explicit _IO_DEVCTL results match. The actual ENOENT probe returned 2 with errno 0; timeout returned MsgSendv -1 / errno 260.
- One generic runner/worker path and one deterministic Python evaluator, with no service-name conditions in the core. Both corrected profiles PASS; both ignore-unblock cases FAIL for cancellation/pending cleanup; a missing required capability is UNSUPPORTED before child launch.
- Twenty-one host validation/evidence-mutation tests pass. Nine malformed native command variants are rejected on QNX before collection/process launch. All four deployed binaries matched SFTP readback hashes; all owned children were reaped; no residual fixture/worker/runner was found.

See E007 in [TEST_EVIDENCE.md](TEST_EVIDENCE.md), [formats-v1.md](formats-v1.md), [adapters.md](adapters.md), and the retained plans, native streams, evaluated results, commands and index in `docs/evidence/phase3/`. Host mutation tests remain labeled synthetic; native claims come from actual QNX execution.

## Next executable step

Proceed into Phase 4: dependable common state machine, structured-channel and sink failures, exact owned-process cleanup, explicit crash/start/probe classification, contamination handling, and remote interruption/reconnection status. Qualify normal, stuck, crashed and unavailable workers/services, blocked probes, malformed events, lost transport and cleanup failure independently. Do not call the existing Phase 3 runner production supervision merely because the happy path and planted defect pass.

The lab VM remains running. SSH uses the existing ignored `.local/ssh_config`; preserve original images, keys, overlays and logs. Phase 3 qualification used the owned target directory `/data/resmgrcheck/p3gate1` and fresh run IDs. No credentials were regenerated, host services changed, or publication performed.
