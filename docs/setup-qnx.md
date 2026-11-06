# QNX development setup

## Existing working environment

The operator has already installed and licensed QNX SDP through the normal myQNX and QNX Software Center flow on an Ubuntu 24.04.3 x86_64 host. Software Center 2.0.4 and `qcc` with GCC 12.2.0 were observed. The SDK environment is at `$HOME/qnx800/qnxsdp-env.sh`.

QEMU 8.2.2 and KVM were tested. A one-CPU, 1 GiB QNX guest in `$HOME/qnx-vm-resmgrcheck` executed the original smoke program twice. Preserve that image directory and its `qemu-console.log`. See [TEST_EVIDENCE.md](TEST_EVIDENCE.md).

The implementation agent should reuse this environment under the account that owns the existing SDK and local license setup. No Windows migration or repeated installation is needed. Keep myQNX authentication and license material local; never copy them into this repository or a chat transcript.

## Start a development session

From the repository root, load the actual installed environment:

```bash
source "$HOME/qnx800/qnxsdp-env.sh"
command -v qcc
qcc -V
```

The intended native variant is `gcc_ntox86_64`. A native QNX executable is run inside the QNX guest, not by the Ubuntu kernel.

Check KVM access in the process that will start QEMU. `id -nG` shows that shell's groups; it must have read and write access to `/dev/kvm`. The operator previously needed a new shell group context after group assignment. Reconnecting or running `newgrp kvm` applies an existing assignment; do not assume another process inherited that change. Do not change unrelated server services or security settings.

## Repository smoke build

```bash
make qnx
file build/qnx-x86_64/hello
```

The build uses `qcc -Vgcc_ntox86_64 -std=c11 -Wall -Wextra -Werror` and writes `build/qnx-x86_64/hello`. Its native execution has not yet been verified from this repository.

## Adapted image recipe

**Status:** the core image options below were used in the successful operator bootstrap. This repository-path adaptation is not yet executed or validated. It uses a new ignored directory to preserve the operator's existing image and evidence. Use a checkout path without spaces for this initial buildfile recipe.

Run from the repository root after a successful `make qnx`:

```bash
qnx_repo_dir=$(pwd -P) &&
mkdir -p .local &&
mkdir .local/qnx-vm &&
mkdir -p .local/qnx-vm/local/snippets &&
printf '%s\n' "[uid=0 gid=0 perms=0755] /proc/boot/hello-qnx=$qnx_repo_dir/build/qnx-x86_64/hello" > .local/qnx-vm/local/snippets/ifs_files.smoke &&
(
    cd .local/qnx-vm &&
    mkqnximage --type=qemu --arch=x86_64 --cpu=1 --ram=1G \
      --graphics=no --tcg=no --hostname=resmgrcheck \
      --ssh-ident=none --build
)
```

Plain `mkdir .local/qnx-vm` deliberately stops the command chain if that directory already exists. Inspect an existing directory before choosing to reuse it. Do not use `--wipe` as routine troubleshooting.

The snippet includes the repository binary at `/proc/boot/hello-qnx`. `--ssh-ident=none` does not disable sshd or networking. Network isolation is set in the QEMU launch below.

## Adapted foreground launch and evidence

The following launch keeps one virtual CPU and 1 GiB of RAM, supplies the documented QNX disk and IFS inputs, and provides a serial console without a network adapter. Its repository paths and log destination still require a real execution checkpoint.

```bash
cd .local/qnx-vm &&
qemu-system-x86_64 \
  -accel kvm -cpu host -smp 1 -m 1G \
  -drive file=output/disk-qemu.vmdk,format=vmdk,if=ide,id=drv0 \
  -kernel output/ifs.bin \
  -display none -nic none \
  -chardev stdio,id=console,mux=on,signal=off,logfile=qemu-console.log \
  -serial chardev:console -mon chardev=console,mode=readline \
  -object rng-random,filename=/dev/urandom,id=rng0 \
  -device virtio-rng-pci,rng=rng0 \
  -no-reboot -snapshot
```

`-snapshot` makes guest disk changes temporary. Preserve a prior console log before repeating a launch at the same log path. Do not start a second VM against an already running instance's image.

At the **QNX guest console**, record:

```sh
uname -a
/proc/boot/hello-qnx
printf 'exit=%s\n' "$?"
/proc/boot/hello-qnx
printf 'exit=%s\n' "$?"
```

Record actual output; these commands are not a prefilled success result. Return to Ubuntu with the fallback already tested in the operator session:

```sh
[ "$(uname -s)" = QNX ] && shutdown -S reboot
```

The guard prevents this command from requesting a shutdown on Ubuntu. QEMU's `-no-reboot` exits when the guest requests a reboot. Ctrl+A followed by X was unreliable in the operator's terminal, so it is not the only documented exit route.

## Finish Phase 1

Retain the console log and associate it with the exact source revision, build command, executable hash, and observed target identity. Complete the required native API/facility and service-monitor inventory. Establish a basic OpenSSH command/file-transfer route using a host-local connection, local authentication, and host-key verification; address the guest authentication-helper issue before claiming transfer support. Never disable unrelated host monitoring or broaden network exposure to work around a setup issue.

## Primary references

- [QNX Software Center command line](https://www.qnx.com/developers/docs/qsc/com.qnx.doc.qsc.user_guide/topic/commandline_qsc.html)
- [QNX 8.0 mkqnximage](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/m/mkqnximage.html)
- [QNX QEMU boot specifications](https://qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/additional_specs.html)
- [QNX 8.0 shutdown](https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/s/shutdown.html)
- [QEMU command-line reference](https://www.qemu.org/docs/master/system/qemu-manpage.html)
