# Continue with Phase 3

Read `AGENTS.md`, `STATUS.md`, relevant sections of `IMPLEMENTATION_PLAN.md`, and E005/E006 in `TEST_EVIDENCE.md` before changing files. Inspect Git state and preserve unrelated changes. Work remains on `implementation/phase-1`; routine phase transitions and fixes are already authorized.

## Passed gates

Phase 1 checkpoint: `554823b`. Tested native probe/build source: `11f7729fcb73c73b9ca7d29c8ec7aed818b14c57`. Full Access resolved the old restrictions, with actual licensed QNX compilation, Git writes and loopback sockets verified.

Phase 2 native source: `8583071886adc4d2df9c8b4e7d1eae47feeab251`. Clean source build and two full saved-input replays passed their gates. Both ignore-unblock cases remain genuine service FAILs; both corrected cases PASS. Complete logs and hashes are in `docs/evidence/phase2-*`. See `docs/phase2-native.md` for semantics, commands and support boundaries.

The Phase 2 supervisor does no service-facing calls. Workers compare ordinary read with native _IO_READ/MsgSendv and arm an absolute monotonic send/reply deadline immediately before the send. Corrected unblock handling preserves default bookkeeping, verifies live ownership and _NTO_MI_UNBLOCK_REQ, and returns ETIMEDOUT (260 on this QNX image) via MsgError(rcvid, -1). Pending state clears and a fresh read succeeds.

A successful kill does not prove a reply-blocked child died: both SIGTERM and SIGKILL left the defect client unreaped at their observation points. Stopping its owned fixture released it, then both children were reaped. Preserve this measured escape path, exact process ownership and event evidence when expanding the runner.

## Qualified lab

- Source `/home/mignon/qnx800/qnxsdp-env.sh`; use qcc, C11 and Make.
- Original `$HOME/qnx-vm-resmgrcheck` and its bootstrap log remain untouched.
- Dedicated image: ignored `.local/qnx-lab/`; overlay `run.qcow2`. It includes hello/capability probes and the missing sshd-auth helper/links. The Phase 2 binaries were uploaded to `/data/resmgrcheck`.
- Existing client and host keys were reused; do not reinstall QNX or recreate credentials. No private material belongs in Git/chat.
- SSH: `ssh -F .local/ssh_config resmgrcheck-qnx`. SFTP: `scp -F .local/ssh_config ... resmgrcheck-qnx:/data/resmgrcheck/...`. Strict host-key verification is pinned to the locally known image key, exact 127.0.0.1:22220 entry.
- Launch through `sg kvm -c 'qemu-system-x86_64 ...'` to apply the already assigned group. One CPU, 1 GiB, KVM, restricted user networking/loopback forwarding. No host service/firewall changes.
- QNX 8.0.0, `2026/06/05-16:26:03EDT`, x86pc x86_64. No server-monitor/slm in the recorded image. Reinventory if the recipe changes.
- VM remains running in the project-owned QEMU tool session; probe SSH before reuse. Preserve the overlay/log before relaunching. Only this guest may be stopped with `[ "$(uname -s)" = QNX ] && shutdown -S reboot`, paired with QEMU -no-reboot.
- Raw logs: `.local/evidence/phase1-*.log`, `phase2-*.log`; console: `.local/qnx-lab/console-phase1.log`.
- Saved replay: upload `tests/qnx/phase2-replay.sh` and the three binaries, then run `sh phase2-replay.sh` in their target directory. Download logs before replay overwrites those target names.

## Next work

Phase 3 is not implemented. Establish formats-v1, bounded explicit Python validators, pinned cJSON, adapter_v1 and registration outside core. Refactor the sensor slice through that interface, add the job fixture/adapter with true WAIT_RESULT devctl baseline/cancellation/next-client retrieval, and introduce the shared host evaluator. Missing capability must be UNSUPPORTED; invalid/missing evidence must not pass.

Do not confuse the Phase 2 text/C-classified spike with the planned versioned run contract or production runner. Signal interruption, client-departure obligations, repetition, transport recovery, JSON/JUnit/HTML, and publication are later gates. Continue in order with real native evidence and coherent commits.
