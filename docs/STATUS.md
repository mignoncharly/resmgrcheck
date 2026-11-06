# Implementation status

Updated: 2026-11-06.

## Current checkpoint

| Item | State |
| --- | --- |
| Current phase | Phase 1: establish the workspace and prove QNX execution |
| Phase state | `in_progress` |
| Repository | New project bootstrap; no Windows workspace migration is required |
| Native environment | The operator built a QNX executable and ran it twice successfully on QNX 8.0 |
| Repository revision tested on QNX | None yet; the successful runs preceded this repository seed |
| Phases 2–10 | Pending, not run |

The earlier environment blocker is resolved. This does not establish that all Phase 1 deliverables or any cancellation tests have passed.

## Verified bootstrap observations

The operator supplied terminal evidence from Ubuntu 24.04.3 x86_64 with QNX Software Center 2.0.4, the QNX SDP environment at `$HOME/qnx800`, and `qcc` reporting GCC 12.2.0 with the `gcc_ntox86_64` variant. QEMU 8.2.2 reported working KVM acceleration after the operator's shell acquired its `kvm` group membership.

A one-CPU, 1 GiB QNX guest reported release 8.0.0, build `2026/06/05-16:26:03EDT`, platform `x86pc`, and architecture `x86_64`. The original smoke executable printed its greeting twice; each execution returned zero. The saved host console log was checked. The guest was then stopped and the Ubuntu prompt returned. See [TEST_EVIDENCE.md](TEST_EVIDENCE.md) for provenance and limits.

## Remaining Phase 1 work

1. Inspect this checkout and its applicable instructions. Record the actual source revision and working-tree state.
2. Build and execute the repository-owned smoke target, linking source, build command, target identity, output, and exit statuses to a retained evidence record.
3. Establish and test the planned OpenSSH command and file-transfer route with local authentication and host-key verification. The bootstrap used image inclusion and a console with guest networking disabled.
4. Confirm the required native APIs and facilities. Inventory `server-monitor` and other target service-management behavior that could affect the fixtures.
5. Finish the reproducible setup record and Phase 1 checkpoint. Proceed to Phase 2 only when the complete Phase 1 gate passes.

## Next executable step

On the existing Ubuntu development host, inspect the checkout, load `$HOME/qnx800/qnxsdp-env.sh`, and build with `make qnx`. Reuse the working licensed environment. Do not reinstall it or restart the setup investigation. Follow [setup-qnx.md](setup-qnx.md) to validate the repository build without overwriting the existing operator VM or its log.

No repository-native cancellation implementation, lifecycle test result, host transport automation, or performance result is claimed at this checkpoint.
