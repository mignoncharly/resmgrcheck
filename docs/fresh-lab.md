# Set up your own QNX 8 lab

Use an owned Linux x86_64 development machine with an installed, locally licensed
QNX SDP 8.0, Make, Git, Python 3.10+, OpenSSH, QEMU and working KVM access.
This guide creates a separate guest and new host keys. It needs no files from the
author's bootstrap and does not install or license the SDK for you.

Fresh-lab qualification is tracked separately from historical clean-source tests
against the reused guest. Follow the actual evidence record for the observed result;
instructions alone are not proof of successful reproduction.

## 1. Build the native tools

Clone the published repository, enter its root and load your installed SDK:

```sh
git clone https://github.com/mignoncharly/resmgrcheck.git
cd resmgrcheck
source "$HOME/qnx800/qnxsdp-env.sh"
make qnx QNX_VARIANT=gcc_ntox86_64
```

Change the SDK path if yours differs. The build must use `qcc`; a Linux binary
does not satisfy this step. Keep this checkout for source provenance.

## 2. Create a new guest directory

Use a new ignored directory. If it exists, inspect it and choose another name.
Do not replace an existing guest or remove old evidence. From the repository root:

```sh
mkdir -p .local
mkdir .local/fresh-lab
mkdir -p .local/fresh-lab/local/snippets
```

In `.local/fresh-lab/local/snippets/ifs_files.resmgrcheck`, write the following.
Replace `REPO` with this checkout's absolute path:

```text
[uid=0 gid=0 perms=0555] /proc/boot/hello-qnx=REPO/build/qnx-x86_64/hello
[uid=0 gid=0 perms=0555] /proc/boot/capabilities=REPO/build/qnx-x86_64/capabilities
[type=link] /usr/libexec/sshd-auth=/system/bin/sshd-auth
[type=link] /usr/libexec/sshd-session=/system/bin/sshd-session
```

In `.local/fresh-lab/local/snippets/system_files.resmgrcheck`, write:

```text
[uid=0 gid=0 perms=0555] bin/sshd-auth=usr/libexec/sshd-auth
```

Build using your own existing client **public** key:

```sh
cd .local/fresh-lab
mkqnximage --type=qemu --arch=x86_64 --cpu=1 --ram=1G \
  --graphics=no --tcg=no --sshd-pregen=yes --hostname=resmgrcheck-fresh \
  --ssh-ident="$HOME/.ssh/id_ed25519.pub" --build
cd ../..
```

Use your actual public-key filename. `--sshd-pregen=yes` generates this guest's
host keys in its local directory; keep the private files there and out of Git.
The installed image scripts support that option. `--tcg=no` controls TPM image
features; it does not select the QEMU accelerator. This guide requires KVM.

## 3. Boot without changing existing services

Check available memory, KVM permissions and listeners. Port 22221 must be free.
Use a different loopback port if it is occupied and update the SSH entry below.
Do not stop an unrelated VM, change a firewall or weaken KVM device permissions.

```sh
free -h
ss -ltn
qemu-img create -f qcow2 -F vmdk \
  -b "$PWD/.local/fresh-lab/output/disk-qemu.vmdk" .local/fresh-lab/run.qcow2
qemu-system-x86_64 -accel kvm -cpu host -smp 1 -m 1G \
  -drive file=.local/fresh-lab/run.qcow2,format=qcow2,if=ide \
  -kernel .local/fresh-lab/output/ifs.bin -display none \
  -netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:22221-:22 \
  -device virtio-net-pci,netdev=net0 \
  -serial file:.local/fresh-lab/console.log -monitor none \
  -object rng-random,filename=/dev/urandom,id=rng0 \
  -device virtio-rng-pci,rng=rng0 -no-reboot
```

Leave that process in its terminal and use a second shell for the remaining steps.
If your account is already assigned to the KVM group but your session lacks it,
start a new group-aware login/session. Do not install a new group policy as part
of this exercise. The guest is an isolated lab using root, not a production recipe.

## 4. Trust your guest's public host key locally

Take the key type and public-key data from
`.local/fresh-lab/local/misc_files/ssh_host_ed25519_key.pub`. Create
`.local/fresh-known-hosts` with exactly this host and your public fields:

```text
[127.0.0.1]:22221 ssh-ed25519 YOUR_GUEST_PUBLIC_KEY_DATA
```

Use public material from the generated image, not an unauthenticated network scan.
Never copy a private host key into known_hosts. Create `.local/fresh-ssh-config`:

```sshconfig
Host resmgrcheck-fresh
    HostName 127.0.0.1
    Port 22221
    User root
    IdentityFile /ABSOLUTE/PATH/TO/YOUR/CLIENT/PRIVATE/KEY
    IdentitiesOnly yes
    UserKnownHostsFile /ABSOLUTE/REPO/.local/fresh-known-hosts
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
```

Only the private-key **path** belongs in this config. Wait for startup to finish in
the console log, then check the new guest:

```sh
ssh -F .local/fresh-ssh-config resmgrcheck-fresh \
  'uname -a; uname -p; /proc/boot/hello-qnx; /proc/boot/capabilities'
```

Check each probe's output and exit. Successful SSH is not native capability proof.

## 5. Configure and deploy

The helper hashes the actual IFS and creates a new 0600 configuration. It never
overwrites an existing file and never reads a private key or SDK license:

```sh
python3 scripts/configure-target.py --ssh-alias resmgrcheck-fresh \
  --ssh-config .local/fresh-ssh-config --ifs .local/fresh-lab/output/ifs.bin
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck doctor --target lab
```

Before deployment, doctor may return 3 for UNKNOWN transfer/engine checks.
After deployment require its actual readiness checks. If the normal configuration
already exists, use `--out .local/fresh-target.json` on the helper and
`--config .local/fresh-target.json` on **every** target CLI command. Preserve the
original configuration and native lab.

Continue with [the codelab](codelab.md), using that same configuration. Preserve
both source checkouts, real build/run identities and all evidence. Share only the
reviewed nonsecret observations in [the independent feedback form](independent-validation.md).

## 6. Stop only this guest

After verifying test cleanup, shut down the exact configured guest:

```sh
ssh -F .local/fresh-ssh-config resmgrcheck-fresh \
  '[ "$(uname -s)" = QNX ] && shutdown -S reboot'
```

The QEMU `-no-reboot` option exits on that guest reboot. A disconnected SSH session
alone does not establish that test processes were reaped. Preserve image/log/evidence
files locally for any failed attempt. Do not publish licensed runtime images.
