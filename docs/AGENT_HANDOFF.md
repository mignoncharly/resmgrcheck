# Continue Phase 1 on Ubuntu

## Immediate objective

Finish Phase 1 of `docs/IMPLEMENTATION_PLAN.md` in this repository, then continue through the remaining phases as their gates pass. Use the existing Ubuntu/QNX environment. The project owner supplied this new repository to continue implementation directly; recovery of the previous Windows workspace is not required.

## Repository and workspace

- Repository: https://github.com/mignoncharly/resmgrcheck
- Implementation branch: `implementation/phase-1`
- Intended Ubuntu checkout: `$HOME/projects/resmgrcheck`
- That directory existed but was not a Git repository at the last operator check. Inspect its current contents and preserve any files before establishing the checkout.
- If an unrelated or nonempty directory prevents a direct clone, use a new sibling checkout or a safe reconciliation. Do not delete files or reset an unrelated repository.
- Run on the actual Ubuntu development host where the SDK is installed. A cloud sandbox or the previous Windows workspace cannot establish the remaining native gates by itself.

## Already established on the development host

These facts come from the operator's supplied command outputs. Confirm the corresponding files and process context locally, without repeating account enrollment or SDK installation.

- Host: Ubuntu 24.04.3 LTS, x86_64.
- QNX Software Center: `$HOME/qnx/qnxsoftwarecenter/qnxsoftwarecenter_clt`, version `2.0.4:v202501021438`.
- QNX SDP environment: `$HOME/qnx800/qnxsdp-env.sh`.
- QNX compiler: GCC 12.2.0; `gcc_ntox86_64` is the reported default target variant.
- QEMU: 8.2.2. KVM was demonstrated as enabled and present.
- The operator's current shell acquired the `kvm` group through `newgrp kvm`. Your own agent process must have access to `/dev/kvm`; membership in another terminal is not proof that your process has it.
- Existing bootstrap image directory: `$HOME/qnx-vm-resmgrcheck`.
- Persisted bootstrap console log: `$HOME/qnx-vm-resmgrcheck/qemu-console.log`.
- The original source and binary are in a separate `$HOME/qnx-smoke.*` directory. Locate the existing files; do not treat that glob as permission to delete or replace them.
- The guest reported: `QNX resmgrcheck 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64`.
- The smoke executable ran twice on the guest and returned zero both times. Its source is reproduced in `native/spikes/hello.c`.
- The VM was shut down after testing. The successful shutdown command in the QNX console was `[ "$(uname -s)" = QNX ] && shutdown -S reboot`; the QEMU invocation used `-no-reboot`.
- The baseline package query returned `com.qnx.qnx800=8.0.0.00141T202311271501L`. This is not a complete inventory of the installed SDK's update level.

## Remaining Phase 1 work

1. Establish the Ubuntu checkout and load the existing SDK environment. Review the seeded files against the approved plan and inspect local host prerequisites.
2. Build the repository's smoke source with `make qnx`, record the source revision/hash and exact compiler command, and link it to actual guest execution evidence. Preserve the earlier bootstrap transcript as prior operator evidence.
3. Complete a basic OpenSSH and file-transfer route to the lab guest. The successful bootstrap deliberately used `-nic none`. Guest startup also reported `/usr/libexec/sshd-auth does not exist or is not executable`.
4. Investigate the SSH image contents using the installed SDK and official QNX documentation. Include the appropriate helper files and links, rebuild the dedicated guest, and validate authentication and the selected transfer mechanism. Use dedicated local SSH material, host-key verification, and a loopback-bound host forwarding port. Inspect for port conflicts; do not expose the guest on the public network or alter the host firewall.
5. Inventory and validate the native facilities needed for Phase 2: resource-manager headers and dispatch, monotonic clocks, process creation/waiting, bounded channels, and the relevant IPC APIs. Inspect whether `server-monitor` or service-management policies could change fixture behavior; record the dedicated lab configuration.
6. Bring the setup recipe, architecture, decisions, status, limitations, and test evidence up to date with what you actually tested. Commit a coherent Phase 1 checkpoint.
7. Mark Phase 1 complete only after its documented gate passes. Then begin Phase 2's real deferred-I/O cancellation reproduction and continue through the plan. Do not claim a cancellation test has passed based on the hello program.

## Working rules

Continue routine implementation and phase transitions without repeatedly asking the owner for approval. If a genuine access or authentication barrier remains, identify the precise local action needed and continue independent work. Never request secrets in chat.

Do not repeat the already completed registration, license deployment, Software Center installation, or SDK installation merely because earlier Windows notes said Phase 1 was blocked. Do not assume native results from host-only tests. Do not publish to Devpost or upload a demonstration on the owner's behalf without the corresponding authorization.

