# ResMgrCheck: jury start here

ResMgrCheck checks whether a QNX resource manager fulfils its declared cancellation
and client-lifecycle obligations. A timeout return alone does not prove that the
server released a pending request or can serve the next client. The tool records
those facts separately, preserves the evidence, and replays the same contract
against an explicitly selected candidate build. Sensor and job services use the
same native runner, worker and evaluator.

The later [impact and innovation extension](submission/impact-innovation.md) adds
a return-code comparison, bounded native cycle reduction and an independently
authored QFuse backend probe. Its source and native evidence are in the repository;
the existing public jury ZIP and deployed application retain their earlier versions.

## Route A: Review without QNX (about five minutes)

No SDK, account, network connection or access to the author's server is needed.
Download the [public jury ZIP](https://github.com/mignoncharly/resmgrcheck/releases/download/hackathon-review-2026-11-14/resmgrcheck-jury.zip)
first, or use the [public recorded-evidence explorer](https://qnx-resmgrcheck.gestionatech.de/demo/)
without downloading. The network is needed for those downloads/hosted pages;
the extracted ZIP is self-contained for offline review.
Extract the dedicated jury ZIP completely, then open its **START_HERE.html** in a
browser. Keep the directory tree together; opening HTML inside a ZIP preview can
break evidence links. This Markdown guide also works in a repository checkout.

1. **Watch the real 170-second demonstration.** In the jury ZIP, open
   [demo.mp4](../demo.mp4). It has English on-screen explanations and no audio;
   [optional subtitles](submission/demo.srt) are included. A public YouTube URL has not
   yet been verified. The MP4 is intentionally excluded from Git; in a checkout,
   download the jury ZIP from the public release above. This is a recording of actual QNX
   execution, including an explicitly labelled project-owned fixture defect.
2. **Open the deliberate sensor failure:**
   [before-fix report](evidence/phase10/executions/p10demo2-broken/report.html).
   In Cases, expand `timeout`. It records **FAIL**, with both
   `cancellation_not_completed` and `pending_state_not_released`.
3. **Follow the supporting observations.** Pending precondition passed: a pending
   request and live unblock were observed. Cancellation did not complete within
   its allowance, and subsequent state still showed pending 1. Click the event
   references beside each assertion to reach the report timeline; Evidence links
   expose the unchanged QNX JSONL stream, native status and sealed manifest.
   `fresh_client_health` is **NOT_RUN** because its prerequisite failed. Cleanup
   PASS does not establish service health. The independent failure reasons remain
   visible. A configured deadline alone is not evidence of timer expiry.
4. **Open the actual source-corrected replay:**
   [after-fix report](evidence/phase10/executions/p10demo2-after/report.html).
   It records **PASS**: native ETIMEDOUT 260, pending zero, and fresh-client value
   42 on that run's original fixture before cleanup. The saved profile and
   `ignore-unblock` setting are unchanged. This is a source fix, not a switch to
   another fixture mode. The earlier defective service was not restarted to prove
   that its own health recovered.
5. **Compare both builds:**
   [comparison report](evidence/phase10/comparison/report.html).
   `fixed` means the saved comparison found the same contract and compatible
   recorded target, a different fixture binary, and the former failures absent.
   Both original and candidate source/build identities remain recorded. Inspect
   the [exact patch](jury/source-fix.patch) and [identity index](jury/identities.json).
6. **Check reuse with a different service:**
   [job-service report](evidence/phase10/executions/p10demo2-job/report.html).
   Cancellation releases the waiter while retaining `job_exists=1`, `job_ready=0`;
   a fresh client completes/retrieves job 1 with value 420. Ordinary `devctl` and
   prepared `_IO_DEVCTL` paths are recorded. The runner and worker hashes match
   the sensor cases. Retained work is distinguished from a leaked waiter.

The [evidence index](jury/EVIDENCE_INDEX.md) maps obligations to exact event numbers,
run IDs and source identities. Reports and sealed evidence are existing genuine
Phase 10 material, copied byte for byte. Only the entry guide and index are new.
This package does not claim a new runtime execution, exhaustive concurrency,
memory-leak measurement, a fresh target, or an independent developer reproduction.

### Verdicts and command exits

| Verdict | Meaning |
| --- | --- |
| PASS | All required obligations for that recorded scope are established. |
| FAIL | A service contract obligation failed with sufficient evidence. |
| ERROR | Input, harness, infrastructure, evidence or cleanup prevents a valid conclusion. |
| UNSUPPORTED | A required capability is unavailable; coverage is not passed. |
| NOT_RUN | Work was withheld, for example after a failed prerequisite or contaminated state. |

Assertions can have different verdicts within one case. Cleanup and recovery are
separate facts. CLI execution exits are 0 complete PASS, 1 completed contract FAIL,
2 input/environment/harness/evidence/cleanup error, 3 unavailable required coverage,
and 130 interruption, in the documented precedence. Offline report/compare can
return 0 for successfully processing valid FAIL evidence. Release verification can
return 0 while its expected defective service cases remain FAIL.

## Route B: Reproduce on QNX

This route needs **your own authorized lab**. The author's private VPS, SDK,
guest images, SSH configuration and credentials are neither required nor supplied.
Allow setup time beyond the five-minute review. These are the qualified command
forms; this documentation update did not execute them again on a new target.

### 1. Prerequisites and checkout

Use Linux, Python 3.10+, Git, Make, OpenSSH with SFTP, an installed **locally licensed
QNX SDP 8.0** with `qcc`/`gcc_ntox86_64`, and an owned, already booted QNX 8.0.0
x86_64/x86pc guest. Obtain the SDK and runtime/image rights from QNX under the terms
applicable to you. Neither open-source project licensing nor this archive grants
a QNX license. No SDK, native executable or guest image is distributed here.

```bash
git clone --branch implementation/phase-1 --single-branch https://github.com/mignoncharly/resmgrcheck.git
cd resmgrcheck
mkdir -p .local
cp docs/jury/source-fix.patch .local/jury-source-fix.patch
git switch --detach 7d8326a454ecf6a1c190413cb9695395c8d2d5cd
source "$HOME/qnx800/qnxsdp-env.sh"
```

The final line is the qualified SDP layout with the home directory substituted;
use your actual installed `qnxsdp-env.sh` path. The patch is saved before selecting
the frozen product checkpoint. That checkpoint has the same runtime fingerprint
as the demo's original d9d2a1a source; new builds record their actual Git identity.
Use a Git checkout, not an extracted source-only archive, for build provenance.

### 2. Prepare your guest and SSH/SFTP route manually

The CLI does not install/license QNX, generate images, start VMs or create accounts
or authentication. Use your SDK's guest-creation instructions. The project's
[recorded QNX image/boot recipe](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/setup-qnx.md)
documents the tested KVM setup, image snippets and SSH helper links. Its bootstrap
key-copy step is historical: on your lab, supply **your own** host keys and client
public key, with local paths. Do not attempt to copy the author's bootstrap files.
An already functioning compatible lab may be used instead; fresh-image creation
was not part of the recorded reproduction.

The guest needs `/bin/sh`, `uname`, `id`, SSH command execution and an SFTP subsystem,
the required QNX libraries, permissions for the managed fixtures/process operations,
and writable `/data/resmgrcheck`. The qualified lab uses UID 0 in an isolated guest.
Keep unrelated services intact; inspect ownership and storage before choosing a lab.
The recorded guest has a small filesystem; the full release matrix needs space
for immutable deployments and retained evidence. Do not broadly remove files.

Create an ignored `.local/ssh_config` for **your own route**, for example a local
guest forwarded on loopback port 22220:

```sshconfig
Host resmgrcheck-qnx
    HostName 127.0.0.1
    Port 22220
    User root
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    UserKnownHostsFile .local/qnx-known-hosts
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
```

Pin the guest's public host key from a trusted image/console channel in
`.local/qnx-known-hosts`, using `[127.0.0.1]:22220` for that example. Do not disable
host-key checking. Configure a different alias/address if your lab requires it.
Check command execution and an actual SFTP transfer in your lab before proceeding:

```bash
ssh -F .local/ssh_config resmgrcheck-qnx 'uname -a; id -u'
sftp -F .local/ssh_config resmgrcheck-qnx
```

At the SFTP prompt, transfer and retrieve a harmless local file in your owned
directory, compare its bytes, then `bye`. This interactive prerequisite does not
launch a ResMgrCheck run. Establish `/data/resmgrcheck` with the expected lab owner.
Copy `config/targets.example.json` to ignored `config/target.local.json`. Set alias,
config path, UID, `8.0.0`/`x86_64`/`x86pc`, and the SHA-256 of **your actual booted
IFS recipe** (`sha256sum /your/guest/output/ifs.bin`). Replace the zero placeholder;
do not reuse the recorded lab's recipe hash to describe a different image.
Detailed configuration semantics are in the
[CLI guide](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/cli.md).

### 3. Doctor, validate, build and deploy

Run from the checkout root in the shell with the SDP environment loaded:

```bash
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck validate profiles/sensor.json
python3 -m resmgrcheck validate profiles/job.json
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck doctor --target lab
```

Before first deployment, doctor may exit 3 with UNKNOWN transfer/compiled capability
checks. Resolve host/SDK/reachability/compatibility errors, then build/deploy and
repeat doctor. UNKNOWN is not PASS. Deployment verifies actual transferred hashes;
local binaries merely existing do not establish target readiness.

### 4. Fixed sensor, deliberate failure and HTML reports

Use new output directories. These examples execute the single timeout family,
including ordinary/prepared/deferred baselines, matching the recording:

```bash
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite profile --fixture-mode fixed --out runs/jury-fixed
python3 -m resmgrcheck report runs/jury-fixed --out runs/jury-fixed/report.html
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite profile --fixture-mode ignore-unblock --out runs/jury-before
resmgrcheck_before_exit=$?
test "$resmgrcheck_before_exit" -eq 1
python3 -m resmgrcheck report runs/jury-before --out runs/jury-before/report.html
```

Expect fixed PASS/exit 0 and deliberate FAIL/exit 1 with both failure reasons from
Route A. Do not use `set -e` across an expected nonzero command without handling it.
The full `--suite lifecycle` broken run can exit 2 because it also establishes an
independent bounded departure-observation ERROR. Open the generated HTML directly.
Keep complete evidence trees and all attempts. After transport loss, use the printed
run ID with `status`/`collect`; do not relaunch an uncertain request.

### 5. Apply the recorded source correction

Keep this original checkout, builds and evidence. Create a separate worktree at the
same frozen source and copy only your own ignored target routing configuration:

```bash
git worktree add -b jury/fix-unblock ../resmgrcheck-jury-fix HEAD
cp config/target.local.json ../resmgrcheck-jury-fix/config/target.local.json
cd ../resmgrcheck-jury-fix
```

Edit that ignored config's `ssh_config` to an absolute path to **your** original
`.local/ssh_config`, so both checkouts use the same guest/host-key route. No private
key needs copying. Apply the saved patch using its actual original checkout path:

```bash
git apply --check ../resmgrcheck/.local/jury-source-fix.patch
git apply ../resmgrcheck/.local/jury-source-fix.patch
git diff --check
git add native/fixtures/sensor.c native/fixtures/job.c
git commit -m 'Complete live owned unblock requests'
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
```

The ten removed lines are the intentional ignored-unblock early returns. Preserve
default resource-manager bookkeeping, live `MsgInfo` ownership checks, `MsgError`
and pending removal. The archived patch is the actual 39b99d7 correction. Your
new commit/binaries will have their own recorded identities; do not relabel them
as the earlier run. No profile, timeout or saved fixture setting is changed.

### 6. Candidate replay and comparison

Still in the candidate checkout, select its manifest explicitly:

```bash
python3 -m resmgrcheck replay ../resmgrcheck/runs/jury-before/replay.json --target lab --candidate-manifest build/qnx-x86_64/manifest.json --out runs/jury-after
python3 -m resmgrcheck compare ../resmgrcheck/runs/jury-before runs/jury-after --out runs/jury-comparison
python3 -m resmgrcheck report runs/jury-after --out runs/jury-after/report.html
python3 -m resmgrcheck report runs/jury-comparison --out runs/jury-comparison/report.html
```

Expect replay PASS/exit 0 and comparison `fixed` only when the saved contract and
recorded target are compatible. A `--fixture-mode fixed` switch changes settings
and is an incomparable control contrast, not this source-fix proof. Without an
explicit candidate, replay selects the original immutable deployment.

### 7. Restore original deployment, test the second service and verify release

The release matrix intentionally expects the planted defects. Return to the
unchanged checkout and restore its original deployment before running it:

```bash
cd ../resmgrcheck
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck run --target lab --profile profiles/job.json --suite profile --fixture-mode fixed --out runs/jury-job
python3 -m resmgrcheck report runs/jury-job --out runs/jury-job/report.html
python3 -m resmgrcheck verify --target lab --suite release --out runs/jury-release
```

Expect job PASS/exit 0, retained-job/fresh-retrieval facts from Route A, and release
checker exit 0 **only if all 36 expected outcomes match**. The recorded matrix has
12 PASS, 19 FAIL, 2 ERROR and 3 UNSUPPORTED individual cases. Never rewrite those
verdicts or remove unsupported coverage to make the checker green. Full managed
lifecycle is available through `--suite lifecycle`; external attachment is scoped
read-only health, without the private observer/build identity needed for lifecycle.

For the extended walkthrough and boundaries, see the
[codelab](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/codelab.md),
[report guide](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/reports.md),
[actual evidence](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/TEST_EVIDENCE.md)
and [limitations](https://github.com/mignoncharly/resmgrcheck/blob/7d8326a/docs/KNOWN_LIMITATIONS.md).
Those source links require a network; every report/evidence link in Route A works
locally in the extracted jury package.
