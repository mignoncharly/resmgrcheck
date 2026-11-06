# Native cancellation slice

Phase 2 is an intentionally small native experiment, before the versioned adapter, host evaluator, and report formats. It tests an original lab fixture, not a QNX vulnerability or an external driver. Real runs at source revision `8583071886adc4d2df9c8b4e7d1eae47feeab251` are recorded in E006.

## Build and replay

Use the Phase 1 [lab setup](setup-qnx.md), then:

```bash
source "$HOME/qnx800/qnxsdp-env.sh"
make qnx
scp -F .local/ssh_config build/qnx-x86_64/sensor-fixture \
  build/qnx-x86_64/sensor-client build/qnx-x86_64/phase2-supervisor \
  tests/qnx/phase2-replay.sh resmgrcheck-qnx:/data/resmgrcheck/
timeout 25s ssh -F .local/ssh_config resmgrcheck-qnx \
  'cd /data/resmgrcheck && chmod 755 sensor-fixture sensor-client phase2-supervisor && sh phase2-replay.sh'
```

The saved reproduction in `tests/qnx/phase2-replay.sh` runs both modes with the **same** 500 ms operation timeout and 2000 ms cancellation allowance. It expects the intentional defect to produce a service **FAIL**, exit 1, and the correction to produce **PASS**, exit 0. The script's own exit zero means those expectations and cleanup markers were observed; it does not turn the defective service's result into a pass. Exit 2 from the supervisor is an infrastructure/evidence error. Each case has a separate 10-second execution deadline and 2-second cleanup deadline; setup/state/health workers have 2-second bounds. These are configured lab waits, not hard scheduling guarantees.

The runner writes `phase2-ignore-unblock.log` and `phase2-corrected.log` in the target working directory. Copy them out before replaying, since the next invocation writes those names again. Invoke a single case manually as `./phase2-supervisor corrected 500 2000` or `./phase2-supervisor ignore-unblock 500 2000`.

## Fixture and ownership

`native/fixtures/sensor.c` exposes a stream of the exact ten-byte sample `sample=42\n`. Without a mode argument it uses corrected behavior. The explicit `ignore-unblock` mode is the only planted defect in this slice. Its single dispatch thread retains up to eight pending requests and immediately returns to dispatch. Each retained request records logical request/generation, rcvid, client pid/tid, connection IDs, byte count, and OCB identity. Receive IDs alone are not persistent request identifiers.

Fixture-only devctl hooks hold new reads, release pending samples asynchronously, and observe pending/unblock/completion counters. The supervisor runs those calls in disposable workers. The control interface is real QNX devctl, and the tested data read is real QNX I/O. No fake transport is used. Clients in this phase each own one descriptor; duplicate-FD/concurrent-close semantics are not qualified yet.

Unblock handling calls `iofunc_unblock_default()` first. When it delegates application handling, the fixture checks current `MsgInfo()` data, `_NTO_MI_UNBLOCK_REQ`, and the retained request's full ownership. Corrected handling uses `MsgError(rcvid, -1)` only for that live cancellation, releases the queue entry once, and returns `_RESMGR_NOREPLY`. The defect records the same live unblock but deliberately leaves the original read pending. An obsolete/unmatched unblock is ignored. The close-duplicate handler clears owned pending state as applicable and calls `iofunc_close_dup_default()`; it never replies to the synthetic close's receive ID. No dispatch context is retained for asynchronous completion: release uses `MsgReply()` on the owned original receive ID.

## Client operation and time

`native/spikes/sensor_client.c` compares ordinary libc `read()` with `_IO_READ` sent through `MsgSendv()` using installed `io_read_t` and iov definitions. Both returned ten matching bytes in the baseline. A separate pending read is released through the control hook to exercise asynchronous success.

For timeout, buffers and iovs are prepared before arming. The client records an absolute `CLOCK_MONOTONIC` deadline, then calls `TimerTimeout()` with `TIMER_ABSTIME`, `_NTO_TIMEOUT_SEND`, and `_NTO_TIMEOUT_REPLY` immediately before `MsgSendv()`. No logging, allocation, clock query, or other call intervenes on the successful arming path. The fixture's pending timestamp must precede that absolute deadline; the matching live unblock must be at or after it. An absent or ambiguous precondition becomes ERROR, not a cancellation success/failure inference from sleep or file order.

The correction returned raw `MsgSendv` result **-1**, captured `errno` **260** (`ETIMEDOUT` in this QNX environment). The deadline plus 2000 ms is the completion bound; a late unblock does not restart the allowance. The fixture then reported pending zero and one successful cancellation completion. A new supervised client read succeeded before the original fixture instance was stopped.

## Independent supervision and cleanup

`native/spikes/phase2_supervisor.c` spawns all service-facing calls; it performs none itself. It reads nonblocking bounded producer frames, checks producer sequence/monotonic order and overflow, collects exact owned-child status with `waitpid(WNOHANG)`, and is the only final log writer. Producer event writes are bounded and nonblocking; a failed write exits 120 and invalidates evidence. The text stream is a Phase 2 protocol, not the future versioned JSON schema. Its final marker means the writer finished; the separate verdict still matters.

In both final defect runs the supervisor observed confirmed pending state and a live unblock, then hit the original completion bound while the fixture still reported one pending read. It remained responsive and produced `FAIL: cancellation_deadline`. During cleanup, successful SIGTERM and SIGKILL sends to the client each left it unreaped at the 100 ms observation points. Stopping the owned fixture released the client; both were reaped, with raw wait status 15 in those runs. This is an observation of this target/fixture, not a general claim that either signal always kills a reply-blocked process promptly. The supervisor records the intervention explicitly and does not call it successful service cancellation.

Cleanup signals only exact unreaped children it created. A cleanup/evidence failure produces ERROR. Phase 4 must expand failure classification, interruption handling, and contamination semantics; this slice is not the production runner. A stopped whole VM can defeat target-side progress, and closing an SSH connection is not proof of remote cleanup.

## Documentation consulted

The installed QNX 8.0 documentation and headers were read for these semantics:

- [Unblocking handler and default delegation](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.resmgr/topic/signals_HANDLING_UNBLOCKING.html)
- [MsgError and the special -1 error](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/m/msgerror.html)
- [TimerTimeout](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/t/timertimeout.html)
- [Close duplicate handler responsibilities](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_resmgr_io_close_dup.html)

The deferred-reply cancellation behavior is documented server-mediated unblocking. The defect is deliberately in this fixture's application queue handling.
