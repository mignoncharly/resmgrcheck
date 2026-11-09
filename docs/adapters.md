# Native adapter ABI 1

The public header is `native/adapter_v1.h`. A registration supplies ABI number,
struct size, adapter/operation IDs, fixture basename, capability mask, result/API
convention and typed fact key sets, plus callbacks. Unknown IDs or ABI/size mismatch
are rejected before service calls. No plugin is loaded from an arbitrary path.
Adapters are statically linked and registered in `native/adapters/registry.c`;
corresponding host validation data is in `resmgrcheck/registrations.py`.

The core runner and worker contain no service-name conditions. Both services use
the same runner/worker binary hashes, process/deadline logic, producer framing,
cleanup policy and Python evaluator. Fixture-specific state decoding and message
layouts live exclusively in adapter/fixture files.

## Callback ownership

| Callback | Contract |
| --- | --- |
| validate_parameters | Validate the exact registered bounded parameter object; no execution/expression parsing |
| control | Supervised worker only; ready/hold/release/state into common counters plus typed facts; ready performs the same real state query; devctl errors returned directly |
| ordinary | Ordinary API baseline/health or optional negative diagnostic; preserve raw return, captured errno, API error, typed outcome/facts |
| prepare | Prepare installed-header messages, buffers and iovs in owned aligned storage before timer arming; no retained dispatch context |
| finish | Decode the reply after the generic worker's MsgSendv, retaining raw return/errno and normalization; reject malformed replies |

The core exclusively owns timed and signal-driven sends. After a logged absolute monotonic
deadline and successful TimerTimeout(send|reply|TIMER_ABSTIME), the next call is
MsgSendv on prepared buffers. No callback/logging/allocation/clock call intervenes.
Prepared native structures are not serialized as portable JSON.

Result types are OK/TIMEOUT/INTERRUPTED/API_ERROR/INVALID_REPLY. Facts are a bounded
array of named int32 values; core serialization has no job/sensor-specific fields.
Control facts and result facts are exact registered key sets in profiles. Native
pids/rcvids/timestamps use decimal JSON strings in observations.

Capabilities: pending, unblock, state, release, health, timeout, signal, departure,
repeat, ordering, error-probe and external-health. Both reviewed adapters implement all six native
families (E011); only the job adapter supplies error-probe. Known capability names
alone never imply implemented/qualified coverage.
Missing required capabilities produce native preflight and host UNSUPPORTED,
with no service process launch. Absence of a pending observer cannot be replaced
with a delay or a long-looking call.

## Sensor integration

`native/adapters/sensor.c` implements sample with errno return convention. It
compares ordinary read with the installed _IO_READ structure/MsgSendv path, parses
a bounded `sample=<integer>\n` record and returns typed value. Existing sensor
control hooks normalize into pending/unblock/completion counters. The original
`native/fixtures/sensor.c` queue/default-handler behavior remains unchanged; a
compile-time observation writer switch emits v1 JSON for the generic path and
preserves the Phase 2 text spike. The shared clock helper does not change timer
placement. The supplied profile expects value 42 and no retained pending request.

## Job integration

Added files: `native/fixtures/job_protocol.h`, `native/fixtures/job.c`,
`native/adapters/job.c`, `profiles/job.json`; added registration entries and Make
targets outside core logic. No job-specific branch was added to runner, worker or
evaluator to execute or classify the second service.

The fixture owns one fixed lab job slot (ID 1), up to eight waiters, and a generation
for slot reuse. SUBMIT (generic hold) creates an incomplete job; COMPLETE (release)
marks it ready and replies to all current waiters. WAIT_RESULT validates request
length using actual message size/resmgr_msgread, job ID and reserved fields. A
nonexistent ID returns ENOENT. Completed results are **non-consuming**: subsequent
clients may retrieve them until explicit SUBMIT replaces the slot with a new
generation. Submitter process departure does not delete the fixture-owned job.

Waiter cancellation uses the same reviewed default-unblock/live-owner checks as
the sensor. It removes only the pending waiter. Job existence/readiness remains
observable separately. The profile requires job_exists=1 and job_ready=0 after
cancellation; generic release then completes that retained job and a fresh client
retrieves job_id=1/value=420. E011 also proves job survival after forced waiter departure.

The adapter's ordinary path uses devctl and interprets its returned error value,
not errno. Its timed path builds _IO_DEVCTL with installed io_devctl_t, separate
header/payload send iovs and a typed reply buffer; successful equivalence is
checked against ordinary devctl. MsgSendv status and reply ret_val/nbytes/reserved
fields are all checked. Negative probe of job ID 2 recorded actual raw return 2,
errno 0 and normalized ENOENT; timeout MsgSendv recorded -1/errno 260 ETIMEDOUT.

Both fixtures default to corrected behavior. ignore-unblock is a separate, explicit
lab defect, while profiles always declare the corrected contract. The evaluator
reports its service FAIL; a regression script expecting that failure does not
change the report to PASS.

## Build and qualify

Source the installed SDP environment and run `make qnx`. cJSON is pinned locally;
no build-time dependency download. The native build record ties source digest,
revision/dirty state and artifact hashes together. Validate/expand profiles with
the local host tools, upload runner/worker/selected fixture/plan through the known
SSH/SFTP route, and invoke `./runner PLAN > EVENTS.jsonl` inside the owned lab.
Evaluate downloaded events with the same host evaluator for both profiles. Use
fresh run IDs and output files. A meaningful adapter qualification requires real
QNX baselines, confirmed pending cancellation, post-state and new-client results,
plus negative/error/capability validation. See E007 for actual commands/artifacts.

Multiple-job scheduling/consumption policies and dynamic adapters remain later scope. Adding a service with a different operation requires an adapter, registered
typed facts and real observation hooks; it is not automatically supported by a
new device path alone.

Phase 4 keeps all readiness, operation, control, state and health callbacks in
disposable supervised workers. The supervisor calls no service operation itself.
One native execution path qualified both adapters in E009. Per-child framed
channels isolate malformed producers, and exact owned-process wait status remains
separate from service results. Original-instance health must precede fixture stop;
a restart/recovery publication invalidates that health conclusion.

Phase 5 signal profiles use the same prepared message and adapter finish callbacks.
The generic worker installs SIGUSR1 with flags 0, verifies its unblocked mask, and
calls MsgSendv without arming TimerTimeout or retrying. Both existing fixtures use
their current live-owned-unblock MsgError(-1) path; actual results were -1/errno 4
(EINTR) and handler flag seen. No fixture ERESTART path was introduced. See QNX's
[MsgError contract](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/m/msgerror.html)
and [sigaction flags](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/s/sigaction_struct.html).
E010 retains both normal results and specific ignored-unblock failures. The
job remains present after waiter cancellation and is completed/retrieved by a
fresh client without restarting the service. E011 separately establishes departure.


Phase 5 adds shared typed fixture control support in adapters/fixture_control.h
and fixtures/control_v1.h. The packet contains only bounded action/cycle fields.
Registered mode metadata permits reviewed defects without core service branches.
cycle changes producer identity after pending0 and does not reset service state.
arm_complete/drain_stale/hold_next/park provide explicit fixture ordering barriers.
All service calls remain in supervised workers. The ABI1 callback layout is stable;
capability bits repeat/ordering extend the existing mask.

The shared lifecycle fixture helper delegates every close_dup and final close_ocb
to iofunc defaults, retains only scalar OCB identity after delegation and clears
references before final free. Actual duplicated-FD and forced-departure callback
order was recorded on both services. QNX supplied nonzero close receive IDs in
these runs; synthetic-zero handling is guarded but not claimed as natively seen.
The fixture is single-threaded; multithread extensions need explicit serialization.


## Explicit external attachment (Phase 7)

`profiles/sensor-external.json` and `profiles/job-external.json` select registered
adapters, explicit lab device paths and `service.mode=external-attach`.
`run --suite health` requires external-health/state/health. Supervised workers open
O_RDONLY and record actual `fcntl(F_GETFL)` access mode, query public state, compare
ordinary/prepared results and open a fresh health connection. The supervisor never
opens the service. No fixture is launched or stopped; there is no hold, release,
submit, restart or reconfiguration. Product cleanup owns only its workers.

This diagnostic explicitly records `service_build_verified=0` and
`instance_verified=0`. It cannot establish original-instance survival or private
pending cleanup. Lifecycle remains UNSUPPORTED until an adapter supplies a
run-scoped pending/unblock observer feed. Changed-build external replay likewise
requires identification of the actual running service; selecting a local manifest
alone is insufficient. No diagnostic PASS replaces unavailable required coverage.

E013 separately owns real lab fixtures, confirms the same external PIDs remain
alive after attachment, then explicitly stops and observes reaping in its test
owner. That owner process is outside the product's ownership scope. The complete
host workflow is documented in [cli.md](cli.md).

## Worked job adapter checklist for another implementer

The second service was implemented and qualified by the project agent; no separate
external developer followed this guide. Use the following actual boundaries:

1. Define the service's fixed request/reply/state types in
   `native/fixtures/job_protocol.h`. Job1 is fixture-owned; completed results are
   non-consuming until SUBMIT. Distinguish jobs from waiters in public facts.
2. Implement `job_devctl` and `job_unblock` in `native/fixtures/job.c`, preserving
   `iofunc_*_default` delegation and live MsgInfo/owner checks. Include the shared
   `lifecycle.h` and `message_bounds.h` helpers. Validate exact current payload,
   declared size, actual reply capacity and access mode before state changes.
   Mutating commands need writable OCBs; public state/result retrieval needs read.
   Combined custom operations are outside this fixed protocol.
3. Implement validate_parameters/control/ordinary/prepare/finish in
   `native/adapters/job.c`. Prepare installed io_devctl_t and separate payload iovs
   before the core arms TimerTimeout. Preserve direct devctl errors independently
   of errno, and validate MsgSendv reply status/size/reserved fields and typed facts.
4. Register the static ABI1 instance in `native/adapters/registry.c` and its typed
   fact/capability/fixture/ordering metadata in `resmgrcheck/registrations.py`.
   Add the fixture target in Make and `profiles/job.json`; do not add branches for
   this service in runner/worker/scenario/evaluator. Schema changes need an explicit
   versioned contract review, not an arbitrary fact/string escape hatch.
5. Build with real qcc, validate the profile, deploy actual bytes with readback
   hashes and run fixed/defect profiles. Prove ordinary/prepared/deferred baselines,
   observed pending, cancellation, zero waiters, retained job, original-instance
   fresh retrieval and exact owned cleanup. Qualify departure,20 reconnect cycles
   and both directed orders through the same generic path. Missing observers are
   UNSUPPORTED, never a substitute health PASS.
6. Run `tests/qnx/qualify-input-bounds.py` with a fresh stage and the release suite.
   The focused input driver covers actual malformed/short/readonly rejection and
   unchanged state/fresh health; its test supervisor owns/reaps exact children.
   E015 records the clean current-source gate, qcc analysis and explicit limitations.

Neither dynamic loading, arbitrary raw messages, multiple-job scheduling nor
external lifecycle instrumentation is supplied by registering a name. An external
running-build identity mechanism is required for candidate verification there.

## Web/customer extension checkpoint W017

The original sensor/job sources and evidence are preserved. See [the versioned integration guide](web/ADAPTER_INTEGRATION.md) for static catalog validation, the additional retained-message mailbox protocol/adapter and exact qualification limits. W017 source has host checks; new QNX build/execution is still pending at that checkpoint. No general external lifecycle support is implied.
