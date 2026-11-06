# Implementation status

Updated: 2026-11-06.

## Current checkpoint

| Item | State |
| --- | --- |
| Current phase | Phase 2: prove the cancellation problem end to end |
| Phase state | `passed`; E006 records two real defect/correction replays |
| Phase 1 | `passed`, checkpoint `554823b`; E005 records the native build, SSH/SFTP and capabilities |
| Tested Phase 2 source | `8583071886adc4d2df9c8b4e7d1eae47feeab251`, clean at build/run |
| Target | QNX 8.0.0, `2026/06/05-16:26:03EDT`, x86pc x86_64; QEMU 8.2.2/KVM, one CPU, 1 GiB |
| Next gate | Phase 3: versioned contracts, host evaluator, adapter boundary and job-service proof |
| Phases 3–10 | Not implemented or validated yet |
| Active blocker | None in the qualified lab |

## Completed deliverables

- Full Access restored normal compiler license-lock writes, Git metadata writes and loopback sockets. Actual qcc builds succeed; no SDK reinstall or credential regeneration.
- Dedicated ignored lab image reuses the existing identities, includes the missing authentication helper, and uses strict host-key verification with SSH forwarding only on 127.0.0.1:22220.
- Repository hello transferred through SFTP and ran twice with exit zero. Compiled capability probe passed the resource-manager/dispatch, monotonic timer, IPC, process and bounded-channel checks. No server-monitor/slm runs in the recorded lab inventory.
- Single-threaded deferred sensor fixture with bounded pending table, logical IDs/generations, explicit release/state hooks, corrected default and opt-in `ignore-unblock` defect.
- Disposable workers for every service-facing operation; independent native supervisor with absolute timeout/precondition checks, bounded producer pipe, evidence sequence checks, watchdog, exact child ownership and bounded cleanup.
- Two saved-input replay invocations at the committed native revision. Each recorded FAIL for the deliberate defect and PASS for the correction. Corrected MsgSendv returned -1 / QNX ETIMEDOUT 260, pending state cleared and a fresh client read succeeded.
- In both defect cases the client stayed unreaped after termination signals until the owned fixture stopped. All four cases then recorded complete reaping, no evidence error and a final writer marker. No residual sensor fixture/client/supervisor appeared in post-run inventory.

## Validation and evidence

Build: `source /home/mignon/qnx800/qnxsdp-env.sh && make -B qnx`, exit 0. Native execution: `timeout 25s ssh -F .local/ssh_config resmgrcheck-qnx 'cd /data/resmgrcheck && sh phase2-replay.sh'`, twice, exit 0 after verifying the expected individual supervisor statuses 1/0.

See [TEST_EVIDENCE.md](TEST_EVIDENCE.md), E005/E006, [phase2-native.md](phase2-native.md), and reviewed `docs/evidence/phase2-*` logs/index. The host audit checked these actual native streams; it is not a separate native scenario or synthetic result.

The Phase 2 text protocol and C outcome classifier are a spike. They do not complete the versioned adapter, deterministic Python evaluator, full lifecycle suite, replay product, host CLI or reports. No signal-interruption/client-departure obligation or job-service claim is made.

## Next executable step

Read Phase 3. Define the bounded versioned formats/validators and adapter interface, pin cJSON with its license and hashes, move service-specific behavior behind the sensor adapter, then prove the job WAIT_RESULT cancellation and next-client retrieval on this same native path. Keep the demonstrated Phase 2 regression intact while refactoring.

The qualified lab VM is currently running; check `ssh -F .local/ssh_config resmgrcheck-qnx` before use. Preserve its overlay/logs and the original operator image. Keep keys, SDK/runtime files, generated binaries and raw local state ignored. No publication or submission has been performed.
