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
| control | Supervised worker only; hold/release/state into common counters plus typed facts; devctl errors returned directly |
| ordinary | Ordinary API baseline/health or optional negative diagnostic; preserve raw return, captured errno, API error, typed outcome/facts |
| prepare | Prepare installed-header messages, buffers and iovs in owned aligned storage before timer arming; no retained dispatch context |
| finish | Decode the reply after the generic worker's MsgSendv, retaining raw return/errno and normalization; reject malformed replies |

The core exclusively owns the timed send. After a logged absolute monotonic
deadline and successful TimerTimeout(send|reply|TIMER_ABSTIME), the next call is
MsgSendv on prepared buffers. No callback/logging/allocation/clock call intervenes.
Prepared native structures are not serialized as portable JSON.

Result types are OK/TIMEOUT/INTERRUPTED/API_ERROR/INVALID_REPLY. Facts are a bounded
array of named int32 values; core serialization has no job/sensor-specific fields.
Control facts and result facts are exact registered key sets in profiles. Native
pids/rcvids/timestamps use decimal JSON strings in observations.

Capabilities: pending, unblock, state, release, health, timeout, signal, departure,
error-probe. The last three do not imply supported scenarios merely by being known
IDs. Current services declare pending/unblock/state/release/health/timeout; only
the job adapter declares error-probe. Signal and departure are not yet qualified.
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
retrieves job_id=1/value=420. This is not yet the full client-departure suite.

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

External attach, multiple-job scheduling/consumption policies, dynamic adapters,
full signal/departure/repetition coverage and transport recovery remain later
scope. Adding a service with a different operation requires an adapter, registered
typed facts and real observation hooks; it is not automatically supported by a
new device path alone.
