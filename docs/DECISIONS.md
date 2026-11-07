# Decisions

## D001: Keep the approved project scope

**Date:** 2026-11-06. **State:** accepted execution specification.

ResMgrCheck tests cancellation and client-lifecycle obligations in QNX resource managers that retain pending requests. Follow the unchanged [ten-phase plan](IMPLEMENTATION_PLAN.md). First prove one actual cancellation defect and its correction, then expand the runner and developer workflow. Do not add a cloud service, database, frontend framework, LLM verdict engine, or unrelated platform support.

## D002: Continue on the working Linux host

**Date:** 2026-11-06. **State:** supported by operator bootstrap evidence.

Use the existing Ubuntu 24.04.3 x86_64 host, licensed QNX SDP environment, and QEMU/KVM target. The new repository is the implementation starting point. Windows migration is outside this work.

Use one virtual CPU and 1 GiB of guest RAM for the initial lab recipe. KVM access depends on the groups of the process starting QEMU; an agent must check its own session rather than infer access from a different shell's successful probe.

## D003: Treat the console route as bootstrap transport

**Date:** 2026-11-06. **State:** temporary bootstrap choice.

The smoke executable was included in the image at `/proc/boot/hello-qnx` and run through the serial console. Guest networking was disabled. This established real execution without a target file-transfer service.

The planned product transport remains system OpenSSH with a tested file-transfer mechanism. Complete that basic route during Phase 1, using local credentials, host-key verification, and a lab connection limited to the host. Full deployment and run-management commands remain later work. `--ssh-ident=none` omits identity configuration; it is not a switch that disables guest networking or sshd.

## D004: Preserve the source of every native claim

**Date:** 2026-11-06. **State:** active evidence rule.

The successful bootstrap runs are operator-provided terminal evidence. They do not validate a new repository commit automatically. Record a fresh repository build/run checkpoint with its source revision and artifact identity. Do not reconstruct an invented transcript or label host-only checks as QNX execution.

The catalog baseline `com.qnx.qnx800/8.0.0.00141T202311271501L` identifies the selected root package. It does not identify every installed SDK component or prove a particular whole-SDK patch level. Record observed package and target versions separately.

## D005: Use the planned small toolchain

**Date:** 2026-11-06. **State:** accepted execution specification.

Use C11 with required QNX extensions, `qcc`, and a small Make build for native code. Use Python 3.10 or newer and its standard library for the host application. Pin and vendor cJSON with its license when Phase 3 requires it. Original project code uses MIT licensing by default.

Publish original source and reproduction instructions. Keep SDK contents, proprietary runtime images, credentials, license material, and machine-local authenticated configuration outside the repository.

## D006: Diagnose execution restrictions before changing the SDK

**Date:** 2026-11-06. **State:** observed blocker; see E002–E004.

The current agent context mounts the installed QNX license directory and Git metadata read-only and prohibits socket creation. The actual compiler failed to acquire its license lock. Preserve the working SDK and credentials; resume with authorized access to those normal operations instead of reinstalling or copying license data. A metadata-only Make preflight now explains the build blocker promptly. It does not validate a license or establish native execution.

Inspect the operator image through a copy and explicit writable qcow2 overlay. This worked under TCG without modifying the original image or log. Absence of `server-monitor`/`slm` in this run is evidence about this image only. Missing `sshd-auth` and an SSH startup memory fault remain unresolved; do not claim a tested transport until actual authentication and transfer pass.

## D007: Qualify a dedicated KVM/SSH lab with existing identities

**Date:** 2026-11-06. **State:** verified in E005; supersedes D006's active blocker.

Full Access restored normal license-lock/Git writes and sockets. The SDK compiled normally without reinstallation. Apply the account's existing kvm membership using `sg kvm`; preserve host services and original images. Build a dedicated ignored image that includes `sshd-auth` and runtime helper links. Reuse existing client and bootstrap host keys locally, pin the public host key to the exact loopback port, and use strict verification and restricted user-mode forwarding. SSH commands and SFTP round-trip transfer passed. The old TCG fault was not reproduced; TCG remains unqualified.

Phase 1's compiled capability probe establishes availability of the needed primitives, not deferred-I/O cancellation correctness. That proof remains Phase 2.

## D008: Preserve server-mediated cancellation and its measured cleanup escape

**Date:** 2026-11-06. **State:** verified in E006.

Use the installed `_IO_READ` structure and MsgSendv for the timed read; ordinary read and this message path returned the same sample. Arm an absolute monotonic send/reply timeout directly before the send. Check source-stamped pending/unblock ownership before classifying completion. Corrected handling delegates default bookkeeping and uses MsgError(rcvid, -1) only for a current owned unblock. The recorded QNX ETIMEDOUT value is 260; do not import Linux error-number assumptions.

The client remained unreaped after termination signals while the deliberate ignore-unblock fixture retained its read. Stopping the owned fixture released it. Therefore cleanup must independently track exact children, record escalation and fixture intervention, and wait for actual reaping. A successful kill call alone is not a cleanup result. The Phase 2 C classifier/text stream is a native spike; the versioned adapter and deterministic host evaluator remain Phase 3 work.

## D009: Versioned bounded contracts and pinned cJSON

**Date:** 2026-11-06. **State:** Phase 3 verified in E007.

Use explicit v1 dataclasses/validators rather than a schema engine or expression
language. Snapshot hashes bind the profile/suite; defect mode remains a separate
plan field and never changes expected corrected behavior. Require typed facts,
source-stamped events, exact producer sequences and final/cleanup evidence. Actual
QNX errno codes are recorded by the native manifest; Linux errno values are not
substituted.

Pin cJSON 1.7.19 to c859b25da02955fef659d658b8f324b5cde87be3 (official
[release](https://github.com/DaveGamble/cJSON/releases/tag/v1.7.19)); preserve its
license and exact file hashes. Review scope/caveats are in third_party/cjson/REVIEW.md.
The QNX toolchain requires libm for this build. Use bounded full-consumption parse,
case-sensitive lookup, duplicate checks, depth 12 and the host-produced canonical
ASCII command subset. This is not an upstream security audit or cryptographic
attestation by the guest. Qualification verifies actual deployment by SFTP readback.

## D010: Reuse the execution core through typed adapters

**Date:** 2026-11-06. **State:** two-service QNX proof passed in E007.

Adapters own service message preparation/decoding and control/state facts; the core
owns every timed send, process, wait and cleanup. Fact serialization is generic.
Registration is outside runner/evaluator. The same runner/worker hashes qualified
both services without a service-name branch in core files.

The job fixture owns one lab job slot separately from its eight possible waiters.
Cancellation removes a waiter, not the job. Results remain readable until explicit
resubmission; completion after cancellation and fresh-client retrieval were tested.
Ordinary devctl error return 2/errno 0 and _IO_DEVCTL MsgSendv timeout -1/errno 260
were recorded independently. Do not normalize devctl as an errno-style API.

The Phase 3 native path is an observation collector, not a second verdict engine.
All service verdicts come from one host evaluator. A fully collected planted
failure can have native exit zero and host FAIL; missing capabilities have native
preflight exit 3 and host UNSUPPORTED. Required evidence loss remains ERROR.

## D011: Persist before acknowledging a detached run

**Date:** 2026-11-06. **State:** Phase 4 persistence subgate verified in E008.

An explicit --persist launch creates exclusive fixed-lab storage and initial
status, then acknowledges a separate supervisor session. The run retains owned
children and deadlines after SSH loss. Reconnection reads its exact run identity,
source/profile, producer and finalized status; it does not start another attempt
or trust a stored PID as cleanup authority. Both active and completed duplicate
starts are rejected without overwriting evidence. Complete status follows native
event finalization and means collection/cleanup, not a service pass. Native
failure assertions survive a later transport/status error in the shared evaluator.

This solves the tested healthy-target SSH-loss path, not arbitrary VM/filesystem
failure. Phase 4's full crash/probe/channel/sink/cleanup-contamination matrix remains
open and must retain explicit infrastructure errors and partial evidence.

## D012: Own each process and evidence channel independently

**Date:** 2026-11-06. **State:** Phase 4 gate verified in E009.

The supervisor owns processes, channels and containment deadlines; disposable
workers own every service-facing open/operation/probe. Each exact child has its
own framed nonblocking pipe and source/sequence validation. Process creation,
termination request and actual wait/reap status are separate records. ECHILD loses
ownership; it never authorizes guessing/signalling a PID. Unexpected fixture exit
is service_interference with no assumed actor. No monitor/slm was present; a
separately owned lab injector qualified interference handling without changing
unrelated managers. Source scheduling stayed modest and polling sleeps are bounded.

## D013: Preserve independent failures and quarantine failed cleanup

**Date:** 2026-11-06. **State:** Phase 4 gate verified in E009.

Keep trustworthy earlier assertions when later evidence/cleanup fails. Overall
ERROR cannot erase an independently established cancellation/pending-state FAIL.
Malformed/truncated/missing required evidence never yields PASS. Dependent native
cases explicitly name their predecessor and become NOT_RUN if clean completion
cannot be established. A separately recorded lab recovery neither rewrites original
failure nor supplies health for the original service instance. Status is never
process cleanup authority. Reason vocabulary is documented in reason-codes.md.

## D014: Contain primary evidence failures without inventing cleanup

**Date:** 2026-11-06. **State:** Phase 4 gate verified in E009.

Use a bounded in-memory journal and reserved recovery descriptor so primary write
failure does not terminate the supervisor before cleanup. Real EBADF and ENOSPC
were qualified, including a prior service FAIL and owned reaping. Exhaust only a
small owned loopback filesystem, never the main guest filesystem. RLIMIT_FSIZE
failed to establish the desired write error and was rejected as a test setup.

This is not independent storage redundancy or power-loss attestation. A stalled
owned lab VM produced an actual bounded host transport timeout, infrastructure
ERROR and remote cleanup NOT_RUN. Reconnection/collection uses the original run
ID; neither a closed SSH session nor successful kill syscall proves remote cleanup.

## D015: Prove one explicit non-restart signal mode

**Date:** 2026-11-06. **State:** Phase 5 signal-family subgate passed E010; the
full Phase 5 gate remains open.

Use a dedicated single-thread worker with SIGUSR1, sigaction flags 0, queried
unblocked mask, no retry and no simultaneous operation timer. The handler changes
only volatile sig_atomic_t. Record trigger request, successful signal syscall,
server unblock, ordinary-context handler observation and actual operation return
separately. Bind the signal number and errno to target manifest/header values,
never host constants. Both services returned MsgSendv -1/EINTR 4 with SIGUSR1 16.
The existing current-owned-unblock MsgError(-1) path preserves the kernel reason;
no ERESTART or fabricated SA_RESTART compatibility definition is used.

Signal profiles declare EINTR and one explicit scenario family; timeout profiles
retain ETIMEDOUT. Known auto-restart requests become UNSUPPORTED before launch.
Strict native rejection and host mutations verify that wrong errors, missing
handler evidence, retry/mask/flags or simultaneous timeout cannot become PASS.
Client departure, repetition and ordering still require their separate native gates.

## D016: Keep execution errors separate from evidence loss

**Date:** 2026-11-06. **State:** native follow-up passed in E010.

A failed producer write can establish fixture death and evidence loss independently;
retain both. A manager terminating a pending fixture can instead produce complete
observations of devctl ESRCH, close EBADF and nonzero worker exit. Classify those
as interference/worker_close_failed, not a service contract FAIL or log truncation.
Record native exit/signal facts with QNX wait macros so Python need not decode raw
wait bits using host assumptions. Successfully returned forbidden payloads remain
independent FAIL assertions even if later interference occurs. No unexplained
nonzero worker exit can satisfy a PASS.

## D017: Observe departure and preserve resource-manager bookkeeping

**Date:** 2026-11-07. **State:** Phase 5 gate verified in E011.

A kill request is only a stimulus. Require actual native wait/reap of the exact
owned worker within the declared bound, then public state and health on the original
fixture. Duplicate a descriptor, close one before pending and observe two close_dup
callbacks/default returns followed by exactly one close_ocb/default destruction.
Callbacks remain serialized in one dispatch thread. Always delegate default count/
close/free bookkeeping; detach no library-owned connection manually. Synthetic
rcvid 0 cannot be replied to. Native callbacks in this lab had nonzero IDs; that
specific synthetic path is not claimed as a native observation.

Pending storage has one terminal owner and static lifetime. Saved notifications
retain immutable request/owner identifiers, with no OCB pointer. Final close clears
links before free. Retained-waiter controls deliberately retain a logical tombstone,
with no live rcvid/OCB reference. Job lifetime is independent of waiter lifetime;
drop-job is a separate explicit defect. Ignored-unblock departure can leave process
termination unobserved until fixture cleanup; classify ERROR/departure_unobserved,
withhold health and never substitute later cleanup reaping for the earlier bound.

## D018: Preserve every cycle and stop at contamination

**Date:** 2026-11-07. **State:** Phase 5 gate verified in E011.

Repeat plans require same-instance reset policy and 1–20 cycles, default20.
SET_CYCLE changes the event identity after pending reaches zero; it does not reset
service counters, generations or job state. Fresh client workers perform each
cycle. Record precondition, timeout, result, public state, fresh health and actual
worker cleanup. Unknown or forbidden state stops the sequence; every later cycle
is explicit NOT_RUN. Retain-third preserves two passing cycles and the failed third.
A cycle-two probe fault preserves cycle one and does not invent state from the
cycle-end placeholder. Final cleanup facts do not get attributed to an earlier
cycle merely because aggregate cleanup uses cycle1. A retained job is distinct
from a leaked waiter. No memory-leak assertion follows from successful reconnects.

Bound the larger sequence separately: 256 children / 4096 accepted producer events,
8192 journal frames / 8 MiB. Extended single cases use 64 children / 1024 events,
2048 journal frames / 4 MiB. Legacy timeout/signal limits remain 16 / 256 and
512 / 2 MiB. Exhaustion remains infrastructure ERROR, never partial PASS.

## D019: Direct ordering with observed fixture barriers

**Date:** 2026-11-07. **State:** Phase 5 gate verified in E011.

Completion-first parks a real kernel unblock at a fixture barrier, then releases
the valid request before cancellation can commit. Cancellation-first observes
interrupted completion before releasing work. Compare event times/identities and
worker control-start observations, not poll sleeps or merged line order. A second
completion-first subcheck records the normal result before signalling the still
live worker. Current MsgInfo, unblock flags and logical/generation/owner identity
guard stale notifications; no cached receive ID alone authorizes a reply.

While a later generation is pending, inspect the saved real notification and prove
no old payload completes that request. Distinct values (42/43 and 420/421) expose
stale delivery. A separate parked control request generates a genuine unmatched
kernel unblock and is safely completed after current-owner validation. A duplicate
terminal-attempt control remains FAIL even if the kernel rejects the second call;
it is not evidence of two delivered replies. These are directed checks, without
exhaustive concurrency claims. All fixture controls are typed reviewed packets
inside registered adapters; core scenario/evaluator files contain no service names.


## D020: Seal evidence separately from the service conclusion

**Date:** 2026-11-07. **State:** Phase6 gate verified in E012.

Reserve an exclusive bundle directory, preserve raw inputs, write finished files
atomically and publish the hashed final marker only after cross-validation. Keep
partial.json on collection failure. A finalized ERROR or FAIL bundle is useful
evidence; finalization never means service PASS. Store native source/build identity
and host evaluator source identity separately. Re-evaluation and exports leave raw
bytes unchanged. Canonical assertions expose reason, contract expected value,
actual observed records/status and event references; no missing private state is
inferred. Read-only files and hashes establish identity/integrity, not attestation.

## D021: Replay one preserved contract against an explicitly selected build

**Date:** 2026-11-07. **State:** Phase6 gate verified in E012.

Require --candidate-manifest for original and changed builds. Resolve only reviewed
lab executable paths, query actual processor/machine, verify all deployed hashes
with SFTP readback, then request exactly one persistent launch. Distinguish request,
acknowledgement and collected outcome. Reserve/preserve each attempt including
preflight failure; never rerun until pass. Original profile, operation inputs,
fixture setting, bounds/reset/order stay identical. Changed expectation/profile
means incomparable; incomplete candidate means incomplete. Retain non-reproduction
honestly and original/candidate identities in every comparison.

The native gate uses committed qualification branch c26365e: actual source removal
of the ignored-unblock early return in both fixtures. It preserves the saved
ignore-unblock setting and fixes the demonstrated behavior with different binary
hashes. It does not alter main's intentional negative controls or merely change a
stamp/comment/flag. The exact patch/build metadata are retained. This specialized
replay transport reuses the intended lab; full target/deploy/collect workflow is
Phase7.

## D022: Keep export success separate from test execution success

**Date:** 2026-11-07. **State:** Phase6 gate verified in E012.

Use ElementTree for deterministic JUnit, stable family/cycle names and bundle
references. Required UNSUPPORTED/NOT_RUN remains skipped plus a synthetic coverage
error; all-skipped required coverage cannot look green. Keep every failed assertion
under later errors. Test-execution exit precedence is130 >2 >3 >1 >0. Offline
inspect/bundle/export/compare may succeed while processing valid red evidence.
