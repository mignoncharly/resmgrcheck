# Implementation status

Updated: 2026-11-06.

## Current checkpoint

| Item | State |
| --- | --- |
| Current phase | Phase 2: cancellation problem end to end |
| Phase 1 state | `passed`; E005 records actual repository build, SSH/SFTP, two runs, native capabilities, and monitor inventory |
| Phase 2 state | `in_progress`; cancellation implementation and evidence are next |
| Tested native source | `11f7729fcb73c73b9ca7d29c8ec7aed818b14c57`; documentation-only dirty tree during testing |
| Target | QNX 8.0.0, `2026/06/05-16:26:03EDT`, x86pc x86_64; QEMU 8.2.2/KVM, one CPU, 1 GiB |
| Phases 3–10 | Not started |

## Phase 1 completion

The user restored Full Access. Actual QNX compilation succeeded, proving normal license acquisition. Git metadata writes and a loopback listener succeeded. No SDK reinstall or credential regeneration was needed.

The native hello and capability probe build with `qcc -Vgcc_ntox86_64 -std=c11 -Wall -Wextra -Werror`. The transferred hello ran twice via SSH with exit zero, and its SFTP round-trip hash matches. The native capability probe passed resource-manager attach/detach, dispatch allocation, monotonic clock and TimerTimeout receive cancellation, fork/wait, posix_spawn/wait, bounded pipe/poll, and Channel/Connect/MsgSend/Receive/Reply.

A dedicated image at ignored `.local/qnx-lab/` preserves the operator image. It reuses existing SSH keys, includes the missing authentication helper and helper links, and forwards SSH only on `127.0.0.1:22220`. SSH uses strict host-key checking against the existing image's public host key. No `server-monitor` or `slm` runs in this lab image. The earlier TCG SSH fault was not reproduced under KVM with this image.

Evidence: [TEST_EVIDENCE.md](TEST_EVIDENCE.md), E005, and reviewed files in `docs/evidence/phase1-*.txt`. No cancellation success is inferred from this gate.

## Next executable step

Implement Phase 2's single-threaded deferred sensor fixture, visibly named `ignore-unblock` mode, disposable worker, and independent bounded supervisor. Record pending timestamps before the absolute operation deadline, live unblock ownership checks, corrected ETIMEDOUT completion, post-cancel state and new-client health, and actual cleanup of a reply-blocked child.

Current lab VM is running as a project-owned QEMU process with its console in the active tool session. Use `ssh -F .local/ssh_config resmgrcheck-qnx`; check target readiness before use. Logs and generated binaries remain ignored. No publication or submission has been performed.
