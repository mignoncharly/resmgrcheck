# Submission draft: ResMgrCheck

Category: Developer Tooling & Host Tools.

## One-line description

Know what cancellation left behind: test QNX resource-manager lifecycle contracts,
inspect native evidence, and replay the same inputs against an identified source fix.

## Problem

A timed call returning the expected error does not establish that a service released
its pending client state or can serve the next client. A departing waiter can also
leave work that legitimately belongs to the service. Those distinctions are easy
to lose when debugging a resource manager with ad hoc client scripts.

The intended user is a QNX developer implementing a service that defers requests:
for example, a sensor reader or a service-owned job queue. The useful development
question is whether the next client can still use the same service after a timeout,
signal or departing client. This project provides recorded behavioral evidence;
it does not establish safety certification or hardware worst-case timing.

## What it does

ResMgrCheck runs service-facing operations in supervised QNX workers, records actual
pending/trigger/result/state/health/cleanup observations and evaluates a declared
contract. It exercises normal baselines, timeout, non-restart signal interruption,
exact-worker departure,20 same-instance reconnect cycles and directed completion/
cancellation orders. Missing required evidence/capabilities cannot become PASS.

A Python standard-library CLI validates, deploys immutable readback-hashed bundles,
starts and recovers exact run IDs, replays saved inputs, compares candidate builds,
and exports JSON/JUnit and offline HTML. SSH loss preserves uncertainty and partial
evidence instead of creating a duplicate run. Reports show expectations beside
observations and link to actual target events.

## Implementation and QNX connection

The C11 native runner delegates every blocking service operation/probe to an owned
worker. The sensor and job services share the same generic runner/worker, adapter
ABI and evaluator. QNX TimerTimeout, MsgSendv, resource-manager default handlers,
live MsgInfo unblock ownership and real devctl/_IO_DEVCTL return semantics are
central to the implementation. See qnx-evidence-map.md for concrete source and proof.

The native tools build with real qcc gcc_ntox86_64 and run in an owned QNX8.0.0
x86_64/x86pc KVM guest. Phases1–9 include actual native failure/cleanup/recovery gates,
a clean-source/reused-target workflow, both-service source-corrected replay and an
expected-outcome release checker. Its12 PASS/19 FAIL/2 ERROR/3 UNSUPPORTED results
remain individual outcomes even when the checker itself succeeds.

## Demonstration and reproduction

The demo labels its intentional fixture defect, confirms native evidence, shows
an actual handler source correction and replays the unchanged contract/settings.
The second job example proves retained jobs are distinct from leaked waiters.
README, docs/codelab.md, docs/adapters.md and the committed evidence provide exact
commands and build identities. The local video and its manifest are reviewable;
its public YouTube URL must be supplied after authorized upload.

## Scope

This is a developer lab tool with two qualified adapters, not universal driver
support, exhaustive concurrency, memory-leak measurement or hardware timing/safety
certification. External attachment is scoped read-only health with unverified
running-build/instance identity; full external lifecycle remains unsupported without
instrumentation. Target startup, licensed SDK and existing SSH authentication are
manual prerequisites. No proprietary SDK/image/binary or credential is redistributed.

## Try it and assess the scope

The public evidence explorer is https://qnx-resmgrcheck.gestionatech.de/demo/.
It shows genuine saved observations without an SDK or account and cannot launch
private-lab work. The CLI and offline reports remain usable without the web service.
The fresh-lab guide creates your own image and trust configuration, then the codelab
walks through the actual source correction. Independent developer feedback and
arbitrary external-service lifecycle integration are still pending.

QNX's existing server-monitor detects unresolved unblock requests and can take
configured actions. ResMgrCheck complements that operational mechanism with
declared service contracts, directed lifecycle tests, post-state and next-client
checks, evidence export and identified-source replay. No first/only-tool claim is made.

## Submission fields still owned by the operator

The existing repository is https://github.com/mignoncharly/resmgrcheck. Publication
of the completed candidate branch and license detection at that public revision
must be verified. Video and codelab URLs remain pending until they exist publicly.
Entrant/team details and eligibility/ownership attestations are not inferred.
No public upload, push or submission was performed by preparing this draft.
