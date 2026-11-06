# Known limitations

Updated: 2026-11-06.

- This is the Phase 1 repository bootstrap. The cancellation tester, fixtures, evaluator, replay workflow, and reports are not implemented by this checkpoint.
- Real QNX smoke execution was observed through operator-provided terminal evidence. The new repository commit has not yet been built and executed on the target.
- The bootstrap route embeds an executable in an image and uses the serial console. OpenSSH command execution and file transfer are not yet validated. An authentication-helper issue in the guest SSH path remains unresolved.
- The required resource-manager and IPC facilities, process supervision, bounded channels, and target service-monitor policy still need their Phase 1 checks.
- KVM was verified in the operator's shell. A different agent or SSH process must independently have the required device permissions and group membership.
- The observed guest release is QNX 8.0.0 with its recorded build identity. The root catalog package version does not establish the revision of the complete installed SDK. No QNX SDP 8.0.5 claim is made.
- The smoke VM was started with `-snapshot`; guest disk changes from that run were temporary. Host console logs remain host files.
- The QEMU Ctrl+A, then X exit sequence did not work reliably in the operator's terminal. The tested fallback was a guarded QNX reboot request with QEMU's `-no-reboot` option.
- QEMU is suitable for the planned behavioral evidence. These results do not establish hardware worst-case timing, safety certification, or production readiness.

Resolve limitations against the actual installed environment, and update this file with the evidence when a limitation changes.
