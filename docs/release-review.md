# Release candidate review

This is a source/self-review by the implementation agent. No independent developer,
external adoption or security certification is claimed. Phase9 passed clean source reproduction and the full expected-outcome release
gate in E015. The renderer-only follow-up is qualified separately there.

## Native ownership and QNX bookkeeping

The sensor/job pending records retain a live receive ID, PID/TID, connection IDs,
logical generation and OCB reference. Their `owner()` checks compare all current
identity fields. Both custom unblock callbacks delegate to iofunc_unblock_default
first, then use current MsgInfo/_NTO_MI_UNBLOCK_REQ before a terminal action.
`MsgError(rcvid,-1)` is used only for the current owned unblock, preserving the
original cancellation error. Obsolete/unmatched notifications are not replies to
a later request. See the [official unblock guide](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.resmgr/topic/signals_HANDLING_UNBLOCKING.html)
and [message-info guidance](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_msg_nto_mi_unblock_req.html).

`native/fixtures/lifecycle.h` delegates every descriptor-close/final-close callback
to its default. It retires pending references before the final OCB free and uses
only saved scalar IDs after delegation. Saved notification records retain no OCB
pointer; deliberate waiter leaks retire live IPC/OCB references. The single dispatch
thread serializes these mutations. Synthetic zero receive IDs are never replied
to directly. The [close_dup reference](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_resmgr_io_close_dup.html)
requires default bookkeeping and notes absent automatic OCB locking; the
[final-close reference](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/i/iofunc_close_ocb_default.html)
describes detachment/free. Multithreaded extensions need a separate synchronization
review; they are not qualified by these fixtures.

Jobs belong to the fixture, not the waiter. Cancellation/departure removes waiter
state while retaining the submitted job; completion is non-consuming until explicit
resubmission. Fixed departure/reconnect/ordering gates already preserve actual QNX
proof. There is no memory-leak-absence claim or exhaustive receive-ID reuse proof.

## Input boundary corrections

Current-message bounds must account for combined messages, and the reply buffer
must have actual capacity. See QNX8 [message checking](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.security.system/topic/manual/message_checking.html)
and [resmgr_msgread](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/r/resmgr_msgread.html).
The review found whole-message checks and output writes at the current message
pointer in custom handlers. `message_bounds.h` now checks the exact fixed current
input, declared size, noncombined whole/current agreement, actual reply capacity
and allocated receive-buffer capacity. It writes replies at the buffer start after
saving input. Read payloads are bounded by the client's actual receive buffer.
Combined custom operations are outside this lab protocol and are rejected.

A native negative probe also exposed an uninitialized `next` output on error paths:
truncated/readonly rejected fixture commands could still change hold/generation in
the caller. Both callers initialize it; the helper clears it before validation.
No transition is requested until a recognized, fully validated command. State and
job waits require readable OCBs; hold/complete/barrier mutations require writable
OCBs. Fixtures retain0600 owner-only nodes and the intended lab namespace.

The actual focused QNX gate checks EINVAL22, EMSGSIZE240, EBADF9, ENOENT2 and
framework EBADMSG77 separately. It verifies unchanged generation/pending state and
fresh public results on the same fixture. Tested combined prefixes were rejected
by the framework before the custom tail ran; no tail-execution claim is made.
Its supervisor keeps even preoccupied-device stat in a bounded owned worker and
requires actual waitpid for every child. Failed development probes remain failed.
The registered adapter path uses fixed uncombined messages; this tightening does
not add arbitrary payload or wire-protocol support.

The job adapter still interprets devctl's returned error value separately from
errno. Its prepared _IO_DEVCTL/MsgSendv path preserves installed-header layout,
raw return/errno, reply status/length/reserved fields and typed job ID/value. The
[devctl reference](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/d/devctl.html)
documents this convention. The profile never supplies native pointers or scripts.

## Supervision, evidence and host boundary

Runner/common process helpers own children from creation through observed wait
status. Signal paths consult the live ledger, never persisted PIDs or process
names. Workers own service opens/operations/probes; supervisor deadlines and
cleanup remain independent. Failed cleanup withholds dependents. Restart/lab
recovery is separate from original-instance health. Earlier native failure gates
remain evidence; changed prerequisites are rechecked in release qualification.

Producer frames, native journals and status are bounded. Duplicate keys, unknown
schemas, truncation, overflow, missing final observations and unexpected child
identity cannot establish PASS. Target and host clock domains remain distinct.
Immutable bundles bind raw bytes, status, plans, builds, snapshots and evaluator
identity; canonical re-evaluation protects derived results. JUnit/HTML retain
required unavailable coverage and separate service FAIL/infrastructure ERROR.

Host transport uses strict alias/config types, OpenSSH host-key verification,
argument arrays and quoted fixed commands. Profiles cannot provide remote commands.
Publication/metadata helpers check ownership, no-follow types and bound manifests;
staging never overwrites unknown destinations. Cleanup has no process-name or
recursive-delete command. Uncertain launch preserves intent/identity and collection
history, without a retry launch. Real SFTP readback checks actual bytes.
A final stderr-size check was added so a fast completed local transport cannot
escape the diagnostic cap between polling intervals; a host regression verifies it.

Reports escape every input, contain no raw JSON scripts/innerHTML/network assets,
and cannot replace sealed/partial/raw/diagnostic/history inputs. Native outcomes
remain canonical; optional JS filters only presentation. Changed target/recipe or
contract/settings are incomparable. Paths/links are quoted relative references,
not executable replay instructions. Phase8's actual browser inspection is E014.

## Tooling and limits

qcc gcc_ntox86_64 C11 builds use Wall/Wextra/Werror. An actual qcc -fanalyzer object
compile of16 owned C files emitted no diagnostics. This is static analysis, without
native IPC/concurrency or malicious-target attestation. Native execution remains
required. No target sanitizer or target memory measurement is claimed. cJSON stays
pinned to the reviewed MIT revision; no SDK/runtime code is redistributed.

## Clean qualification procedure

From a separate clean checkout with ignored local target routing configured and
SDP loaded, use `tests/qnx/qualify-phase9.py --out NEW_IGNORED_DIRECTORY
--fixed-source CLEAN_CORRECTED_SOURCE --input-prefix UNIQUE_LAB_ID`. The source-fix
checkout must be separately committed; remove only the intentional ignore-unblock
early-return block from both fixture handlers. Keep profile/settings unchanged.
The script follows README's actual commands, including the initial UNKNOWN doctor,
then the complete expected-outcome release matrix, focused native input gate and
explicit changed-build replay on both services. It preserves commands/output,
JSON/JUnit/HTML, hashes, actual source identity and reused-target disclosure.
E015 records the successful clean-checkout execution, actual source identities and
reused-target state. Native/build/engine equivalence and the small report-only
follow-up are bound separately; earlier bytes were not relabelled.
