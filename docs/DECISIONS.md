# Decisions

## D001: Keep the approved project scope

**Date:** 2026-11-06. **State:** accepted execution specification.

ResMgrCheck tests cancellation and client-lifecycle obligations in QNX resource managers that retain pending requests. Follow the unchanged [ten-phase plan](IMPLEMENTATION_PLAN.md). First prove one actual cancellation defect and its correction, then expand the runner and developer workflow. Do not add a cloud service, database, frontend framework, LLM verdict engine, or unrelated platform support.

## D002: Continue on the working Linux host

**Date:** 2026-11-06. **State:** supported by operator bootstrap evidence.

Use the existing Ubuntu 24.04.3 x86_64 host, licensed QNX SDP environment, and QEMU/KVM target. The new repository is the implementation starting point. Windows migration is outside this work.

Use one virtual CPU and 1 GiB of guest RAM for the initial lab recipe. KVM access depends on the groups of the process starting QEMU; an agent must check its own session rather than infer access from a different shell's successful probe.

## D003: Treat the console route as bootstrap transport

**Date:** 2026-11-06. **State:** temporary bootstrap choice.

The smoke executable was included in the image at `/proc/boot/hello-qnx` and run through the serial console. Guest networking was disabled. This established real execution without a target file-transfer service.

The planned product transport remains system OpenSSH with a tested file-transfer mechanism. Complete that basic route during Phase 1, using local credentials, host-key verification, and a lab connection limited to the host. Full deployment and run-management commands remain later work. `--ssh-ident=none` omits identity configuration; it is not a switch that disables guest networking or sshd.

## D004: Preserve the source of every native claim

**Date:** 2026-11-06. **State:** active evidence rule.

The successful bootstrap runs are operator-provided terminal evidence. They do not validate a new repository commit automatically. Record a fresh repository build/run checkpoint with its source revision and artifact identity. Do not reconstruct an invented transcript or label host-only checks as QNX execution.

The catalog baseline `com.qnx.qnx800/8.0.0.00141T202311271501L` identifies the selected root package. It does not identify every installed SDK component or prove a particular whole-SDK patch level. Record observed package and target versions separately.

## D005: Use the planned small toolchain

**Date:** 2026-11-06. **State:** accepted execution specification.

Use C11 with required QNX extensions, `qcc`, and a small Make build for native code. Use Python 3.10 or newer and its standard library for the host application. Pin and vendor cJSON with its license when Phase 3 requires it. Original project code uses MIT licensing by default.

Publish original source and reproduction instructions. Keep SDK contents, proprietary runtime images, credentials, license material, and machine-local authenticated configuration outside the repository.
