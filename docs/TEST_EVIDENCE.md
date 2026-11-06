# Test evidence

## E001: Operator bootstrap, 2026-11-06

**Provenance:** terminal output supplied by the operator during environment setup. This record summarizes those observations; it is not a fabricated raw log or a claim that the repository-seeding agent executed the commands. The source and binary used for these runs existed before this repository checkpoint.

| Observation | Reported result |
| --- | --- |
| Host | Ubuntu 24.04.3 LTS, x86_64 |
| QNX Software Center | 2.0.4 |
| SDK environment | `$HOME/qnx800/qnxsdp-env.sh` loaded successfully |
| Compiler | `qcc -V` reported GCC 12.2.0 and `gcc_ntox86_64` |
| Emulator | QEMU 8.2.2 |
| KVM probe | QMP reported `enabled: true` and `present: true` in the operator's authorized shell |
| Native build | Original C smoke program compiled and linked with the QNX x86_64 variant |
| Executable inspection | ELF 64-bit x86-64 PIE with interpreter `/usr/lib/ldqnx-64.so.2` |
| Guest resources | One virtual CPU, 1 GiB RAM |
| Target identity | QNX, node `resmgrcheck`, release 8.0.0, build `2026/06/05-16:26:03EDT`, `x86pc`, `x86_64` |
| Guest executable | `/proc/boot/hello-qnx`, included through `local/snippets/ifs_files.smoke` |
| First execution | Greeting printed; exit status 0 |
| Second execution | Greeting printed; exit status 0 |
| Retained console output | Operator confirmed the host console log contained the real output |
| Guest stop | Guarded `shutdown -S reboot` caused QEMU started with `-no-reboot` to exit; Ubuntu prompt returned |

The compile flags used were:

```text
-Vgcc_ntox86_64 -std=c11 -Wall -Wextra -Werror
```

The operator's existing VM directory is `$HOME/qnx-vm-resmgrcheck`. Its host console evidence is `qemu-console.log` in that directory. Preserve that file. Locate the original smoke source and executable among the operator's existing `qnx-smoke.*` directories when associating the old artifact with a source hash. Do not treat a similarly named file as the same artifact without checking it.

The bootstrap guest had no network adapter. No OpenSSH transfer, cancellation scenario, timeout behavior, signal behavior, client-departure cleanup, or resource-manager recovery was tested by these smoke runs.

## E002: Repository-native checkpoint

**State:** not run.

The repository build interface is `make qnx`, producing `build/qnx-x86_64/hello` from `native/spikes/hello.c`. The image recipe in [setup-qnx.md](setup-qnx.md) adapts the observed bootstrap configuration to that path. This recipe has not yet been executed from the new repository.

The implementation agent must append the actual source revision and dirty state, build command and exit status, executable identity, target identity, two runtime outputs and exit statuses, console-log location, and any relevant environment change. Retain original evidence locally and publish only reviewed copies without credentials, license information, or unrelated host details.

Passing this checkpoint establishes a repository-owned smoke result. The remaining Phase 1 transport, native-facility, and service-monitor checks must still be recorded before the phase is marked passed.
