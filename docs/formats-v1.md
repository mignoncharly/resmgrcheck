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
and `service_instance_id`. Expansion selects one explicit family required by the profile and attempt1,
aggregate cycle1. Repeat child events/results cover cycles1–20; all other plans
execute exactly one cycle. Run IDs must be unique within the owned lab; uncertain
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
| Capabilities | `{required, optional}` distinct bounded lists of known IDs; no overlap. Pending, state, release, health and the selected family capability are required for strict evaluation; repeat additionally requires timeout and ordering requires signal. require_unblock also requires unblock capability |
| Expectations | `{cancel_error, pending_after, require_unblock, health, state_after}`; ordering also requires distinct next_health; ETIMEDOUT for timeout/repeat, PROCESS_EXIT for departure, EINTR for signal/ordering; pending zero, boolean observer requirement, exact registered typed fact predicates |
| Timing | setup_ms, operation_ms, cancellation_ms, probe_ms, execution_ms, cleanup_ms; 100–5000 ms except execution up to 30000; execution must accommodate operation+cancellation+setup+probe bounds |
| Suite | `{required, optional, cycles, reset}`; required exactly one timeout/signal/departure/repeat/complete-first/cancel-first family; optional known signal/departure/repeat without overlap; repeat cycles1–20/reset same-instance, other expanded plans exactly1/reset new-instance; signal family also requires signal_mode |

Profiles cannot select fixture defects, shell commands, executable paths, scripts,
Python expressions or arbitrary operation IDs. Defect mode is a separate expanded
plan setting; it never relaxes the corrected-service contract. The supplied
profiles use the same 500/2000 ms timeout/allowance and 10 s case bound as Phase 2.

Repeat expansion supports1–20 cycles (reviewed default20); other multiple-cycle
requests are rejected at expansion rather than silently running one. Optional scenario
names do not imply those cases executed. External lifecycle becomes UNSUPPORTED before any process launch. External-health
uses external-attach, one cycle/external-unchanged reset, NOT_APPLICABLE cancellation
and explicit read-only public-state/health expectations.

## Expanded scenario plan (`kind: scenario-plan`)

Exact fields: kind/version; all five shared identity fields; `profile` snapshot;
`profile_sha256`; `suite_sha256`; `fixture_mode`; `builds`.

Snapshot hashes use ASCII JSON with sorted keys and compact separators. The suite
hash covers the exact suite subobject. fixture_mode is corrected (default), ignore-unblock, retain-waiter, retain-third,
duplicate-terminal, or job-only drop-job, checked against registration metadata. A plan changes neither profile expectations
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
fixture_mode; error_codes; recognized optional signal_codes.

`target` is exactly `{sysname, release, version, machine, scheduling_policy,
priority}`. These are captured with native uname/scheduling calls. Error codes
EOK, ETIMEDOUT, EINTR and ENOENT are captured from the QNX build. The host never
imports Linux errno numbers to evaluate QNX results. New manifests also declare
signal_codes {SIGUSR1: integer, SIGKILL: integer}, captured from the actual QNX header.
Signal evaluation requires its map; historical SIGUSR1-only or timeout manifests remain
readable. No Python/Linux signal-number substitution is permitted. Capabilities are the actual
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
loss. Legacy cases cap accepted producer frames at256; extended single cases at1024;
repeat at4096. Journal bounds are512/2048/8192 frames and2/4/8 MiB respectively.
The host accepts at most4096 records /32 MiB per stream. Overflow is ERROR.

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

New canonical assertions contain exactly `{id, verdict, reason, expected, observed, event_refs}`. Historical v1 triples `{id, verdict, event_refs}` remain readable.
Expected is a typed contract predicate; observed contains only supporting raw events
and, for status binding, the actual validated status. Missing evidence is not
filled with inferred private state. References are ordinal
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

## Phase 4 persistent supervision

`runner PLAN --persist` forks a dedicated session, closes the SSH standard streams
and acknowledges only after exclusive target storage and initial status succeed.
It uses `/data/resmgrcheck/runs/<run_id>/`, never a profile-supplied output path.
The run directory, events.jsonl and stderr.log are created exclusively with
no-follow opens; a repeated run ID is rejected without truncating earlier data.
Target operations and cleanup retain their own deadlines after the launch channel
closes. Startup failure/timeout is uncertain until the known run directory is
inspected; it does not authorize blind retry or PID-based cleanup.

New control record `kind: run-started`, schema 1: shared identity fields plus
supervisor_pid (decimal string). This acknowledges launch, not service PASS or an
independently observed exit status of the detached supervisor.

`kind: run-status`, schema 1, has exact fields: shared identities; supervisor_pid;
started_ns; state; cleanup_ok; exit_code; unresolved; profile_sha256;
source_tree_sha256; recognized optional pair event_file/lab_control. Current native
writers always include that pair. State is running/complete/incomplete/not-run. exit_code is -1 while
running and otherwise the collector's declared exit code. Each unresolved entry is
exactly `{pid, role}` (worker/fixture/manager). Status replacement uses a separate file,
file fsync and atomic rename. Complete status is published after event finalization.
No power-loss/disk-failure durability claim is made by the transport-loss test.

A status file is the last recorded observation, **not proof that its PID is still
alive or permission to signal that PID**. Internal cleanup still uses exact children
owned by the live supervisor. E009 qualifies contamination and sink containment.
`event_file` selects events.jsonl or recovery.jsonl; `lab_control` binds the explicit
qualification control to the stream. Neither field authorizes signalling a PID.

The event vocabulary adds supervisor `run_storage` with exact `{run_id}` payload.
Offline evaluate accepts `--status STATUS` to bind status identity, source/profile
hashes, supervisor PID and cleanup/finalization to the native stream. Its result
adds the recognized optional `status_sha256` (canonical status digest) and
`target_completion_status` assertion. Running, stale or inconsistent status makes
ERROR/incomplete even if a copied event stream otherwise passes. Existing FAIL
assertions remain visible. Complete collector status does not change a planted
service FAIL into PASS.

A real abrupt SSH-client termination after confirmed pending state, reconnect
collection and duplicate-start rejection passed in E008 and again in E009 after
the writer changed. A stalled VM or blocked filesystem may prevent target progress;
the host outer bound returns infrastructure ERROR and makes no remote cleanup claim.

Each child has its own nonblocking pipe, bound to its exact PID and producer role.
No partial bytes from different children are combined. The supervisor validates
canonical frames, registered field shapes, IDs, sequence and source time before
forwarding them. The generated native producer field table comes from the host
contract. Bounded invalid-frame diagnostics include size and up to 64 bytes in hex;
they are diagnostics, not accepted producer events.

The supervisor keeps at most 512 frames / 2 MiB in an in-memory journal, separate
from the 256 accepted child-event limit. A primary write failure does not exit the
supervisor or prevent owned-child cleanup. It records actual errno, continues the
journal, and seals recovery.jsonl through a reserved independent descriptor. That
stream preserves original observations and original written prefix. Recovery
evidence still yields ERROR for the lost primary sink. If both storage paths or
the journal fail, no complete conclusion is claimed; a stale/missing final status
also invalidates evaluation. This does not promise durability after power loss.

Supervisor events add lab_control, phase, problem, wait_bound, invalid_frame,
dependency and case_not_run with exact payloads in EVENT_FIELDS. Explicit lab
controls require --persist and never occur in profile expectations. --lab=CONTROL
selects a reviewed qualification fault. The full-storage control uses only the
isolated /data/resmgrcheck/phase4-full filesystem, prepared/exhausted by the test
helper; a real ENOSPC is required by the test. lab_discarded_wait records the
deliberately discarded wait observation in the ownership-loss experiment.

`--after=RUN_ID` requires persistent execution. A bounded, no-follow parse of that
specific predecessor status must establish clean completion before children launch.
Failed cleanup leaves the dependent case NOT_RUN/prior_cleanup_failed; missing or
untrusted completion yields NOT_RUN/predecessor_unestablished. No status-based PID
cleanup is attempted. The cleanup-failure control separately records lab recovery
in recovery.json after sealing original failure/status. That recovery uses only
children still owned by the same live parent and never rewrites the original case.

The evaluator retains a trustworthy prefix when later evidence is malformed or
truncated, preserving independent earlier FAIL assertions while returning ERROR.
No incomplete flow or required evidence loss can become PASS. Reason meanings are
documented in [reason-codes.md](reason-codes.md).

## Phase 5 explicit signal family

Profiles sensor-signal.json and job-signal.json use suite.required=[signal],
expected cancel_error EINTR and required signal capability. The suite adds the
exact signal_mode field: non-restart-no-retry is implemented; auto-restart is a
recognized UNSUPPORTED request. Unknown modes/keys, retry fields, mismatched case
IDs/errors and missing required signal observers are rejected. Plan case_id must
match its profile's one required family. Timeout profiles retain their prior shape
and ETIMEDOUT expectation; a signal profile does not relax those checks.

The worker records signal_setup (name, target number, configured flags, retry,
timeout_armed, queried masked bit and error), operation_armed, and after return
signal_handler_observed. The minimal handler only changes a sig_atomic_t flag;
these are ordinary-context events. The supervisor records trigger_requested with
owned child PID, signal and absolute completion bound, then signal_sent with the
actual syscall outcome. Pending must precede the trigger. Server-mediated unblock
can occur before the signal_sent log is written; source times and the pre-send
trigger marker determine conditions, not merged line order.

Signal evaluation requires SIGUSR1 bound to the native manifest, flags/retry/mask/
operation-timer all zero, successful send after matching pending, no timeout deadline
event, a live matching unblock, MsgSendv -1 with target EINTR, observed handler,
terminal ownership removal, post-state and original-instance fresh health. The
completion bound starts at the recorded signal request, not a kernel operation
timeout. A later unrelated error cannot satisfy EINTR. An absent handler while
ignored cancellation remains blocked does not by itself identify a root cause.
The original observed bound violation remains a service FAIL. E010 is the signal proof; E011 supplies the remaining native scenario gate.

Native process_exit adds exact child_pid, exited (0/1), exit_code (0–255) and signal
(0–255). Native wait macros populate it; raw reaped status is retained separately.
Historical successful zero-status records remain readable. New nonzero natural
worker exits require consistent worker-final/native exit facts. A recorded close
failure or nonzero exit is execution ERROR; it does not by itself mean evidence
was lost. Missing/inconsistent required observations still invalidate completeness.
Fixture interference invalidates transport-style baseline errors while preserving
independently returned forbidden payloads. E010 includes both native failure facts
and explicitly synthetic preservation/nonzero-exit checks.


## Phase 5 lifecycle and cycle records

Departure uses operation_armed with no timer, pending, trigger_requested(SIGKILL),
signal_sent, process_exit/native wait facts, reaped and departure_bound. The bound
has exact child_pid, completion_bound_ns and reaped flag. Successful signal_sent
alone cannot establish death. descriptor_duplicated/descriptor_closed identify
worker FD actions; request_ocb links logical/generation/client to fixture-local OCB
number. close_dup includes OCB/client/rcvid/synthetic; synthetic must exactly equal
(rcvid=="0"). close_dup_default and close_ocb_default record returned status;
close_ocb records final destruction entry. IDs are observations, never commands.

terminal_attempt records logical/generation/rcvid/action/rc/error separately from
successful removal. A rejected second call remains a duplicate attempt. Defect
retained_request is a logical tombstone without a live IPC or OCB reference.

Repeated aggregate results add exactly cycle_count and cycles. Each cycle record
is {cycle,verdict,reasons,completion,assertions}; ordered coverage must be exactly
1..cycle_count. A cycle PASS requires every mandatory condition PASS and complete.
Top-level repeat PASS additionally requires every cycle PASS. cycle_begin binds
cycle/fixture_pid/deadline; cycle_ready proves pending0 while retaining generation;
cycle_end records worker_pid/worker_reaped/pending/state_observed/clean/safe.
When state_observed==0, pending's numeric placeholder is **not** a state observation.
cycle_not_run records the requested cycle and contamination/incomplete reason.
Sequences remain global per producer PID across cycle changes. Worker frames must
match the cycle used at spawn; aggregate status/final cleanup remain cycle1.

Directed-order events include linked barrier_wait, ordering_stage, stale_checked
(live/matched), real parked/park_completed and unmatched/obsolete unblock records.
Typed fixture controls implement arm_complete/drain_stale/hold_next/park, never
supplied shell text, PIDs or rcvids. State/health still come from supervised workers.
A distinct next_health predicate is mandatory for ordering. Required barrier/start/
result timings establish the observed order; normal-result-before-trigger is also
required for complete-first. Missing evidence cannot be replaced by a delay.


## Phase 6 immutable run bundle

`run-bundle` schema1 is the final `bundle.json` marker. Exact fields are kind,
schema_version, bundle_id, the five shared identities, evaluator, files. evaluator
is {source_revision,dirty,source_tree_sha256}, separate from the native build's
source identity. files maps exactly these names to {sha256,bytes}:

- observations.jsonl (original immutable bytes)
- plan.json and status.json (original validated input bytes)
- profile.json, builds.json, target-manifest.json (validated snapshots)
- result.json (one canonical evaluator)
- replay.json (exact replay input)
- notes.txt (human-readable identity/outcome)

bundle_id is SHA256 of canonical marker content excluding bundle_id. File hashes
cover actual bytes. A new exclusive directory first gets partial.json. Raw inputs
are preserved before semantic validation. Finished files use a temporary same-
filesystem file, fsync and atomic replacement; the final marker follows complete
cross-validation. Collection failure retains a separate partial-run artifact and
no final marker. A sealed bundle can correctly contain FAIL, ERROR or UNSUPPORTED;
sealing is artifact finalization, never a service verdict. Members become read-only.
Integrity verification rejects missing, additional, symlinked, truncated, changed
or inconsistently bound members and rechecks canonical evaluation. Read-only mode
and hashes are not protection against a malicious owner/target or power-loss proof.
Reports are generated outside the source bundle.

`replay-input` schema1 retains original_plan, original_event_sha256 and
selected_builds. selected_builds must equal the original build; changing it silently
is invalid. Original plan snapshots profile/inputs, family order, cycles, timing,
triggers, reset policy and fixture setting. It contains no executable snippets or
live PIDs/receive IDs to execute. Runtime identifiers in observations stay evidence.
An explicit candidate-build document is a separate selected input to replay.

## Candidate build and attempts

`candidate-build` schema1 has exactly kind/schema_version/build_id/builds/adapter/
architecture/target_machine/directory/executables. ABI1, gcc_ntox86_64, architecture
x86_64 and machine x86pc are currently supported. directory is one reviewed
/data/resmgrcheck/NAME deployment; executable names are registered runner, worker
and fixture basenames in that directory. Adapter is statically part of worker.
build_id hashes {builds,adapter,architecture,target_machine}; deployment location
is resolved separately and target bytes must match every hash before launch.
Recipe/architecture/adapter incompatibility is rejected. No arbitrary command path
or string is accepted from profiles/replay files.

Replay requires --candidate-manifest even for a same-build selection. The tool
queries actual uname -p/-m, downloads/hashes deployed binaries, reserves one new
attempt directory and a fresh native run ID, then launches once. Attempt numbers
include original attempt1; all preflight failures/partial attempts remain recorded.
launch_requested and acknowledged are separate facts. Lost acknowledgement does
not prove absence of a target process and never authorizes an automatic relaunch.
Target PID observations never authorize host-side process killing. Lab fault
injection controls are explicitly not portable replay inputs.

Comparisons retain original/candidate bundle and build IDs, contract equality,
original/candidate reasons/failure obligations, new obligations and reproduction.
Labels: fixed, still-failing, newly-failing, still-passing, unsupported, incomparable,
incomplete. Different profile/expectations/settings or architecture are incomparable.
Any incomplete candidate remains incomplete, never fixed. Reproduction refers to
established original FAIL obligations, not merely any red result. Identical replay
inputs do not guarantee identical scheduler interleavings.

JUnit is a deterministic derived XML view serialized with ElementTree. Stable
suite/case/cycle names retain assertion details and bundle references. FAIL creates
failure, ERROR creates error, UNSUPPORTED/NOT_RUN creates skipped. Every current
expanded case is required; unavailable or incomplete coverage additionally creates
required-coverage/error, so an all-skipped suite cannot appear green. Optional
scenario names do not create executed optional cases or waive required coverage.

Execution CLI precedence is130 (interrupted),2 (input/environment/harness/evidence/
cleanup error),3 (required unavailable/NOT_RUN/no qualifying cases),1 (valid
completed contract FAIL),0 (complete required PASS). Offline bundle/inspect/junit/
compare return0 when valid failed evidence was successfully processed. Their
success never changes the recorded test result. Legacy native collector code4
still means withheld dependent execution; host test execution maps it to3.


## Phase 7 host/transport records

`config/targets.example.json` documents the strict local target schema. Unknown
keys and targets are rejected. Authentication remains in OpenSSH; records contain
routing/compatibility metadata, never secrets. See `transport.Target`.

`deployment.Deployment` validates `deployed-build` version1: full content-derived
identity, fixed destination, actual file SHA256/lengths, native source/build record,
independently bound management-helper identity, compatibility/recipe/UID and
per-adapter candidate manifests. `native/targetctl.c` uses protocol1 completed
publication/ownership markers. A manifest file alone cannot establish publication.

`workflow.Request` validates exact `execution-request` version1: root run ID,
target name, complete immutable deployment, ordered case plans and profile
snapshots. `suite-replay` points to that saved request and its digest; replay
requires an explicit candidate deployment manifest to change the selected build.
Persistent attempt ordinals include failed preflight attempts. Run IDs have a
bounded ASCII letter/digit/underscore/hyphen grammar; the root ID has at most40
characters to leave room for native family suffixes.

Remote session storage is `/data/resmgrcheck/sessions/RUN_ID`; native case storage
remains `/data/resmgrcheck/runs/CASE_RUN_ID`. Exclusive directories, UID/type/mode
checks and request/plan hashes establish their binding. Launch intent precedes the
single invocation. Acknowledged, status-observed and collected are separate facts.
`state.json` preserves uncertainty; `result.json` binds every required case to its
sealed bundle or explicit uncollected result. Collection history keeps old result,
state and partial raw bytes. It never supplies absent acknowledgements or launches
withheld cases. Deleted/archived target status is UNKNOWN, never a PASS.

All metadata is bounded and parsed through duplicate-key/type/field validation.
Actual SFTP hashes are required before native launch. Producer signal/termination
records must name ledger-owned children; fixture-stop must name a fixture role.
Saved PIDs are observations only and never authorize later cleanup.
