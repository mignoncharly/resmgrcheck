# Architecture and scope

## Purpose

ResMgrCheck will detect, explain, and replay cancellation and client-lifecycle failures in QNX 8.0 resource managers. The initial services retain requests while waiting for a sample or a job result. The tool checks declared obligations under recorded conditions; it does not certify an arbitrary service as defect-free.

The [implementation plan](IMPLEMENTATION_PLAN.md) is the execution specification. Phases1–6 are qualified; the remaining host workflow/interface/distribution components follow their ordered gates.

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

Native code uses C11 with required QNX extensions and the installed `gcc_ntox86_64` variant through `qcc`. Make owns the native build. The host implementation uses Python 3.10 or newer and its standard library. cJSON is pinned and vendored with reviewed revision/license metadata. No cloud service, database, desktop wrapper, or LLM component is planned.

Source, profiles, recipes, and reviewed evidence belong in version control. Generated binaries, run output, VM images, licensed SDK/runtime content, and private local configuration remain outside it or in ignored directories.

## Current boundary

Phases1–6 passed with actual QNX execution. Both services use one generic native
runner/worker and registered adapters. The supervisor owns exact processes and
framed channels; every potentially blocking service operation/probe stays in a
worker. Native persistence survives tested SSH loss and retains cleanup facts.

Phase5 adds six scenario families,20-cycle same-instance reconnect and directed
barriers; defects and infrastructure errors stay distinct. Phase6 seals raw bundles,
validates replay/candidate identities, checks deployed binaries, preserves attempts,
and derives comparison/JUnit through one canonical evaluator. Host evaluator source
identity and native build identity are separate. Full host target/deployment/
collection commands, HTML interaction and distribution remain later phases.

The feature/production-web-ai control plane is documented separately in
[web/ARCHITECTURE.md](web/ARCHITECTURE.md). It preserves this native/CLI architecture
and canonical evaluator. The approved web access model uses only locally provisioned
administrator password/MFA identities and scoped developer access-code sessions,
without signup/email/SMTP. Its staging and production gates are tracked separately
in [web/STATUS.md](web/STATUS.md); web work does not requalify arbitrary QNX services.
