# QNX development setup

## Verified environment

The installed Ubuntu 24.04.3/QNX SDP environment is reused as mignon. Do not reinstall it or recreate credentials. Load:

```bash
source "$HOME/qnx800/qnxsdp-env.sh"
make qnx
qcc -V
file build/qnx-x86_64/hello
```

Verified compiler: GCC 12.2.0, `gcc_ntox86_64`. Native build flags: `-std=c11 -Wall -Wextra -Werror`. `make check-qnx` checks environment and directory access without reading licenses; the actual build validates normal compiler licensing. The previous read-only license/Git and socket restrictions are historical (E002–E004); Full Access resolved them.

## Preserve the bootstrap

The operator's original image and console log remain at `$HOME/qnx-vm-resmgrcheck`. The earlier inspection copy is `.local/qnx-vm`. Neither is the active dedicated lab. The working image is `.local/qnx-lab`.

The following recipe was executed successfully. It stops if the lab directory exists; inspect existing state and use a new path rather than deleting or overwriting it. Existing client and bootstrap host keys are reused locally. Never commit key material, generated runtime or images.

From the repository root after `make qnx`:

```bash
mkdir .local/qnx-lab &&
mkdir -p .local/qnx-lab/local/snippets .local/qnx-lab/local/misc_files &&
cp -p "$HOME"/qnx-vm-resmgrcheck/local/misc_files/ssh_host_* .local/qnx-lab/local/misc_files/
```

Create `local/snippets/ifs_files.resmgrcheck` under that lab directory, substituting the actual repository absolute path for `REPO`:

```text
[uid=0 gid=0 perms=0555] /proc/boot/hello-qnx=REPO/build/qnx-x86_64/hello
[uid=0 gid=0 perms=0555] /proc/boot/capabilities=REPO/build/qnx-x86_64/capabilities
[type=link] /usr/libexec/sshd-auth=/system/bin/sshd-auth
[type=link] /usr/libexec/sshd-session=/system/bin/sshd-session
```

Create `local/snippets/system_files.resmgrcheck`:

```text
[uid=0 gid=0 perms=0555] bin/sshd-auth=usr/libexec/sshd-auth
```

The SDK's generated image omitted the installed authentication helper. Including it and providing the runtime helper links produced a working SSH route under KVM. Authentication-helper dependencies were checked with the installed readelf and are present in the image's system libraries.

Build:

```bash
(cd .local/qnx-lab &&
 mkqnximage --type=qemu --arch=x86_64 --cpu=1 --ram=1G \
   --graphics=no --tcg=no --hostname=resmgrcheck \
   --ssh-ident="$HOME/.ssh/id_ed25519.pub" --build > build.log 2>&1)
```

`--tcg=no` here controls Trusted Computing Group/TPM image features, not QEMU's software accelerator. No new host keys were generated because both existing keys were present before image generation.

## Launch the isolated lab

Check no other process owns the selected port or image. The initial check found no listener at 22220 and no running QEMU. Do not change host services/firewalls.

```bash
ss -ltn
id
getent group kvm
qemu-img create -f qcow2 -F vmdk \
  -b "$PWD/.local/qnx-lab/output/disk-qemu.vmdk" .local/qnx-lab/run.qcow2
```

The account is already assigned to kvm; the agent's original supplementary groups did not include it. `sg kvm` applies that existing assignment without changing device permissions. Launch from the repository root:

```bash
sg kvm -c 'qemu-system-x86_64 -accel kvm -cpu host -smp 1 -m 1G \
 -drive file=.local/qnx-lab/run.qcow2,format=qcow2,if=ide,id=drv0 \
 -kernel .local/qnx-lab/output/ifs.bin -display none \
 -netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:22220-:22 \
 -device virtio-net-pci,netdev=net0 \
 -chardev stdio,id=console,mux=on,signal=off,logfile=.local/qnx-lab/console-phase1.log \
 -serial chardev:console -mon chardev=console,mode=readline \
 -object rng-random,filename=/dev/urandom,id=rng0 \
 -device virtio-rng-pci,rng=rng0 -no-reboot'
```

Use a new overlay/log name for another clean run. Keep the descriptor and its relative `disk-qemu` backing file together. An explicit writable overlay avoids the earlier restricted context's implicit `-snapshot` temporary file failure at /var/tmp. The tested target uses KVM; the older TCG image had an unresolved SSH memory fault and is not a qualified transport fallback.

## Host identity and local SSH configuration

Before connecting, read the existing image's **public** `ssh_host_ed25519_key.pub` and put its key type/base64 fields into an exact `[127.0.0.1]:22220` entry in ignored `.local/qnx-known-hosts`. This trusts the image's local key, not an unauthenticated network scan. Keep private keys local and unchanged.

The verified ignored `.local/ssh_config` contains:

```sshconfig
Host resmgrcheck-qnx
    HostName 127.0.0.1
    Port 22220
    User root
    IdentityFile /home/mignon/.ssh/id_ed25519
    IdentitiesOnly yes
    UserKnownHostsFile /home/mignon/projects/resmgrcheck/.local/qnx-known-hosts
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
```

Adjust only machine paths for another authorized setup. Wait for the console's startup-complete marker; an early connection during boot timed out during banner exchange. A subsequent connection succeeded without weakening verification.

## Verified build/transfer/run

```bash
timeout 15s ssh -F .local/ssh_config resmgrcheck-qnx 'mkdir -p /data/resmgrcheck'
timeout 15s scp -F .local/ssh_config build/qnx-x86_64/hello resmgrcheck-qnx:/data/resmgrcheck/hello
timeout 15s ssh -F .local/ssh_config resmgrcheck-qnx \
 'chmod 755 /data/resmgrcheck/hello; uname -a; /data/resmgrcheck/hello; echo run1_exit=$?; /data/resmgrcheck/hello; echo run2_exit=$?'
timeout 15s scp -F .local/ssh_config resmgrcheck-qnx:/data/resmgrcheck/hello .local/evidence/hello-returned
cmp build/qnx-x86_64/hello .local/evidence/hello-returned
timeout 15s ssh -F .local/ssh_config resmgrcheck-qnx '/proc/boot/capabilities; echo capability_exit=$?; pidin ar'
```

Modern OpenSSH scp used its SFTP subsystem. Both transferred runs exited zero, the returned binary matched SHA256, and the capability probe exited zero. Native source/build identities and the actual outputs are E005 in [TEST_EVIDENCE.md](TEST_EVIDENCE.md). Check each command's status; printing a later success does not establish earlier commands passed.

No `server-monitor` or `slm` was running in this image, and startup files contain no monitor launch. Do not disable monitoring on unrelated systems. Reinventory if the image changes.

Stop only this guest through its console or SSH:

```sh
[ "$(uname -s)" = QNX ] && shutdown -S reboot
```

QEMU's `-no-reboot` exits on that guest reboot. Never issue an unguarded host shutdown. Closing SSH alone does not prove remote test processes stopped.

## References

- [QNX qcc](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/q/qcc.html)
- [QNX mkqnximage](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/m/mkqnximage.html)
- The installed SDK's `host/common/mkqnximage` scripts were inspected for identity reuse and generated file paths.
