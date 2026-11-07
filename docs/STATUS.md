# Implementation status

Updated: 2026-11-07.

| Item | State |
| --- | --- |
| Current phase | Phase 10 in progress: local demo and submission package |
| Phases 1–4 | Previously passed; only affected supervision prerequisites rechecked |
| Phase 5 | Full 40-case native matrix; 63 host tests |
| Qualified source | 9d4a10d, dirty=false; complete 40-case confirmation in evidence/phase5-clean-lifecycle |
| Target | Existing QNX 8.0.0 build 2026/06/05-16:26:03EDT, x86_64 KVM, one CPU / 1 GiB |
| Active blocker | None |
| Phase 6 | Immutable bundles, explicit changed-build replay on both services, comparison/JUnit passed |
| Phase 7 | Full native workflow/negative/recovery gate passed E013; 95 host tests |
| Phase 8 | Offline HTML, honest comparison, 105 host tests /45 browser views passed E014 |
| Phase 9 | Clean source/reused-target workflow passed E015:58 native cases,36 release expectations |
| Phase 10 | Local copy/rules/evidence map prepared; actual recording/package pending |

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
exit gate is passed; native/host source identities are recorded separately. Clean host checkpoint
a96c627 passed the complete replay gate again (evidence/phase6-clean).

Phase7 now implements named target configuration, doctor, immutable SFTP-verified
deployment, six-family run/replay, persistent status/collection, candidate selection,
offline HTML and expected-outcome release verification. External attachment
is an explicit read-only health diagnostic with unverified build/instance identity;
private lifecycle remains UNSUPPORTED. E013 records the final source-qualified end-to-end, negative and recovery matrix,
75 distinct native cases and36 exact release expectations. The Phase7 exit gate
passed. Phase8 passed E014:15 actual/synthetic-scoped reports,45 offline browser views,
no external requests, every artifact link valid, raw/JSON/JUnit unchanged.
Phase9 completed source/input/ownership review, codelab, adapter and dependency
records. E015 has58 clean-source native cases, both real source-fix replays and
36 exact release expectations; clean host106 and report-follow-up107 tests passed.
Next: Phase10 concrete demo, evidence map and submission/release package.

Preserve SDK, images and local authentication. Use fresh run IDs; native records
remain /data/resmgrcheck/runs/RUN_ID, host sessions /data/resmgrcheck/sessions/ID.
The small guest has3072 file entries. Verified historical archives preserve bytes
and start guards; monitor target storage before another large matrix.

Phase9 review found and fixed uninitialized fixture transition output on rejected
commands, bounded current-message input/reply handling and writable-OCB checks.
Focused actual QNX input checks passed on both services as p9-input3, including
exact rejection errors and unchanged state/fresh-client health. Combined custom
wire operations are outside the fixed lab protocol; tested prefixes were rejected
by the framework, without claiming the tail ran. Full Phase9 gate subsequently passed E015 from clean d2e0a43.
The completed p7gate3 target histories/sessions have subsequently been archived
with owned-helper/SFTP/cksum/SHA256 verification; all start guards remain. Use their
committed/offline copies. Unknown/missing status never becomes PASS.
