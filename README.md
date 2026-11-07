# ResMgrCheck

A QNX 8.0 developer tool for testing cancellation and client-lifecycle contracts in resource managers.

The intended workflow exercises deferred I/O, records what happened on the QNX target, checks a declared service contract, and replays saved inputs after a fix. The complete execution specification is in [the ten-phase implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Current state

**Phases 1–6 have passed their native gates.** Both sensor and job fixtures use the
same generic QNX runner/worker and deterministic host evaluator. Phase 4 includes
the real crash/probe/channel/sink/full-storage/cleanup-contamination matrix and
SSH-loss recovery. Corrected cases PASS, explicit defects FAIL, infrastructure
faults ERROR and missing capabilities are UNSUPPORTED. See [status](docs/STATUS.md),
[formats](docs/formats-v1.md), [adapters](docs/adapters.md), [reason codes](docs/reason-codes.md)
and E009 in [evidence](docs/TEST_EVIDENCE.md).

Phase 5 completed all six native families on both services, including actual
forced departure/OCB lifetime, 20-cycle same-instance reconnect, and explicit
completion/cancellation ordering. Its 40-case regression preserves targeted FAILs,
infrastructure ERRORs and withheld NOT_RUN cycles. See the
[supported matrix](docs/supported-scenarios.md) and E011. Phase6 adds immutable bundles, explicit deployed-build replay, comparison and JUnit.
Both saved failures reproduced against their original builds and passed against
source-fixed candidates with changed hashes (E012). Product transport automation
remains Phase7. Host tools validate/expand, evaluate, bundle, inspect, replay and export. The
[Phase 2 guide](docs/phase2-native.md) remains a spike reference.

An operator has already built the smoke program with QNX's compiler and run it twice inside an x86_64 QNX 8.0 QEMU guest, with exit status zero both times. Those bootstrap results are recorded as operator-provided evidence, separately from validation of this repository checkout. See [test evidence](docs/TEST_EVIDENCE.md).

## Continue implementation

The implementing agent should read:

1. [AGENTS.md](AGENTS.md)
2. [Current status](docs/STATUS.md)
3. [Agent handoff](docs/AGENT_HANDOFF.md)
4. [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

Continue the current phase from status/handoff, respecting each gate in order. The approved plan defines the gates and scope.

## Build the native tools

On a Linux development host with an installed, locally licensed QNX SDP 8.0:

```bash
source "$HOME/qnx800/qnxsdp-env.sh"
make check-qnx
make qnx
```

Outputs in build/qnx-x86_64 include runner, worker and both fixtures, plus the
retained smoke/reference tools. They are QNX executables and must run on the QNX
target. See [QNX setup](docs/setup-qnx.md) and the current handoff for the qualified
manual SSH/SFTP lab route.

## Scope and evidence

A passing scenario will establish only the declared behavior under the recorded test conditions. QEMU results do not establish a hardware worst-case execution time or safety certification. See [architecture](docs/architecture.md) and [known limitations](docs/KNOWN_LIMITATIONS.md).

Original project code is licensed under the [MIT License](LICENSE). QNX SDK files, runtime images, license material, credentials, and generated binaries are not part of this repository.

