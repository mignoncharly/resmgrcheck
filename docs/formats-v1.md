# Version 1 contracts

The executable contracts are the typed records and explicit validators in
`resmgrcheck/contracts.py`, with native command checks in `native/common/plan.c`.
There is no general schema engine, expression evaluator or command language.
Unknown fields, kinds, schema versions, adapter ABIs and registered operations are
rejected. Field names and lookups are case-sensitive.

## Shared bounds and identities

Each document has `kind` and integer `schema_version: 1`. JSON input is at most
1 MiB with nesting at most 12. Duplicate object keys, trailing data, NULs,
non-ASCII strings, floats/non-finite numbers, integers outside int64, and wrong
contextual types/ranges are errors. A JSON boolean is not an integer. Identifiers
are 1–64 ASCII letters/digits/underscore/hyphen, starting with a letter or digit.
SHA256 is exactly 64 lowercase hex digits; a source revision is 40 lowercase hex.

Run-bound documents/events share `run_id`, `case_id`, `attempt_id`, `cycle` (1–200),
and `service_instance_id`. The first expansion currently selects one timeout
case, attempt1, cycle1. Run IDs must be unique within the owned lab; uncertain
transport does not authorize starting another copy. Phase 4 owns persistent
reconnection/contamination handling.

Nanoseconds and opaque native identifiers (including pids and rcvids) are canonical
nonnegative **decimal strings**, at most int64. They are not JSON floating-point
numbers. Logical request and generation IDs are decimal strings too. Millisecond
bounds and small counters are JSON integers. Never subtract host wall time from
target CLOCK_MONOTONIC values or infer occurrence order merely from line order.

Native command files use the narrower canonical ASCII subset produced by the
host: no escaped strings and integral decimal numbers. They may contain formatting
whitespace. cJSON serialization/compact-input comparison rejects permissive number
syntax; full consumption, duplicate and context checks still apply. cJSON is not
trusted to enforce application types by itself.

## Profile (`kind: profile`)

Exact top-level fields: `kind`, `schema_version`, `id`, `version`, `adapter`,
`service`, `operation`, `capabilities`, `expectations`, `timing`, `suite`.

| Group | Exact fields / meaning |
| --- | --- |
| Identity | id; version integer 1–1000000; adapter `{id, abi}` selects a compiled registration, ABI 1 |
| Service | `{mode, device}`; mode managed-fixture or external-attach; device is a single `/dev/resmgrcheck-...` lab pathname component, bounded to 96 suffix characters |
| Operation | `{id, parameters, result_shape, convention}`; all service-specific fields are checked against the registration; result shape is integer-record; convention is errno or devctl |
| Capabilities | `{required, optional}` distinct bounded lists of known IDs; no overlap. Pending, state, health and timeout are required for strict timeout evaluation. require_unblock also requires unblock capability |
| Expectations | `{cancel_error, pending_after, require_unblock, health, state_after}`; ETIMEDOUT, pending zero, boolean observer requirement, exact registered typed fact predicates |
| Timing | setup_ms, operation_ms, cancellation_ms, probe_ms, execution_ms, cleanup_ms; 100–5000 ms except execution up to 30000; execution must accommodate operation+cancellation+setup+probe bounds |
| Suite | `{required, optional, cycles, reset}`; required timeout; optional known later scenarios signal/departure/repeat; cycles 1–200; reset new-instance |

Profiles cannot select fixture defects, shell commands, executable paths, scripts,
Python expressions or arbitrary operation IDs. Defect mode is a separate expanded
plan setting; it never relaxes the corrected-service contract. The supplied
profiles use the same 500/2000 ms timeout/allowance and 10 s case bound as Phase 2.

Current expansion supports only one timeout cycle; a profile requesting multiple
cycles is rejected at expansion rather than silently running one. Optional scenario
names do not imply those cases executed. External attach is validated as a mode
but currently becomes UNSUPPORTED before any process launch.

## Expanded scenario plan (`kind: scenario-plan`)

Exact fields: kind/version; all five shared identity fields; `profile` snapshot;
`profile_sha256`; `suite_sha256`; `fixture_mode`; `builds`.

Snapshot hashes use ASCII JSON with sorted keys and compact separators. The suite
hash covers the exact suite subobject. fixture_mode is corrected (default) or the
explicit ignore-unblock regression. A plan changes neither profile expectations
nor the evaluator when selecting a defect.

`builds` is exactly `{source_revision, dirty, source_tree_sha256,
compiler_variant, recipe_id, binaries}`. dirty is a JSON boolean. Variant is
currently gcc_ntox86_64. The source-tree hash covers project C/headers, Python
runtime/build scripts, vendored cJSON C/headers and Makefile. recipe_id currently
identifies the qualified IFS by its SHA256. binaries contains SHA256 entries for
runner, worker, fixture and adapter (the statically linked worker artifact contains
the adapter). Build records are produced by Make only after successful native
prerequisites. Expansion rejects stale source/binary hashes. Documentation-only
edits do not change the source digest.

The guest checks command syntax/types and consumes these identity declarations;
they are not guest cryptographic attestation. The host validates snapshot hashes
before expansion and again during evaluation. Qualification uses SFTP readback to
associate declared deployment hashes with the actual transferred artifacts.

Commands remain typed roles interpreted by the generic worker, not shell strings.
The managed runtime device is profile.device + '-' + service_instance_id. Identity
and time bounds propagate unchanged to producers. The same native runner/worker
binaries execute every registration.

## Target run manifest (`kind: target-run-manifest`)

The native supervisor writes exactly one manifest as the first NDJSON record.
Exact fields: kind/version; shared identities; tool_version; adapter_id;
adapter_abi; capabilities; profile_sha256; suite_sha256; builds; target;
fixture_mode; error_codes.

`target` is exactly `{sysname, release, version, machine, scheduling_policy,
priority}`. These are captured with native uname/scheduling calls. Error codes
EOK, ETIMEDOUT, EINTR and ENOENT are captured from the QNX build. The host never
imports Linux errno numbers to evaluate QNX results. Capabilities are the actual
compiled registration's declarations, not a copy of the requested list.

A missing required capability produces an explicit unsupported event, no child
launch, verified cleanup/final markers, and host UNSUPPORTED. It cannot produce
PASS. Invalid manifests, missing markers or inconsistent identities produce ERROR.

## Producer event (`kind: producer-event`)

Exact fields: kind/version; shared identities; `producer`, `pid`, `seq`, `ns`,
`event`, `data`. producer is fixture/worker/supervisor; pid is a decimal string;
seq starts at 1 and increases by one per producer process; ns is the source's
CLOCK_MONOTONIC observation timestamp. Sequence gaps, decreasing source time,
wrong producer roles, duplicate fields and cross-run events invalidate evidence.

The supervisor is the sole final stream writer. Producers write nonblocking
atomic frames into a bounded pipe. A frame is at most 16 KiB by contract and at
most the installed QNX PIPE_BUF (5120) in this implementation. Oversize/full-pipe/
write/allocation errors are visible failures (producer exit 120), never silent
loss. This runner caps one case at 256 collected producer frames; overflow is an
evidence error. The host accepts at most 2048 records / 32 MiB per stream.

Every event has an exact payload shape and permitted producer in EVENT_FIELDS /
EVENT_PRODUCERS. Important payloads:

| Event | Required data |
| --- | --- |
| received/pending | logical/generation/rcvid/client_pid strings; pending also has pending count |
| unblock | matching logical/generation/rcvid, live flag, visible fixture mode; timestamp is handler observation, not exact timer expiry |
| deadline | operation, deadline_ns string, timeout_ms |
| result | operation, api, raw_return, raw_errno, api_error, normalized, error_name, result_shape, facts |
| control_result | operation, error, pending/unblocks/completed counters, generation string, typed facts |
| cancel_completed/removed | original request identity, terminal reply outcome / pending count and reason |
| operation_bound | absolute completion_bound_ns, expired/result_observed/worker_reaped flags |
| spawned/reaped/signal_sent | exact child PID, role/binary or raw wait status or signal result/error |
| cleanup | all_reaped and evidence_error flags |
| run_final | flow_complete, cleanup_ok, evidence_error flags |

Other exact event payloads are defined in the validator, including readiness,
close/final worker markers, stage/state transitions, evidence/execute errors and
unsupported declarations. No arbitrary payload is accepted simply because its
outer object is JSON.

Operation result conventions:

- read and MsgSendv: raw -1 uses captured errno; successful return is byte count
  for _IO_READ and status zero for _IO_DEVCTL.
- devctl: the raw return is the error value directly; captured errno is an
  independent observation. Real job negative probe: raw_return=2, raw_errno=0,
  api_error=2, normalized=API_ERROR / ENOENT.
- normalized is OK, TIMEOUT, INTERRUPTED, API_ERROR or INVALID_REPLY. Success facts
  are bounded int32 key/value records supplied by adapters. The evaluator checks
  their exact predicates against the profile.

A final marker is writer termination, not a service pass. The native collector
returns zero for a fully collected deliberate service failure; only the host
shared evaluator issues the service verdict.

## Evaluated result (`kind: evaluated-result`)

Exact fields: kind/version; shared identities; fixture_mode; verdict; reasons;
completion; assertions; profile_sha256; event_sha256 (hash of original stream
bytes). Verdict is PASS/FAIL/ERROR/UNSUPPORTED/NOT_RUN. Completion is separate:
complete/incomplete/aborted.

Assertions contain exactly `{id, verdict, event_refs}`. References are ordinal
record indices in the original stream (manifest index 0). A PASS requires every
mandatory baseline, pending, cancellation, terminal reply, state, health, cleanup
and completeness obligation, with all assertions PASS. Missing evidence cannot
become success. A confirmed pending request/live trigger with completion absent
past the original bound is FAIL; an unestablished precondition is ERROR.

The evaluator checks source timestamps, request/generation ownership, API return
conventions, state release, registered typed facts and fresh-client health before
stopping the original fixture. Cleanup/error facts remain assertions alongside
already established contract failures. Overall ERROR takes precedence when
execution/evidence is compromised; underlying FAIL assertions are retained.
Dependent health can be NOT_RUN after a proven stalled operation without erasing
that failure. Defect mode stays explicit and does not change verdict rules.

## Replay input (`kind: replay-input`)

Exact fields: kind/version; original_plan; original_event_sha256; selected_builds.
The original plan is fully validated and retains the exact profile/suite/settings.
The new build selection is explicit, independently validated build metadata. This
contract exists now; product replay/comparison/deployment commands are later phases.
The Phase 3 CLI supports only validate, plan and offline evaluate.

## Local tools

`python3 -m resmgrcheck validate profiles/job.json` validates before target work.
`plan ... --run-id ID --output NEW_FILE` expands against current build metadata.
`evaluate PLAN EVENTS --output NEW_FILE` performs offline shared evaluation; exit
codes are PASS=0, FAIL=1, ERROR=2, UNSUPPORTED=3, NOT_RUN=4. Output files are created
exclusively, preserving prior records. No command here connects to a target or
executes a profile-supplied program. Deployment remains the qualified manual SSH
route until Phase 7.
