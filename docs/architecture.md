# Architecture and scope

## Purpose

ResMgrCheck will detect, explain, and replay cancellation and client-lifecycle failures in QNX 8.0 resource managers. The initial services retain requests while waiting for a sample or a job result. The tool checks declared obligations under recorded conditions; it does not certify an arbitrary service as defect-free.

The [implementation plan](IMPLEMENTATION_PLAN.md) is the execution specification. This repository is currently at Phase 1. The components below describe the planned design, not completed functionality.

## Execution model

| Component | Responsibility |
| --- | --- |
| Host application | Validate inputs, deploy through the tested OpenSSH route, apply an outer transport deadline, collect evidence, and evaluate it |
| QNX supervisor | Own launched test processes, observe progress and deadlines, preserve events, and perform bounded cleanup |
| Disposable client worker | Execute operations that may block, including probes and the operation under test |
| Service adapter | Translate a service's operations and observations into the common runner interface |
| Sensor and job fixtures | Provide real QNX resource-manager behavior, including explicitly selected defect modes |
| Host evaluator | Produce consistent verdicts for JSON, JUnit, replay comparisons, and the offline HTML report |

The supervisor must remain independent of blocking service calls. Pending-state observation is a prerequisite for cancellation claims. An incomplete event stream, uncertain precondition, or failed transport must remain an explicit error rather than become a passing result.

Managed-fixture mode owns only the processes it launches. Attaching to another service does not authorize stopping, restarting, or reconfiguring it.

## Technical choices

Native code uses C11 with required QNX extensions and the installed `gcc_ntox86_64` variant through `qcc`. Make owns the native build. The host implementation uses Python 3.10 or newer and its standard library. cJSON is to be pinned and vendored in Phase 3. No cloud service, database, desktop wrapper, or LLM component is planned.

Source, profiles, recipes, and reviewed evidence belong in version control. Generated binaries, run output, VM images, licensed SDK/runtime content, and private local configuration remain outside it or in ignored directories.

## Current boundary

Phases 1–3 passed with actual QNX execution. The sensor and job fixtures use the
same generic native runner/worker, registered adapter ABI and one deterministic
Python evaluator. Strict versioned contracts, pinned cJSON, typed facts, missing-
capability UNSUPPORTED and native parser rejections are qualified in E007. The
Phase 2 text/C-classified slice is retained separately as a spike reference.

Phase 4 is in progress. Explicit --persist launches have exclusive target storage,
separate sessions/logs, atomic status, reconnect binding and duplicate guards. The
real SSH-loss subgate passed in E008, preserving the deliberate service FAIL and
observed child cleanup. The full crash/probe/channel/sink/contamination matrix is
still open; persistent status is never PID cleanup authority or service PASS.
Complete lifecycle suites, replay, deployment CLI and reports remain later gates.
