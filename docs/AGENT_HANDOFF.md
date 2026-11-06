# Continue Phase 4

Read AGENTS.md, STATUS.md, the relevant implementation plan, E007 in
TEST_EVIDENCE.md, DECISIONS.md, formats-v1.md and adapters.md. Inspect the actual
Git state and preserve unrelated work. Branch remains implementation/phase-1.

## Passed prerequisites

Phases 1 and 2 remain passed. Their gates were not restarted. Phase 3's changed
sensor path was requalified through the generic adapter. Phase 3 passed the same
native runner/worker against both services, real job cancellation/retention/fresh
retrieval, strict input validation, pinned cJSON compilation, shared evaluator,
missing-capability UNSUPPORTED and native parser rejection checks. The qualification
index records the actual revision/dirty state/source digest and deployment hashes.
The clean-source confirmation at e871ab2 is retained in docs/evidence/phase3-clean; b0f737a records it.

Native code lives in native/runner.c, worker.c, adapter_v1.h, common/, adapters/
and fixtures/. The Phase 2 spike is retained separately. Generic core files have
no service-name conditions. Service registration is outside core; typed facts
carry service-specific meaning from profiles/adapters to one Python evaluator.
There are no host deployment/report/replay product commands yet.

## Working lab

- Reuse /home/mignon/qnx800/qnxsdp-env.sh. No reinstall or credential recreation.
- Original $HOME/qnx-vm-resmgrcheck and prior logs remain preserved.
- Dedicated KVM VM .local/qnx-lab/run.qcow2 remains running; check existing SSH.
- ssh -F .local/ssh_config resmgrcheck-qnx; loopback-only 127.0.0.1:22220;
  StrictHostKeyChecking and existing keys. No host firewall/service changes.
- Native Phase 3 qualification used /data/resmgrcheck/p3gate1. Use fresh owned
  directories/run IDs for further tests and preserve completed bundles.
- Source environment, make qnx, then python3 tests/qnx/qualify-phase3.py --prefix
  UNIQUE for a manual-lab qualification. This helper is test orchestration, not
  Phase 7 application transport. It verifies all four uploaded artifacts by
  readback, runs real cases and rejections, and downloads the results.
- Build metadata includes source digest and binary hashes. Any relevant source
  change requires make qnx before profile expansion. Plan/CLI output files are
  created exclusively. Keep private/generated state ignored.
- QNX target: 8.0.0 / 2026/06/05-16:26:03EDT / x86pc x86_64, one CPU / 1 GiB.
  Recorded scheduling policy 2 / priority 10; no explicit priority boost. No
  server-monitor/slm in this image. Reinventory if the recipe changes.

## Phase 4 work already performed

Persistence/SSH-loss subgate E008 passed with actual QNX execution. --persist
launches a separate supervisor session only after exclusive /data/resmgrcheck/runs/
RUN_ID storage and initial status. Structured logs and stderr are separate; atomic
status contains identity, source/profile hashes, exact supervisor PID and unreaped
children. Reconnect/offline evaluation binds those records. Duplicate active or
completed run IDs are rejected without truncation. A real SSH-client termination
after pending state did not stop target cleanup or alter the planted service FAIL.
The normal persistent job passed. No native PID was killed by the host test helper.

Use tests/qnx/qualify-persistence.py --prefix UNIQUE after make qnx for this focused
manual-lab regression. Existing artifacts are in /data/resmgrcheck/p4gate2 and
/data/resmgrcheck/runs/p4gate2-{normal,disconnect}; preserve them. The Phase 3
qualification and 27 host tests remain passing. Current Phase 4 native claims use
the exact precommit source digest in the E008 index, not the parent commit alone.

A stored running status is not proof of liveness; never kill by a stale PID file or
blindly restart on transport uncertainty. The supervisor still owns/reaps its own
children internally. Complete collector status is not the service verdict.

## Phase 4 objective

Promote the observation collector to dependable supervision. Qualify normal,
stuck, crashed and unavailable workers/services, a blocked diagnostic probe,
malformed/lost producer evidence, transport interruption and cleanup failure.
Keep every service-facing call in a disposable worker. Preserve exact PID ownership,
wait/reap observations and the measured fixture-stop escape for reply-blocked
clients. Closing SSH or a successful kill is not proof of remote cleanup.

Keep case assertion failures alongside later execution/cleanup errors. Add persistent
run status and reconnect collection without blind duplicate starts. Stop dependent
cases when cleanup leaves contamination. The current single-case runner does not
establish those gates merely because it handles the planted ignored-unblock defect.
Use explicit lab test controls only when needed, label them in retained evidence,
and never present them as an external service defect. Continue autonomously after
passing gates, keeping records and coherent commits current.
