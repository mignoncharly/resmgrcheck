# ResMgrCheck

A QNX 8.0 developer tool for testing cancellation and client-lifecycle contracts in resource managers.

The intended workflow exercises deferred I/O, records what happened on the QNX target, checks a declared service contract, and replays saved inputs after a fix. The complete execution specification is in [the ten-phase implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Current state

**Phases 1 and 2 have passed their native gates.** The repository smoke program builds with qcc, transfers through SSH/SFTP, and ran twice on QNX with exit zero. The deferred sensor cancellation slice distinguishes an explicit ignored-unblock defect from corrected handling, with two real before/after replays and observed cleanup. See [current status](docs/STATUS.md) and E005/E006 in [test evidence](docs/TEST_EVIDENCE.md).

The native fixture, disposable clients and independent supervisor are a Phase 2 spike. Versioned adapters, the second service, complete lifecycle suite, host evaluator, CLI and reports remain planned work. Use the [native reproduction guide](docs/phase2-native.md) to run the current slice; the intentional defect remains a FAIL in its evidence.

An operator has already built the smoke program with QNX's compiler and run it twice inside an x86_64 QNX 8.0 QEMU guest, with exit status zero both times. Those bootstrap results are recorded as operator-provided evidence, separately from validation of this repository checkout. See [test evidence](docs/TEST_EVIDENCE.md).

## Continue implementation

The implementing agent should read:

1. [AGENTS.md](AGENTS.md)
2. [Current status](docs/STATUS.md)
3. [Agent handoff](docs/AGENT_HANDOFF.md)
4. [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

Finish the remaining Phase 1 gates, then continue through Phases 2-10 in order. The approved plan defines the gates and scope.

## Build the current smoke program

On a Linux development host with an installed, locally licensed QNX SDP 8.0:

```bash
source "$HOME/qnx800/qnxsdp-env.sh"
make check-qnx
make qnx
```

The output is `build/qnx-x86_64/hello`. It is a QNX executable and must be executed on the QNX target. See [QNX setup](docs/setup-qnx.md) for the image recipe and the remaining transport work.

## Scope and evidence

A passing scenario will establish only the declared behavior under the recorded test conditions. QEMU results do not establish a hardware worst-case execution time or safety certification. See [architecture](docs/architecture.md) and [known limitations](docs/KNOWN_LIMITATIONS.md).

Original project code is licensed under the [MIT License](LICENSE). QNX SDK files, runtime images, license material, credentials, and generated binaries are not part of this repository.

