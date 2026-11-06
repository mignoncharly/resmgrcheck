# Continue Phase 2 on Ubuntu

Read `AGENTS.md`, `STATUS.md`, the relevant implementation plan sections, and `TEST_EVIDENCE.md`. Preserve the current diff and continue autonomously through passing gates.

## Phase 1 passed

Full Access resolved the previous execution restrictions. The actual `qcc` build and license acquisition, Git writes, and loopback sockets succeeded. Native source revision tested: `11f7729fcb73c73b9ca7d29c8ec7aed818b14c57` (documentation-only changes during the test). E005 links the binary hashes, build, transferred hello's two exit-zero runs, SFTP round trip, compiled capability probe, and target inventory.

Do not reinstall QNX or regenerate credentials. Source `/home/mignon/qnx800/qnxsdp-env.sh` before Make. Native C11/QNX code uses `qcc`; Python host checks do not establish native results.

## Dedicated lab

- Original `$HOME/qnx-vm-resmgrcheck` and its bootstrap log remain preserved.
- Active dedicated image: ignored `.local/qnx-lab/`; IFS, disk and disposable overlay `run.qcow2`. It includes the repository hello and capability probe plus `sshd-auth`.
- Reused the existing client public key and the existing bootstrap host keys; no new credentials. Keep all key material local.
- SSH: `ssh -F .local/ssh_config resmgrcheck-qnx`. SFTP: `scp -F .local/ssh_config ... resmgrcheck-qnx:/data/resmgrcheck/...`.
- Strict host-key verification uses an exact loopback/port entry derived from the existing image's public host key. Listener: `127.0.0.1:22220` only; QEMU user networking with `restrict=on`.
- Launch under the account's already assigned group using `sg kvm -c 'qemu-system-x86_64 ...'`. Main agent group context still lacks kvm; do not modify group or device permissions.
- QNX identity: 8.0.0, build `2026/06/05-16:26:03EDT`, x86pc x86_64, one CPU, 1 GiB. No running server-monitor/slm in the recorded lab inventory.
- Raw logs: `.local/evidence/phase1-*.log`, `.local/qnx-lab/console-phase1.log`; reviewed copies: `docs/evidence/phase1-*.txt`.
- The lab VM is currently running in a project-owned tool session. Probe SSH; if absent, inspect its state and preserve its overlay/log before relaunch. Stop only this guest using the guarded QNX reboot and `-no-reboot`.

## Phase 2 next

Implement the minimal real deferred-read cancellation slice, independent supervision and bounded cleanup. Compare ordinary read with timed native MsgSendv. Arm an absolute CLOCK_MONOTONIC send/reply deadline immediately before the send. Establish pending before that deadline using source timestamps, observe the unblock, and distinguish the explicit ignored-unblock defect from the correction. After default unblock bookkeeping, verify live MsgInfo ownership and _NTO_MI_UNBLOCK_REQ; use MsgError(rcvid, -1) only for a live cancellation. Record a fresh health read, retained pending count, and actual process termination/reaping.

The Phase 1 probes do not test these semantics. Do not expand to Phase 3 until the defective/corrected reproduction and cleanup gate pass. Keep evidence/status/decisions current and commit coherent checkpoints on `implementation/phase-1`.
