# Test evidence

## E022: Native reduction and independently authored backend integration

2026-11-14. Clean source5e1fb8a, runtime source-tree SHA256
`46d1ffdbcbe9cd9a017a5a34e31fd8b63d4626aad2d813046d2765dc4337122b`
was qualified on the separate QNX8.0.0 x86_64/x86pc KVM review guest. The
[machine index](evidence/impact-innovation/qualification/index.json) is authoritative
for exact source hashes/builds. Installed qcc/gcc_ntox86_64 and Make were reused;
the existing core C binaries were unchanged and the optional external probe was
compiled/linked with qcc, C11, Wall/Wextra/Werror. No SDK/image/binary/license material
was added to Git. Pinned MIT QFuse source and LGPL libfuse dependencies remain
ignored downloads with their original license texts and checked hashes.

`python3 -m unittest discover -s tests/host -q`:131 passed. The final native command
matrix is in [commands.json](evidence/impact-innovation/qualification/commands.json):

- Both sensor/job baselines PASS; both deliberate retain-waiter cases FAIL with
  pending1 despite a matching ETIMEDOUT260. All four derived limited return
  predicates are SATISFIED; canonical results remain unchanged.
- Both original20-cycle retain-third inputs FAIL at the third cycle, with later
  work NOT_RUN. Both bounded searches record1 PASS,2 PASS,3 FAIL with the same
  pending-state failure signature, verified original-instance observations and
  owned cleanup. All smaller counts were tested once on new instances.
- Both separate one-attempt budgets stop as budget_exhausted after1 PASS, without
  a minimum claim. A preserved first search stopped at ERROR instead of continuing.
- Both pinned QFuse timeout/signal probes PASS: cancelled client returns260/4
  before release, public admin status observes retained callback/cancellation,
  another path returns byte81, callback drains after release, both children are
  reaped and mount disappears. The backend is unchanged; workload/harness are ours.

Sixteen native executions matched expected outcomes:14 sealed ABI1 bundles and2
separate scoped integration records. Service defects remain FAIL. All14 canonical
executions were inspected and14 reports rendered. Four relevant new reports passed
12 Chromium views (desktop, narrow, JavaScript disabled), artifact/anchor links,
keyboard disclosure, no overflow, no external requests/page errors and unchanged
source bytes. See [browser evidence](evidence/impact-innovation/qualification/browser/index.json).

The initial qualification preflight lacked sourced SDK variables and stopped
before native cases. After sourcing the installed environment, the first reduction
established two PASS cycles and a third-cycle service FAIL, but the old evaluator
classified an aborted final requested cycle as a coverage ERROR. The reducer stopped
as designed. Its [original sealed bundle](evidence/impact-innovation/trials/final-cycle-error/bundle.json)
and ERROR result remain unchanged at source21bf7f4. The correction marks known final
failure coverage NOT_RUN while retaining the established FAIL; missing observations,
unknown cleanup and other uncertainty still yield ERROR. Regression uses the actual
recording plus explicitly synthetic missing-observation checks. Final qualification
used new run IDs and clean5e1fb8a; no old result was relabelled.

The first QFuse contract incorrectly expected cumulative cancelled_waits to become
zero. Its [FAIL record](evidence/impact-innovation/trials/cumulative-counter-assumption/result.json)
is preserved. Source inspection established the count increments until pool restart;
the corrected contract checks drainage of active operations/cleanup and stability
of cumulative cancellations. This is our contract correction, not an upstream bug.

Original lab selection and the build manifest were preserved; the fresh-review
selection was restored. The final separate-guest capacity check showed2637 available
file entries of3072. The separate guest was then gracefully stopped with exact
QEMU identity checks; its listener disappeared and the original lab listener
remained. [Guest-stop evidence](evidence/impact-innovation/guest-stop.json) records
that cleanup. No production deployment, YouTube publication, external contact
or independent validation occurred. The [review guide](submission/impact-innovation.md)
explains inputs, scope, reproduction commands and the judging relevance without
invented adoption, debugging savings, hardware timing or win-probability claims.

## E021: Production explanation release and compatible rollback passed

2026-11-14. The operator provided the final successful JSON for exact driver
b289dc3, application 7ecb812: HTTPS/browser and full application rollback passed;
native W036 acceptance retained/not rerun; independent UAT pending. The agent did
not execute the privileged drill or reread its protected receipts. W043 and
[the operator result](web/evidence/evidence-story-release/operator-result.json)
identify that evidence source explicitly.

Separate agent observations confirm the active 7ecb812 pointer, HTTPS200 readiness,
all three public recorded case pages with the new explanations, and healthy
web/executor metadata. [Public checks](web/evidence/evidence-story-release/public-checks.json)
and [service checks](web/evidence/evidence-story-release/services.json) preserve the
observations. The earlier original-pointer discrepancy is resolved. Records-only
follow-up: no native build, target run, full host/web matrix or deployment repeated.
YouTube remains held as a draft; independent UAT/developer feedback remain pending.

## E020: Public source and downloadable review assets, 2026-11-14

Atomic normal fast-forward publishedb289dc3 to public main/feature. The actual
source correction570a956 was published to qualification/hackathon-fresh-fixed;
implementation/phase-1 and historical native identities remain untouched.
Releasehackathon-review-2026-11-14 contains the original portable evidence ZIP
(SHA25675b7335266f4278d3fbd44eee7a83c76870a8055af53af3f83c06d3bcec5f072),
the150s actual video edit(SHA25654014dc7bf996ce52c00d989f9a41efb2064be934161962bc9a38a7bf64e1be4)
and their checksum file. No SDK/image/executable/private config/key is included.

An anonymous verifier used no Authorization header: public repository/MIT license
detection, exact main SHA, five public raw source files and all three downloaded
asset byte/hashes matched. [Publication receipt](evidence/hackathon-improvements-20261114/publication.json)
records the actual source/asset identities. Source publication is separate from
the currently deployed immutable application. The description/homepage/topics are
set through normal GitHub account access; no privacy or permissions changed.

Read-only plan for deploy_evidence_story.py at exactb289dc3 passed. User was given
the concrete local sudo command; actual production round-trip receipts remain
pending. YouTube media import and exact draft creation succeeded for the selected
channel, but no publish call was made without final draft approval. Independent
developer feedback/UAT, entrant attestations and Devpost submission remain pending.
The new readiness-current.json distinguishes these from the historical preparation
snapshot; later docs do not relabel old native recordings or create new target proof.

## E019: Fresh-target proof, browser checks and release preparation, 2026-11-14

The source7ecb812 checkpoint was committed/clean. Real Make/qcc build metadata binds
that source. A newly generated QNX8.0.0 x86_64 KVM image/host keys booted separately.
Actual hello/native capability probes passed. Fresh target qualification passed
four native cases: baseline PASS, intentional sensor defect FAIL, job PASS and
source-corrected replay PASS. Original and actual corrected source570a956, full
build hashes, exact IDs, cleanup and comparison are preserved unchanged in
[the fresh-target evidence](evidence/fresh-target-20261114/README.md).
The original lab deployment selection/build manifest were preserved byte-for-byte.
Only the new guest was shut down after cleanup; fresh22221 listener closed and
original22220 remained. This is fresh-target agent reproduction, not independent UAT.

Two setup omissions were found/fixed in the guide: create the private target root
before bootstrap, and choose a distinct local target name for a second guest.
A first local orchestration logger failed after root creation, before any native
case/deploy; that attempt remains local and the successful attempt has separate output.

The installed browser environment now has an explicit executable option because
its Playwright default expected an absent browser version. Using installed Chromium,
`tests/browser/qualify_reports.py` passed15 reports/45 laptop/narrow/no-JS views:
no external requests/overflow/page errors; original source/evidence and JUnit bytes
unchanged. The initial default-browser failure is retained locally. Packaging the
historical jury evidence succeeded with178 checked references, without relabelling
historical native source or touching original bundles. Its original170s video remains.

An edited150s video removes original seconds0–20 and retains20–170 chronologically.
ffprobe confirms150.000s/H.264/no audio; sampled frames were inspected. It opens
with the labelled intentional failure, retains source correction/replay/departure/job,
and keeps original execution identities. The original file remains unchanged.
The selected YouTube channel is @mignoncharly; exact draft approval is pending.
See submission/video-edit-20261114.json; import/draft creation is not publication.

The first full web suite ran483 tests and failed6+1error: three tests omitted their
production hostname from ALLOWED_HOSTS; four preparation fixture checks inherited
the umask changed by earlier modeled release tests. Fixtures now declare their
hostname/modes, and release tests restore umask. Production settings were unchanged.
Focused34 tests pass. Refreshed full isolated staging suite:492 tests PASS in123.988s;
test database destroyed.24 release-helper tests pass in0.063s with root/services
modeled. The new immutable presentation/compatible app rollback driver is prepared;
actual local-root execution and independent UAT remain pending. See
[the check summary](evidence/hackathon-improvements-20261114/checks.json) and
web/EVIDENCE_STORY_DEPLOYMENT.md. Source scan found only the intentionally incomplete
key marker in the existing rejection test, no private key material or ELF.

## E018: Hackathon improvement checkpoint, 2026-11-14

Owner approved six priorities. Initial sourcecc851a9 on feature/production-web-ai
was clean. No independent tester is available (owner reply); an exercise and safe
feedback form are prepared in independent-validation.md. No outreach was sent.

Shared plain-language story views describe only saved assertions and retain exact
verdicts/references. Web raw details remain available in keyboard disclosures.
The private config helper hashes IFS bytes, validates routing types and exclusively
creates0600 files; occupied/symlink destinations are preserved. Fresh-lab docs use
new generated guest keys rather than the author's bootstrap. Packaging binds its
own current source separately from the recorded native runtime identity.

Actual checks on the changed working tree:

- `python3 -m unittest discover -s tests/host -q`:117 tests PASS in14.636s.
- Existing isolated staging venv, `web/ops/staging.py manage.py test
  tests.test_dashboard --noinput`:10 tests PASS in7.402s; disposable test DB removed.
  Initial sandbox access failed; authorized host execution passed.
- `python3 -m unittest web.tests.test_navigation_release
  web.tests.test_security_release -q`:15 tests PASS in0.037s; root/services modeled.
- Installed mkqnximage built a new image under ignored .local/fresh-lab-20261114:
  exit0 in4.0s, own host keys, no bootstrap/key/image copied. A new KVM guest booted
  on previously unused loopback22221. Native connectivity/reproduction pending.
- Host-origin service observation: web/executor active; current symlink names
  dfe1060. No protected deployment receipt was read; sudo requires a local password.

No production mutation, native-matrix repetition, independent reproduction, new
public upload or completed submission is claimed at this checkpoint. Next: fresh
guest probes and clean-source behavior proof, browser qualification and consistent
release delivery. Historical evidence remains unchanged.

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

## E002: Actual repository build attempt, 2026-11-06

**State:** build failed; repository-native execution blocked. Executed by the agent, distinct from E001.

The intended workspace was empty and not a Git repository. The agent cloned `implementation/phase-1` directly into it. Initial `git status --short --branch` showed a clean checkout at `cd1ecf809a78dab223297b48d57f8a6488a92786`. No workspace contents were removed.

Command executed before any source changes:

```bash
source /home/mignon/qnx800/qnxsdp-env.sh && make qnx
```

Make invoked:

```text
qcc -Vgcc_ntox86_64 -std=c11 -Wall -Wextra -Werror "native/spikes/hello.c" -o "build/qnx-x86_64/hello"
```

The compiler waited without output, then reported a licensing failure and six lock-acquisition timeout diagnostics. The operative diagnostic was:

```text
Lockfile (/home/mignon/.qnx/license/licenses.lck) acquisition timed out after 10 seconds. Check that the file and containing folder have write permissions set for this user, and that no other processes are using this file
make: *** [Makefile:12: build/qnx-x86_64/hello] Error 129
```

Actual Make process exit: **2**. A separate unbounded `qcc -V` attempt also exited **129** with the lock diagnostic. Bounded compiler probes returned **124** (timeout); these did not provide a compiler version. Native source SHA256: `7ef116b3ddb0f829a290887c4cee28df182d0a06d8aeb5cc84386e5cd9904947`. No output executable was produced, transferred, or run. There are no repository runtime outputs or statuses to report.

An independent metadata probe using `os.statvfs()` confirmed `ST_RDONLY` on `/home/mignon/.qnx/license`; no license files were read, copied, edited, or unlocked. This execution-context restriction is sufficient to prevent the normal compiler license lock. The compiler's generic invalid-license message does **not** establish that the operator's installed license is invalid.

The initial compiler output was returned by the tool session; the text above is a selected command/result record, not a reconstructed raw log. E004 retains the later preflight output as a local file.

## E003: Agent-run QNX image inventory, 2026-11-06

**State:** real QNX inspection passed; repository build/run gate remains blocked.

The agent copied `ifs.bin`, `disk-qemu`, and its VMDK descriptor from the operator's image into ignored `.local/qnx-vm/`. SHA256 checks after the run confirmed each copied input still matched the original:

| Input | SHA256 |
| --- | --- |
| `ifs.bin` | `11ec3c0f02f119c03c7c64d0ddd9c2f05c0e840d8270a80538898c2aedb18667` |
| `disk-qemu` | `8f7ea89eb38e5c6d690477e0d2844978b184e1adc84f89717b45325e1d57c7e7` |
| `disk-qemu.vmdk` | `2b60cc7974f882f097af4c832831bda18164299b0d538ee68aca89ebd95825c6` |

The original bootstrap console log remained at SHA256 `bdaab6672a75a5640ddb8512502bb64fba65e46d7c6355496635315088c501e6`. No original image or log was overwritten. These inputs predate the repository; no revision-built binary was included.

KVM launch failed with `failed to initialize kvm: No such file or directory`. This process does not inherit the operator's active KVM group. `sg kvm -c id` failed with `Cannot open audit interface - aborting.` No host service or group configuration was changed. TCG was used for inspection only.

`-snapshot` failed to open a temporary file in read-only `/var/tmp`, including with `TMPDIR=/tmp`. Instead, the agent created an explicit disposable overlay:

```bash
qemu-img create -f qcow2 -F vmdk \
  -b /home/mignon/projects/resmgrcheck/.local/qnx-vm/disk-qemu.vmdk \
  .local/qnx-vm/inspection.qcow2
qemu-system-x86_64 -accel tcg -cpu max -smp 1 -m 1G \
  -drive file=.local/qnx-vm/inspection.qcow2,format=qcow2,if=ide,id=drv0 \
  -kernel .local/qnx-vm/ifs.bin -display none -nic none \
  -chardev stdio,id=console,mux=on,signal=off,logfile=.local/qnx-vm/console-inspection.log \
  -serial chardev:console -mon chardev=console,mode=readline \
  -object rng-random,filename=/dev/urandom,id=rng0 \
  -device virtio-rng-pci,rng=rng0 -no-reboot
```

The guest reported `QNX resmgrcheck 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64`. `pidin ar` showed no `server-monitor` or `slm`, and the generated startup files contained no monitor launch. A pipe manager was running. This is a snapshot of this lab image, not evidence that all required native APIs have been exercised.

`/usr/libexec/sshd-auth` and `/system/bin/server-monitor` were absent. `/system/bin/sshd`, `sshd-session`, and `sftp-server` were executable. The installed SDK provides `x86_64/usr/libexec/sshd-auth`, but the bootstrap's generated system build includes only `sshd-session`. This omission is a candidate image fix, not a tested SSH solution. This TCG boot reported `Memory fault (core dumped)` during SSH startup; its cause remains unestablished. The operator's KVM log had instead reported a missing helper.

Retained raw console: `.local/qnx-vm/console-inspection.log`, SHA256 `228a25c836a2e239b7927adc5df337a6d98b0604d21895199ba1b2a7a3c95d53`. [Reviewed console excerpt](evidence/2026-11-06-target-inventory.txt) removes CR characters and excludes the printed SDK startup script. The guest was stopped with the guarded `shutdown -S reboot`; QEMU exited **0**.

The SDK headers `sys/dispatch.h`, `sys/iofunc.h`, `sys/neutrino.h`, `sys/iomsg.h`, `sys/resmgr.h`, `time.h`, `spawn.h`, `sys/wait.h`, `poll.h`, and `unistd.h` are present. No compile/link or runtime probe of these interfaces succeeded in this session. Native facility acceptance remains open.

## E004: Host preflight and transport/commit restrictions

**State:** expected host checks observed; native gate still blocked.

- Host tools observed: Ubuntu 24.04.3, Python 3.12.3, GNU Make 4.3, OpenSSH 9.6p1, QEMU 8.2.2. GCC 12.2.0 remains an operator observation because the current `qcc -V` failed.
- With the local Makefile and preflight changes (base revision E002, dirty tree), SDK-enabled `make qnx` reports `BLOCKED: QNX license directory is on a read-only filesystem; qcc cannot acquire its license lock` and exits **2** promptly. Log: `.local/evidence/build-preflight.log`. The preflight checks environment and directory metadata only; it neither invokes the compiler nor validates a license.
- A QEMU launch with `-netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:22220-:22` failed to set up the forwarding rule (exit **1**). An independent Python `socket.socket()` probe failed with `PermissionError: [Errno 1] Operation not permitted` before binding. No SSH connection/transfer was tested.
- `git add Makefile scripts/check-qnx-build.py` failed with `Unable to create .../.git/index.lock: Read-only file system` (exit **128**). `os.statvfs('.git')` confirmed `ST_RDONLY`. The subsequent commit command was not reached. No checkpoint commit exists; final changes remain uncommitted at E002's HEAD.

Resume in an authorized context allowing normal SDK license-lock writes, Git metadata updates, and loopback sockets. Do not infer a passing Phase 1 gate from this preflight, the prior operator smoke program, or the copied-image inventory. Phases 2–10 remain not run.

## E005: Phase 1 gate passed after Full Access, 2026-11-06

**Provenance:** commands and real target execution performed by the agent after the user restored Full Access. Supersedes the active restrictions of E002–E004; their historical outcomes remain unchanged.

Initial SDK-enabled `make qnx` exited **0**; `qcc -V` exited **0** and reported GCC 12.2.0 / `gcc_ntox86_64` default. This establishes normal license acquisition without inspecting/changing license contents. A write/remove probe under `.git` and an actual loopback socket bind/listen both passed. The account's existing `kvm` membership was applied by `sg kvm`; no host permission changes were made.

Native sources and Makefile were committed as **`11f7729fcb73c73b9ca7d29c8ec7aed818b14c57`** before `make -B qnx` and target execution. Only documentation/evidence changes were uncommitted during that run. Both native targets built with `qcc -Vgcc_ntox86_64 -std=c11 -Wall -Wextra -Werror` (exit **0**). The executable interpreter is `/usr/lib/ldqnx-64.so.2`, x86_64 PIE.

| Artifact | SHA256 |
| --- | --- |
| `native/spikes/hello.c` | `7ef116b3ddb0f829a290887c4cee28df182d0a06d8aeb5cc84386e5cd9904947` |
| `native/spikes/capabilities.c` | `89cf812da21766d33a40f066a451a55c4e50c98e9923e7cf1a8cfc30aeefc8f7` |
| `build/qnx-x86_64/hello` | `5bc69f792a46fd07327e2f509ef7f6143e24a4e2324a9254a6a43628ebce587c` |
| `build/qnx-x86_64/capabilities` | `17b53ea44dbbdee33e72daf327a302f0670701a91a8e194f703cd816116373f4` |
| Dedicated `output/ifs.bin` | `6cb923cc6f93fb122c8d36d63a8359663681db0357d826d6890ea7ddbfdc254f` |

The original image/log were preserved. The dedicated image at ignored `.local/qnx-lab` reuses the existing client public key and bootstrap host keys, includes `sshd-auth` plus helper links, and built with the exact recipe in [setup-qnx.md](setup-qnx.md), exit **0**. No credentials were regenerated. The IFS snippet SHA256 is `6d782c9a611863d94787395820fd3087718ff8f98b220f41a0902c4da036c9c7`; helper system snippet SHA256 is `31c68afd510e6114e8e9437bc3b9f3d1623aa98293f776886d2da67561ae20ad`. These ignored snippets contain only the documented local paths/recipe, not licensed code.

QEMU 8.2.2 launched under KVM with `-cpu host`, one CPU and 1 GiB. An explicit qcow2 overlay contains guest writes. User networking uses `restrict=on` and `hostfwd=tcp:127.0.0.1:22220-:22`; no public listener or host firewall change. SSH uses BatchMode, IdentitiesOnly, and StrictHostKeyChecking with an exact host/port entry derived from the existing image's public host key. An initial connection before startup completed timed out during banner exchange; after startup, command execution and transfer succeeded.

Actual target identity: `QNX resmgrcheck 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64`. The embedded repository hello exited **0**. `/proc/boot/capabilities` exited **0**, with these real checks:

- Resource-manager dispatch creation, function-table setup, pathname attachment, dispatch context allocation/free, detach/destroy.
- Fork/wait and an actual child-to-parent native Channel/Connect/MsgSend/MsgReceive/MsgReply exchange.
- Bounded pipe/poll transfer, CLOCK_MONOTONIC progression, TimerTimeout receive cancellation with **ETIMEDOUT**.
- posix_spawn of the repository hello and bounded wait/reap.

`pidin ar` recorded no running `server-monitor` or `slm`, and this recipe's generated startup contains no monitor launch. `sshd` remained running; no SSH memory fault was observed in this KVM image. This is not an explanation or qualification of the earlier TCG fault.

The agent created `/data/resmgrcheck`, transferred `hello` using `scp -F .local/ssh_config` (OpenSSH's SFTP path), and executed the transferred binary twice through SSH. Both outputs were `QNX smoke test: hello`, with **run1_exit=0**, **run2_exit=0**, and SSH exit **0**. Upload and download each exited **0**. The returned binary's SHA256 matches the built hello above; `cmp` exited **0**. Commands used explicit 15-second host deadlines.

Reviewed actual logs: [build](evidence/phase1-build.txt), [toolchain](evidence/phase1-toolchain.txt), [QNX capability/inventory run](evidence/phase1-guest.txt), [two transferred runs](evidence/phase1-transferred.txt). Original raw local logs are `.local/evidence/phase1-*.log` and `.local/qnx-lab/console-phase1.log`; VM/runtime/key files stay ignored. These source-level primitive checks do not establish the Phase 2 deferred-cancellation contract.

## E006: Phase 2 defect, correction, replay and cleanup, 2026-11-06

**State:** Phase 2 gate passed on real QNX. The individual deliberately defective service results remain FAIL.

Native source and saved replay script were committed as **`8583071886adc4d2df9c8b4e7d1eae47feeab251`**, then rebuilt with `make -B qnx` in a clean source tree (exit **0**). Compiler/target/image are E005's qualified environment; the three new binaries were transferred through its verified SFTP route. The fixture defaults to corrected mode; `ignore-unblock` is an explicit regression mode. Initial debug runs exposed the SDK header-order requirement (`sys/iofunc.h` before `sys/dispatch.h` for typed OCB handlers); that compile error was fixed before the recorded revision. Debug runs first demonstrated both outcomes, then the final committed revision was replayed twice.

| Final binary | SHA256 |
| --- | --- |
| `sensor-fixture` | `10246ad117dd63c3d2c55e5cc74f6bd0c9707a9d98c6ec9da2859af527481cc2` |
| `sensor-client` | `b4c9dc0c4511ab509e2fb644b18ea1e2bd8271185ffdb6bd4454c700e96e6841` |
| `phase2-supervisor` | `ab3b5ccd0f13828b148944a3a0d022c1af8de4a02b33c054fad83e31b04af03d` |

Actual execution for each of the two replay invocations:

```bash
timeout 25s ssh -F .local/ssh_config resmgrcheck-qnx \
 'cd /data/resmgrcheck && sh phase2-replay.sh'
```

The first invocation also applied executable permissions after upload. Each replay script and SSH process exited **0** after observing the defective supervisor exit **1** and corrected supervisor exit **0**. The same inputs were used every time: 500 ms operation timeout, 2000 ms cancellation allowance, 10 s case execution bound, 2 s cleanup bound. No limits were increased to make a result pass.

Every case first verified ten matching bytes via ordinary read and native `_IO_READ`/MsgSendv, then established and released a deferred ordinary read. For the timed read, matching logical request/generation and source monotonic timestamps established the pending-before-deadline and live-unblock preconditions:

| Run/mode | Pending ns | Intended deadline ns | Observed unblock ns | Outcome |
| --- | --- | --- | --- | --- |
| 1 / ignore-unblock | 447868675029 | 448368650083 | 448369278644 | FAIL cancellation_deadline |
| 1 / corrected | 450701999427 | 451201974291 | 451202261944 | PASS cancellation_completed_and_healthy |
| 2 / ignore-unblock | 465565707427 | 466065682872 | 466066267832 | FAIL cancellation_deadline |
| 2 / corrected | 468374302464 | 468873948623 | 468874261173 | PASS cancellation_completed_and_healthy |

These are all target CLOCK_MONOTONIC values in decimal nanoseconds, not host wall time. The unblock timestamp is when the fixture handled the notification, not exact kernel timer expiry. Corrected client result times were `451202445061` and `468874439401`, both within the original deadline plus allowance. Both returned raw **-1**, captured QNX errno **260 / ETIMEDOUT**. Post-case state reported **pending=0, unblocks=1, completed=1**; a new ordinary client read succeeded on the same fixture instance before cleanup.

In both defect cases, the pending count remained **1** with **unblocks=1, completed=0** after the bound, and no client result had returned. The supervisor stayed responsive and recorded the intended failure. SIGTERM and SIGKILL each returned success when sent to its exact owned client PID, but the client remained unreaped at both 100 ms observation points. Stopping the owned fixture allowed both processes to be reaped (raw status 15). All four cases ended with **all_reaped=1, evidence_error=0**, followed by their actual verdict and final writer marker. A subsequent target `pidin ar` inventory found no sensor fixture/client/supervisor processes. No broad kill or host service change was used.

Reviewed complete target event streams: [run 1 defect](evidence/phase2-run1-ignore-unblock.txt), [run 1 corrected](evidence/phase2-run1-corrected.txt), [run 2 defect](evidence/phase2-run2-ignore-unblock.txt), [run 2 corrected](evidence/phase2-run2-corrected.txt). [Evidence index](evidence/phase2-index.json) retains source/binary/log hashes and key original timestamps. Raw target logs were downloaded before the next replay; local copies are `.local/evidence/phase2-run*.log`. Build log: `.local/evidence/phase2-build.log`; post-inventory: `.local/evidence/phase2-post-inventory.log`. The build log and final inventory also have reviewed text copies.

A host-only audit parsed these actual streams and asserted timestamp ordering, matching request/generation, final markers, expected error results and complete cleanup. That audit is a consistency check of real native evidence, not an additional QNX scenario or synthetic native result. See [native semantics and replay guide](phase2-native.md). Signal-interruption, client-departure obligations, repetition suites, adapter reuse, JSON contracts, and production supervision are later gates and are not claimed here.

## E007: Phase 3 contracts, generic adapters and job proof, 2026-11-06

**State:** Phase 3 acceptance gate passed. No Phase 4 production-supervision claim.

The initial checkpoint was clean at 55b6d3232d436234c4503af53e2c175435493733.
Phase 1 was not rerun. The sensor's changed adapter/observation path was specifically
requalified because Phase 3 refactored it. The same qualified QNX/KVM lab and
existing SSH identities were reused; no credentials or SDK were recreated.

The precommit qualification identifies that base plus dirty source digest
`ac642b507b1d21de0714cdb7c36d8bd86eb58fb9a46b4829ca7bc63d1f75e968`.
The Make-owned build record binds the relevant project source inputs, revision /
dirty state and actual binary hashes. The retained plans and index contain those
identities; source/digest equality was checked after qualification. This is an
actual dirty-source run, not a claim that the parent commit alone contained the
new implementation. A clean committed-source confirmation is recorded below when
performed.

Commands actually executed:

```bash
source /home/mignon/qnx800/qnxsdp-env.sh
make qnx
python3 tests/qnx/qualify-phase3.py --prefix p3gate1
python3 -m unittest discover -s tests/host -v
```

All exited zero. Native compile used qcc -Vgcc_ntox86_64 -std=c11 -Wall -Wextra
-Werror, RMC_EVENT_V1, CJSON_NESTING_LIMIT=12, pinned cJSON.c and libm. Early debug
compiles exposed missing explicit errno includes and libm linkage; both were fixed
before qualification. cJSON is pinned at 1.7.19 / c859b25 with exact file/license
hashes in third_party/cjson/REVISION.json; no build downloads occur.

Each case ran `./runner CASE-plan.json` inside the owned target directory
`/data/resmgrcheck/p3gate1`, with a 20-second outer SSH deadline. Each original
native stream was collected and evaluated offline by the same Python evaluator.
The full argv/status transcript is [commands.json](evidence/phase3/commands.json).
The native collector deliberately has no service verdict classifier.

| Case | Native exit | Host outcome | Native observations |
| --- | --- | --- | --- |
| sensor-corrected | 0 | PASS | ordinary/read-message parity; deferred release; live timeout; queue clear; fresh sample |
| sensor-defect | 0 | FAIL | pending/live unblock before original bound, then cancellation_not_completed and pending_state_cleanup |
| job-corrected | 0 | PASS | devctl/message parity; deferred WAIT_RESULT release; timeout removes waiter; job preserved; new client retrieves result |
| job-defect | 0 | FAIL | identical generic rules detect ignored unblock and retained waiter |
| unsupported | 3 | UNSUPPORTED | required signal capability absent; explicit preflight skip, no child launch |

All use the original 500 ms timeout / 2000 ms completion allowance, 10 s case bound
and 2 s cleanup bound. Source-stamped pending, deadline and matching unblock IDs
are in the native streams. Corrected results are raw MsgSendv -1 / QNX errno 260
ETIMEDOUT. Job post-cancel facts are job_exists=1, job_ready=0 with pending=0;
release completes that retained job, then a different client PID retrieves job_id=1,
value=420 on the same fixture instance. Its ordinary negative probe of nonexistent
job ID 2 returned raw devctl=2, captured errno=0, normalized ENOENT; both successful
ordinary devctl and explicit _IO_DEVCTL returned the same typed facts.

The same runner and worker binaries were used for both registrations. Core runner,
worker, plan/result logic and evaluator were checked for service-name branches;
the host test preserves that check. Only adapter/fixture/registration/profile files
contain the service-specific message layouts/facts.

All four uploaded binaries were downloaded by SFTP and matched SHA256 before
execution. Exact hashes are in [index.json](evidence/phase3/index.json). The native
manifest captured QNX 8.0.0 / build 2026/06/05-16:26:03EDT / x86_64, scheduling
policy 2 and priority 10; no explicit priority boost was requested. Defect cleanup
retained the measured owned-fixture stop escape; all cases reaped their exact
children. Post-run inventory found no residual generic worker/runner/fixture.

Nine invalid native commands (version, boolean timing, unknown operation, unsafe
path, ABI, duplicate keys, leading-zero number, trailing data and nesting) each
exited 2 with empty stdout, before manifest/event collection or child launch.
Their raw inputs, stderr and statuses are retained in the bundle. A host-invalid
profile (boolean job_id) was rejected with exit 2 before plan output or any target
invocation from that CLI. Missing capabilities were not reclassified as success.

Twenty-one host tests passed: strict profile/parser checks, replay/hash consistency,
mutations of the recorded QNX streams (truncation, keys/types/sequence/identity,
late pending, retained state, deleted job, wrong API convention, bad health,
missing worker-final, cleanup errors), original native outcomes, and generic-core
separation. Mutated cases are synthetic host tests, not additional native scenarios.

Reviewed bundle: [formats](formats-v1.md), [adapter guide](adapters.md), and
`docs/evidence/phase3/` containing full profile/plan snapshots, raw native JSONL,
evaluated results, build/command/rejection logs, readback hashes and final inventory.
Raw local originals, including downloaded executables, remain ignored under
`.local/evidence/phase3-p3gate1`. No binaries, SDK/runtime contents or private keys
were added to Git.

### E007 clean committed-source confirmation

The complete qualification was repeated after the passing checkpoint commit
`e871ab2` from a clean tree, using `make qnx` and
`python3 tests/qnx/qualify-phase3.py --prefix p3clean1`. All five native/evaluated
outcomes, nine native rejections, host rejection, readback hashes and final
inventory passed again. Build metadata records dirty=false and the same source
digest/binary hashes. [Clean-revision bundle](evidence/phase3-clean/index.json)
retains full revision identity, plans, raw observations, evaluated results and
command statuses. This confirms the actual checkpoint revision, not only the
precommit source snapshot. No prerequisite Phase 1/2 suite was restarted.

## E008: Phase 4 persistence and SSH-loss subgate, 2026-11-06

**State:** persistent-run/transport-loss subgate passed; Phase 4 remains in progress.
This is not the complete Phase 4 failure matrix.

Native/Python changes were tested at base revision b0f737a plus the exact dirty
source digest and artifact hashes in [index.json](evidence/phase4-persistence/index.json).
The current source digest was compared to that recorded digest after testing.
The new native persistence module built with the same actual qcc toolchain. No
SDK, credentials, image or host services were changed. Earlier direct debug runs
used fresh p4persist1/p4gate1 directories; the retained final qualification used
p4gate2 after stricter identifier/frame scalar checks were added.

Actual final commands:

```bash
source /home/mignon/qnx800/qnxsdp-env.sh
make qnx
python3 tests/qnx/qualify-persistence.py --prefix p4gate2
python3 -m unittest discover -s tests/host -v
```

All exited zero. The test helper uploaded the four generic-path binaries to
`/data/resmgrcheck/p4gate2` and verified their SFTP readback SHA256 values. The
native `--persist` launch creates an exclusive run directory, detaches its session,
redirects stdin to /dev/null and events/diagnostics to owned files, writes initial
status and acknowledges the supervisor PID. SIGCHLD disposition preserves child
reaping. Status uses file fsync plus atomic rename; complete status follows final
native events. Foreground operation and ABI 1 remain available.

| Actual QNX case | Transport observation | Collected result |
| --- | --- | --- |
| normal job | successful launch acknowledgement, later reconnect | PASS, complete target status, cleanup_ok true, no unresolved children |
| intentional sensor defect | pending timed request confirmed; active host SSH client terminated with SIGTERM (local exit -15); reconnect | FAIL cancellation_not_completed / pending_state_cleanup; complete collection, preserved failure, cleanup_ok true, no unresolved children |

The second case kept an SSH channel open with a harmless stdin reader after the
start acknowledgement. The helper observed matching timed/pending events and a
running status, then terminated only its own SSH process. It did not signal any
remote PID or change the network/firewall. The detached supervisor continued the
original bounded attempt and reaped all its children through the measured fixture
escape. The returned status PID matched the native producer, and the source/profile
identities matched the original plan. Status exit code zero is the collector's
recorded declaration, not an independently waited daemon exit or a service PASS.

A duplicate launch was rejected with exit 2 while the interrupted attempt was
active. Both cases also rejected duplicate launch after completion; sealed event
and status bytes were checked unchanged. The start acknowledgement has no service
verdict. A stale status/PID is never used as cleanup authority or as proof of
liveness.

Two new invalid native inputs (identifier starting underscore and invalid device
suffix) were rejected with exit 2 and empty stdout before persistent storage / test
execution. Frame PID/time scalars and sequence/cycle integer types were tightened
on the native reader. Actual malformed-producer fault injection is still a
remaining Phase 4 test, not established by these command-input rejections.

Twenty-seven host tests passed, including six new **synthetic status mutation**
checks: wrong owner/run/build/profile, running status over otherwise complete
events, unresolved cleanup, ambiguous types/versions/fields, and preservation of
service FAIL assertions under later incomplete status. These are host tests, not
native cleanup-failure or crash experiments. Exact executable-token review of
retained target inventory found no residual project runner/worker/fixture.

Reviewed complete plans, native streams, partial-before-disconnect observations,
start/running/final status records, evaluated results, host SSH termination and
duplicate command statuses, readback hashes, native rejection records and inventory
are in `docs/evidence/phase4-persistence/`. Raw originals/downloaded binaries remain
ignored under `.local/evidence/phase4-p4gate2`. No compiled/runtime or private
material is in the reviewed bundle.

**Remaining Phase 4 gate:** focused actual-QNX checks and dependable classification
for worker start/crash/stall, unavailable service, blocked diagnostic call,
malformed/truncated/overflowed producer events, sink/full-storage failures,
unresponsive target and failed cleanup/contamination. Persistent status and the
existing bounded collector do not by themselves pass those cases. The event sink's
fatal failure/cleanup path still needs containment work; no native sink-failure
cleanup success is claimed.

## E009: Phase 4 native failure matrix and containment gate

**Date:** 2026-11-06. **Outcome:** PASS for the Phase 4 exit gate. Individual
negative cases retain their actual ERROR, FAIL, NOT_RUN or UNSUPPORTED outcomes.

Qualification used base revision `175a6af24ca336ca091d9b08725db785fbdd2e2d`
with the explicitly dirty source digest
`ee3f95b47f01f0d447c768f57f41f3a44cd3f386f3fef0b888b5fa8e2f409e9e`.
The retained plans/manifests bind this exact source, profile/suite, recipe and
artifact hashes; this is not a claim that the parent revision contains the change.
Actual qcc/C11 builds with warnings as errors passed. All four generic binaries
matched SFTP readback. Target remained QNX 8.0.0 / 2026/06/05-16:26:03EDT,
x86pc x86_64, KVM, one CPU / 1 GiB, scheduling policy 2 / priority 10.
No explicit priority boost or busy-spin watchdog was used.

Actual commands, all successful at the qualified gate:

```bash
source /home/mignon/qnx800/qnxsdp-env.sh
make qnx
python3 tests/qnx/qualify-phase4.py --prefix p4gate3
python3 tests/qnx/qualify-target-loss.py --prefix p4gate3
python3 tests/qnx/qualify-persistence.py --prefix p4gate4
python3 -m unittest discover -s tests/host -v
```

The matrix requires exact equality of observed verdict/reason sets. The following
are actual target observations, not synthetic host result fixtures:

| Case / explicit lab control | Verdict | Exact reason set | Host elapsed seconds |
| --- | --- | --- | --- |
| normal / none | PASS | all_obligations_satisfied | 0.976 |
| normal_read / none | PASS | all_obligations_satisfied | 1.011 |
| stuck / worker_stuck | ERROR | worker_timeout | 2.263 |
| crash / worker_crash | ERROR | worker_crashed | 0.315 |
| start / worker_start_failed | ERROR | worker_start_failed | 0.294 |
| unavailable / service_unavailable | ERROR | service_unavailable | 0.301 |
| readiness / readiness_blocked | ERROR | probe_timeout | 2.238 |
| health / health_blocked | ERROR | probe_timeout | 2.884 |
| malformed / malformed | ERROR | evidence_invalid, evidence_incomplete | 0.964 |
| truncated / truncated | ERROR | evidence_incomplete | 0.981 |
| oversize / oversize | ERROR | evidence_invalid, evidence_incomplete | 0.970 |
| capacity / event_overflow | ERROR | evidence_capacity_exceeded, evidence_incomplete | 1.555 |
| channel / channel_full | ERROR | evidence_capacity_exceeded, evidence_loss, evidence_incomplete | 1.051 |
| sink / sink_unavailable | ERROR | event_sink_failed, evidence_incomplete | 0.973 |
| quota / sink_quota | ERROR | event_sink_failed, cancellation_not_completed, evidence_incomplete | 3.113 |
| manager / manager_interference | ERROR | service_interference | 0.266 |
| late / late_malformed | ERROR | evidence_invalid, cancellation_not_completed, evidence_incomplete | 3.174 |
| cleanup / cleanup_failure | ERROR | cleanup_failed, cancellation_not_completed, pending_state_not_released | 4.863 |
| dependent / none | NOT_RUN | prior_cleanup_failed | 0.275 |
| ownership / ownership_lost | ERROR | cleanup_failed, ownership_unknown, evidence_incomplete | 0.309 |
| owned_dep / none | NOT_RUN | prior_cleanup_failed | 0.268 |
| unsupported / none | UNSUPPORTED | required_capability_missing | 0.264 |

The case execution bound was 10 s, cleanup 2 s, setup/probe 2 s, operation timeout
500 ms and cancellation allowance 2 s. The helper's independent outer bound was
16 s. Observed matrix launch-to-final-status times were 0.264–4.863 s. Every
recorded timed-out wait was checked against the target's own absolute monotonic
bound. Case and cleanup are separate deadlines. A stalled VM is not covered by a
promise that native waits will make progress.

Each producer owns a separate nonblocking, bounded framed pipe. Malformed JSON,
a mid-frame EOF, an overlong frame, accepted-event capacity overflow and an actual
full producer channel were exercised. Invalid input is rejected before forwarding;
the bounded diagnostic retains its byte prefix. Producer exit 120 and raw wait
status establish channel evidence loss. The supervisor performed no blocking
service operation: readiness and health both blocked in disposable workers when
the owned fixture was stopped, and returned probe_timeout within their bounds.
The crash case was an actual SIGSEGV with core output disabled; start failure was
an actual missing executable; service-unavailable was a real failed worker open
after stopping only the owned fixture.

The unavailable primary sink produced actual EBADF (9). The full-storage control
used an isolated 8 MiB Power-Safe image through devb-loopback, not the main guest
filesystem. Native writes filled 8,290,304 bytes and returned ENOSPC (28); the
subsequent supervisor log write also returned 28. Its separate in-memory journal
and reserved recovery descriptor preserved the prior observations, original
written prefix, failure reason and cleanup/reaping. Both sink cases remain ERROR;
recovery does not make their evidence obligations PASS. The storage driver was a
child of a live test shell, which unmounted only its lab filesystem, terminated
that exact child and waited for it. Its spawn/reap PID and fill outcome are retained.
An earlier RLIMIT_FSIZE experiment did **not** cause a write error on this build;
its test rejected the missing error. It was replaced, not counted as passing or
used to relax the expected result. Debug originals remain ignored in p4trial2.

The cleanup-failure control deliberately withheld the fixture-stop escape for the
ignore-unblock fixture. TERM/KILL requests did not reap the reply-blocked worker;
the original 2 s cleanup bound expired with two genuinely unresolved children.
The original result retains cancellation_not_completed and pending_state_not_released
as FAIL assertions alongside cleanup_failed ERROR. Original status is incomplete,
cleanup_ok false, exit 2 with those PIDs. Only after sealing it did the same live
parent separately kill/reap its still-owned children in lab recovery (2.806 ms,
within its separate 2 s bound). Original status bytes remained unchanged. The
explicit dependent case still returned NOT_RUN/prior_cleanup_failed with zero
child launches. This is a policy-fault experiment, not a claim that QNX SIGKILL
cannot terminate every kind of process.

The ownership-loss control deliberately waited a ready worker outside the ownership
tracker and recorded that discarded wait. The tracker's actual subsequent ECHILD
(10) established ownership_unknown. No signal was sent to that uncertain PID;
cleanup remained unestablished for the tracker, and its dependent was NOT_RUN.
Inventory separately showed no residual project process. Persistent status was
never used as PID cleanup authority. The lab-manager control was a separately
owned child that terminated the fixture; its own wait status and unexpected
fixture death yielded service_interference, not successful service cancellation.
No server-monitor/slm was present in before/after inventories, and no unrelated
manager was disabled. This does not claim a real server-monitor policy was tested.

The target-wide experiment verified the exact owned QEMU PID, UID, command-line
lab image/loopback port and /proc start identity while no project operation was
running. It temporarily stopped only that VM, with a separate resume guardian.
An actual SSH command timed out in 0.802 s (0.8 s host timeout), producing
ERROR/target_unreachable and remote_cleanup NOT_RUN. The exact same VM was resumed
and SSH/inventory succeeded. No target-side cleanup or service assertion was
invented during the pause; the host and unrelated services were untouched.

Because the supervisor writer changed, the previously passed persistence subgate
was specifically rechecked. Normal job PASSed. A real active SSH client was
terminated after the sensor's timed pending barrier; reconnect by the original run
ID collected the preserved service FAIL, complete status and all owned reaps.
Active/completed duplicate launches were rejected without changing sealed bytes.
Original partial events/running status and transport exit are retained.

Thirty-five focused host tests passed: original 27 plus actual-matrix evaluation
and explicitly synthetic mutations for late malformed/truncated evidence,
independent FAIL plus cleanup ERROR, incomplete final flow/status, recovery-primary
loss, restart/health invalidation, ownership quarantine and target-wide ERROR with
no cleanup claim. Host mutations are not additional native executions.

Reviewed artifacts: [matrix index](evidence/phase4/index.json), plans, source-stamped
streams, starts/status/results, raw primary prefixes for sink tests, exact commands,
[storage lifecycle](evidence/phase4/storage-lifecycle.txt), separate recovery,
build/test logs and inventories in evidence/phase4; target pause records in
evidence/phase4-target; changed-writer SSH-loss regression in evidence/phase4-transport.
Raw originals and binary readbacks remain in .local/evidence. No SDK material,
VM image, compiled binary or credential is committed. The final inventory found no
residual project executable; all normal-cleanup cases had exact spawned=reaped
sets and empty unresolved status. The two deliberately failed-cleanup statuses
remain quarantined despite the separately observed lab restoration.

### E009 clean committed-source confirmation

After the passing precommit gate, checkpoint `1d49ad4` was committed. A fresh
`make qnx` recorded that actual revision with dirty=false and the identical source
digest. `python3 tests/qnx/qualify-phase4.py --prefix p4clean1` then re-executed all
22 native cases successfully with the same exact verdict/reason sets. All four
artifact readbacks matched; the isolated full filesystem and separate lab recovery
were restored, and final inventory found no project executable. Full reviewed
plans/manifests, events/status/results, commands, build log, readback identities
and index are retained in evidence/phase4-clean. This confirms the implemented
checkpoint itself; it does not relabel the earlier dirty-source experiment.

## E010: Phase 5 non-restart signal-family subgate

**Date:** 2026-11-06. **Outcome:** signal subgate PASS; **full Phase 5 remains
in progress**. Departure, repetition and directed ordering have not passed.

Actual source was base `d1b4536db63e1c8c83bc51f97548cbde8b41f8bc`, dirty=true, digest
`ed481cb5dd9f83e6a231598d14973f8b5f6ead7d6487d8201d1ef3e45d855888`. The plans/manifests and index retain source,
recipe/profile/suite and all artifact identities. Actual qcc builds passed with
C11/QNX extensions and warnings as errors; all four deployed generic binaries
matched SFTP readback. This is the same qualified QNX 8.0.0 x86_64 KVM lab, with
policy 2 / priority 10. No fixture cancellation implementation was changed for
this signal family; both use their reviewed current-owned-unblock MsgError(-1)
path and never return ERESTART.

```bash
source /home/mignon/qnx800/qnxsdp-env.sh
make qnx
python3 tests/qnx/qualify-signal.py --prefix p5signal6
python3 -m unittest discover -s tests/host -v
```

| Actual native case | Verdict | Exact reason set | Host elapsed seconds |
| --- | --- | --- | --- |
| sensor-signal-fixed | PASS | all_obligations_satisfied | 0.540 |
| sensor-signal-defect | FAIL | cancellation_not_completed, pending_state_not_released | 2.814 |
| job-signal-fixed | PASS | all_obligations_satisfied | 0.553 |
| job-signal-defect | FAIL | cancellation_not_completed, pending_state_not_released | 2.769 |
| sensor-timeout-fixed | PASS | all_obligations_satisfied | 1.069 |
| sensor-timeout-defect | FAIL | cancellation_not_completed, pending_state_not_released | 3.316 |
| job-timeout-fixed | PASS | all_obligations_satisfied | 1.105 |
| job-timeout-defect | FAIL | cancellation_not_completed, pending_state_not_released | 3.316 |
| sensor-auto-fixed | UNSUPPORTED | signal_mode_unsupported | 0.401 |
| job-auto-fixed | UNSUPPORTED | signal_mode_unsupported | 0.407 |
| job-missing-fixed | UNSUPPORTED | required_capability_missing | 0.412 |

The worker source creates no application thread and installs one SIGUSR1 handler.
The handler only sets volatile sig_atomic_t. Ordinary-context setup records
configured flags=0, retry=0, timeout_armed=0, actual queried masked=0 and error=0.
The actual QNX header/manifest signal number was 16; no host signal constants were
used to infer it. After actual matching fixture pending, the supervisor recorded
its trigger request and separate successful kill result for that exact owned PID.
No deadline/TimerTimeout event exists in the signal cases; the independent 2 s
cancellation allowance starts at the signal request.

Both corrected services recorded a live matching unblock, successful cancellation
reply/removal, handler seen=1 and MsgSendv raw_return=-1, raw_errno=4, api_error=4,
normalized INTERRUPTED/EINTR. Source trigger-to-result observations were 121,393 ns
(sensor) and 130,340 ns (job). These are observed runs, not worst-case bounds.
Post-state showed pending zero; the job still existed and was not ready. Completion
of that retained job and fresh-client retrieval succeeded. Health preceded stopping
the same fixture; no restart supplied a health result. All owned children were
actually reaped and final status was complete with no unresolved PID.

The two ignore-unblock cases confirmed actual pending and successful SIGUSR1 send,
then live ignored unblock and no completion past the original allowance. Each
retained cancellation_not_completed and pending_state_not_released as FAIL. Absence
of a handler observation while the operation remained blocked was not used to guess
a root cause. Emergency fixture cleanup was recorded separately; no restart or
cleanup result satisfied original-instance health. The changed common scenario
selection/process notification path specifically rechecked both timeout profiles
and both existing defect controls, preserving their ETIMEDOUT semantics/results.
No earlier full phase suite was restarted.

Both known automatic-restart requests returned UNSUPPORTED/signal_mode_unsupported
before any child launch. A missing required departure capability remained
UNSUPPORTED/required_capability_missing. Five new native malformed requests
(unknown signal mode, wrong expected cancellation error, mismatched case ID,
missing required signal observer and an undeclared retry key) returned 2, with
empty stdout and no run storage created. Every rejection had a fresh run ID to
avoid confusing duplicate protection with schema rejection.

Forty-six host tests passed, including eight new signal tests over these actual
vectors and explicitly synthetic mutations: flags/mask/retry/timer configuration,
missing handler, mismatched target signal number, signal-send failure, unrelated
timeout error and simultaneous operation timeout. These host mutations are not
additional QNX experiments. The native matrix and rejection helper check exact
outcome/reason sets and empty ownership ledgers. Final target inventory contained
no project process and no server-monitor/slm.

Reviewed plans, native manifests/events, starts/status/results, input rejections,
commands, build/host logs, inventory and the readback index are retained in
[phase5-signal](evidence/phase5-signal/index.json). Original binaries/raw local
state remain ignored in .local/evidence/phase5-signal-p5signal6. The remaining
Phase 5 gate must prove forced client departure, callback/OCB lifetime, 20-cycle
same-instance repetition and the two directed completion/cancellation orders on
both services, including their targeted negative controls.

### Shared producer follow-up during Phase 5

Review found that a fixture exiting with the reserved producer-write failure status
120 establishes both fixture interference and producer evidence loss. Both are now
retained. An added explicit fixture_evidence_loss control closes only the fixture's
own event descriptor before its readiness write; the real failed write exits 120.
The parent recorded raw wait status 30720, independent service_interference and
evidence_loss, plus required evidence_incomplete. It launched no worker and made no
service FAIL claim. Cleanup/reaping were complete. A ninth new host regression
checks that neither independent reason disappears.

Because the shared producer path changed, the expanded 24-case supervision matrix
was executed successfully at the same final source digest with
`python3 tests/qnx/qualify-phase4.py --prefix p5supervise5`, before the final signal
matrix. Its exact per-case outcomes, artifacts and support-tool readback/source
hashes are in evidence/phase5-supervision. The prior Phase 4 checkpoint and its
clean qualification remain preserved; this is an affected-path follow-up.

Two setup attempts were explicitly rejected before any scenario: accumulated old
lab images prevented creating the isolated image, and an attempted RAM-backed
loopback mount reported read-only filesystem. Neither counted as a native case or
passed gate. The six known generated temporary images were copied to ignored local
archives, verified with matching POSIX cksum/length, then removed from the guest.
Original VM/SDK images, all test logs/status and binary readbacks were preserved.
The helper retains the qualified file-backed filesystem, now preflights at least
16 MiB main-volume free space, cleans its exact temporary image after unmount and
owned-driver wait, and retains partial setup output on failure. Final checks
confirmed its image, mount directory and pseudo-device absent; the guest main
volume had ample free space. Setup errors and archive inventory are retained as
text, with no image or SDK binary committed.

The additional manager_pending case terminated the fixture while its baseline
ordinary devctl was actually pending. The worker recorded devctl return 3/errno 0,
close -1/errno 9 and declared exit 2; the parent recorded actual reaping. This is
ERROR/service_interference plus worker_close_failed, with no service FAIL and no
claim that the complete event stream was truncated. A native process_exit record
now provides WIFEXITED/WEXITSTATUS/WTERMSIG observations, avoiding host decoding of
QNX raw wait status. Known fixture interference invalidates transport-style
baseline errors; an independently returned bad payload remains a separate FAIL.
Explicit close failure and unexplained nonzero worker exit are execution errors,
not missing evidence. The complete 24-case matrix passed after this correction.

Current-host synthetic tests also verify that a later manager error cannot erase an
earlier successful-but-forbidden payload and that a recorded nonzero worker exit
cannot become PASS. This last host-only guard does not change native binaries;
the original native source identities above remain unchanged in retained plans.

### E010 clean committed-source confirmation

After committing source checkpoint `e78502ff02555638d5f859e05e30de6ae16ed0cd`, `make qnx` recorded it with
dirty=false and source digest `c446676dace9c6de52052d699e551e18f92bf4b252b9867f40d62ca907bcb578`. Actual commands
`python3 tests/qnx/qualify-signal.py --prefix p5clean1` and
`python3 tests/qnx/qualify-phase4.py --prefix p5clean2 --case normal --case normal_read --case manager_pending --case fixture_sink`
passed. The first re-executed all eleven signal/timeout/capability checks plus five
native rejections. The second confirmed both normal services and both additional
interference/evidence-loss cases, with their exact distinct reasons. All four
native artifact readbacks matched. These clean vectors include the final host
nonzero-exit guard; their actual source identity is not substituted into older
streams. Full reviewed records are in evidence/phase5-clean-signal and
evidence/phase5-clean-supervision. Final inventory found no project executable.

Phase 5 remains in progress: client departure, same-instance repetition and directed
ordering still require their native matrices. The signal subgate and the affected
supervision/timeout prerequisites are passed; this does not declare the Phase 5
exit gate complete.

## E011: Complete Phase 5 native lifecycle, repeat and directed-order gate

**Date:** 2026-11-07. **Outcome:** full Phase 5 exit gate PASS. This is checker
qualification: deliberately defective service runs retain FAIL and infrastructure
controls retain ERROR. It is not a claim that all forty service runs passed.

Started from clean 26c32232b632eecabfa39867075a830209c1d6de, preserving the existing
QNX installation/VM/authentication. The final precommit run is p5gate2: base revision
26c3223, dirty=true, exact source digest
61ac0d4ad9c48050413f19276588e9c3a155b5aa9d11e8c5da3155a0f0b8c370.
Do not relabel this run with a later commit. A clean committed-source confirmation
is recorded separately below. All native assertions here derive from actual
QNX execution; altered host-test vectors are explicitly synthetic.

Commands executed with the installed environment:

```
source /home/mignon/qnx800/qnxsdp-env.sh
make qnx
python3 -m unittest discover -s tests/host -q
python3 tests/qnx/qualify-phase5.py --prefix p5gate2
```

The real qcc gcc_ntox86_64/C11 warning-as-error build succeeded. Runtime IFS digest
remains 6cb923cc6f93fb122c8d36d63a8359663681db0357d826d6890ea7ddbfdc254f.
The four deployed executables were independently downloaded through SFTP and their
SHA256 matched the local build and manifest declarations:

| Artifact | SHA256 |
| --- | --- |
| Common runner | 3bad265115a7c84cdbef3e612aadcbe25740c80576759c9df983249a940b6e55 |
| Common worker / statically linked adapters | 420ccfdcdde6e96f6373763d5da857294f0a9ac41637ef7df92bae89eefd3ee8 |
| Sensor fixture | 822baa8b52081104c594245f9f5565060a4981e84b106f9bc2da9c66e5e82df3 |
| Job fixture | 377bce3f1741e742c57e3a7aa8642553f6f20f7bc808d2694e151a120dc72967 |

Reviewed text in `evidence/phase5/` includes index, commands, exact plans, native
manifest/producer streams, original status, results, stderr, independent recovery,
input rejections, inventories and build/host-test logs. Binaries and machine-local
configuration remain ignored. The lab is the same QNX8.0.0 x86_64 KVM guest, one
CPU/1GiB. No server-monitor/slm was observed. No unrelated host service changed.

### Complete matrix and explicit coverage

40 native cases completed with exact expected verdict/reason sets: **12 PASS,
19 FAIL, 6 ERROR, 3 UNSUPPORTED**. The longest measured host case was 14.94s (a
20-cycle run), below its declared outer bound. All owned processes were reaped
except the deliberately failed *original* cleanup controls, whose separate
same-parent recovery was observed and preserved without changing original status.
No residual project process was present in the final inventory.

- Both fixed services: normal ordinary-API, MsgSendv, duplicated-FD and actual
  deferred-release baselines; timeout; non-restart signal; forced departure;
  20 repeated timeouts; completion-first and cancellation-first all PASS.
- Timeout ignore-unblock retains cancellation_not_completed and
  pending_state_not_released FAILs. Retained-waiter and duplicate-terminal controls
  retain their specific FAILs. Signal ignore-unblock retains both prior FAILs.
- Departure retained-waiter FAILs pending_state_not_released on both services;
  job drop-job independently FAILs unexpected_service_state and
  unexpected_operation_result (fresh retrieval/control error observed).
- Departure ignore-unblock is **ERROR/departure_unobserved** on both. The exact
  SIGKILL syscall succeeded, but no reap occurred within the original bound.
  Later fixture cleanup allowed reaping; this does not prove earlier death or
  original-instance health, which stays NOT_RUN.
- Each corrected repeat has20 PASS cycles. Retain-third has PASS/PASS/FAIL followed
  by17 NOT_RUN. Ignore-unblock has1 FAIL and19 NOT_RUN. The cycle-two blocked state
  probe has PASS/ERROR and18 NOT_RUN. Failed final cleanup retains first-cycle FAIL,
 19 NOT_RUN and independent cleanup_failed ERROR. Across10 repeat runs, all200
  requested cycles are explicit:46 PASS /6 FAIL /2 ERROR /146 NOT_RUN.
- Both directed-order families' duplicate-terminal controls FAIL
  duplicate_terminal_attempt. The observed second MsgError returned -1/error3;
  this proves a duplicate attempt rejected by QNX, not double-delivered replies.
- Automatic-restart signal requests are UNSUPPORTED on both services. Sensor
  error-probe is UNSUPPORTED/required_capability_missing. No fixture is spawned.
- Native input rejection for cycles21, repeat reset new-instance, aggregate cycle2
  and case/profile mismatch returned2, empty stdout and no persistent run storage.

### Departure and OCB lifetime observations

The exact worker duplicates a descriptor, closes the original, enters an untimed
prepared MsgSendv, and is confirmed pending before SIGKILL9. Native wait macros
record actual signal9 termination and reap within the bound for both corrected
fixtures. For the linked OCB, actual records show two close_dup callbacks/default
returns, then one final close_ocb/default return; every default returned0. The
first descriptor close precedes pending, the final close follows the trigger.
No post-free OCB access is used; pending references are cleared before final free.
Both observed close receive IDs were **nonzero**. The synthetic rcvid0 branch is
guarded/delegated and its marker is validated, but was not observed in these runs.

Public pending returns0. Without fixture restart, a fresh client reads value42
from the sensor. The job remains job_exists1/job_ready0 after waiter departure;
release completes it and a fresh client retrieves job1/value420. The retained-job
fact is distinct from leaked waiters. Stored PIDs never authorize cleanup.

### Repetition and ordering observations

One fixture readiness and PID per repeat;20 distinct operation workers, independent
fresh health workers, no service reset. Unblock counters progress1..20 and
request generations3..22; pending0 and exact state/health facts at each cycle.
Every attempted cycle records precondition/timer/result/state/health and observed
worker reaping. Unknown-state cycle-end pending placeholders are marked
state_observed0 and do not become adapter observations. Later cycles never touch
contaminated service state. No memory usage was measured; no memory-leak claim.

Completion-first queues a genuine kernel unblock at an explicit barrier, then
replies normally before cancellation commits. Cancellation-first observes the
interrupted result before the release worker starts. The evaluator requires
linked barrier/control-start/terminal/result ordering, rather than mere case names.
Complete-first additionally observes a normal result before SIGUSR1 is requested
against a still-live worker. Signal-handler observations are separate from send
success. Saved notifications are checked with current MsgInfo/flags and immutable
owner/logical/generation data while a new generation is pending. New values43/421
prove stale42/420 cannot satisfy the fresh request. A separate parked devctl
receives a real unmatched kernel unblock and completes EINTR after owner checks.
These are two directed orders plus specific obsolete/unmatched paths, not exhaustive
concurrency or arbitrary receive-ID reuse coverage.

### Affected prerequisites and host negatives

Phase5 changed the child ledger, bounded event/journal capacities and both close
callbacks, so14 affected supervision checks were rerun using
`qualify-phase4.py --prefix p5reg1` with crash/readiness/health/malformed/truncated/
capacity/channel/sink/manager_pending/fixture_sink/cleanup/dependent/ownership/
owned_dep. Every exact expected reason set passed. Text is in
`evidence/phase5-lifecycle-supervision/`; it accurately retains the preceding
source digest875899fa... (same native binary hashes), before the final evaluator's
additional required barrier assertion. Phases1–3 and unaffected full-storage/
target-loss/SSH prerequisites were not repeated. Legacy capacity limits remain
unchanged; actual extended repeat streams fit the declared larger bounds.

63 host tests pass. New checks re-evaluate every actual gate vector and mutate
wait status, callback defaults, synthetic markers, counters, barriers, stale
matching/payloads and missing unmatched notifications. Profile reset/cycle/case/
distinct-result checks reject invalid input. Generic scenario/evaluator sources
contain no service-name conditions. Host mutations establish validation behavior,
not new native claims. Failed experiments p5d1–p5d4/p5gate1 remain local debug
records and are not substituted for this final gate.

The small target filesystem accumulated duplicate journal/debug logs. Completed
debug-run log copies were archived locally with per-file POSIX cksum/length checks
and SHA256 before removing only those log copies; run-status/duplicate guards were
retained. Final p5gate2 gate records were preserved. SDK, original images and
credentials were neither removed nor recreated.

### E011 clean committed-source confirmation

Phase5 checkpoint **9d4a10d25ebf506f59fac274e5902ec699aebd45** was committed only
after the complete gate passed. From a clean working tree, `make qnx` recorded
that exact revision, dirty=false and source digest61ac0d4a... . The entire40-case
matrix was rerun as **p5life-clean1**, including both20-cycle positives, both
ordering families and all negative/containment/capability cases. All exact expected
classifications/reasons and four native input rejections passed again. Four SFTP
readback hashes match the preceding artifact table. Reviewed text is retained in
`evidence/phase5-clean-lifecycle/`. This clean run is independent from precommit
p5gate2; no dirty observations were relabelled. An initial attempt to use already
occupied prefix p5clean2 was refused by exclusive directory creation before any
new run; its old contents were preserved and a fresh prefix was used.

The remaining63 host tests pass. Raw inventory trailing spaces are retained as
observed bytes. Phase6 now begins; its changed-build replay/export gate is still
open. No earlier phase was reopened without the specific affected-path reasons above.

## E012: Phase 6 immutable evidence, actual changed-build replay and exports

**Date:** 2026-11-07. **Outcome:** Phase6 exit gate PASS. This gate reuses the
qualified Phase5 observations; it does not reopen/repeat earlier native matrices.
New native executions are the required original/candidate replays on both services.

Host evaluator source: base9c06190280bc37de35ae2ce49d11c931b4a889a5, dirty=true,
source digest95a99f6e46db01ae1bd97f794f57e046bdb7593304ff1092f9066189dd779e9e.
The final gate is **p6gate3**. Native original build remains clean9d4a10d with the
E011 hashes; host/evaluator identity is stored separately in every sealed marker.
No original observation was relabelled with the new evaluator's revision.

### Real behavior fix and explicit selection

Created an isolated Git worktree in ignored local storage from9c06190, preserving
main's intentional defect controls and all uncommitted host implementation.
Qualification branch `qualification/phase6-fixed-unblock` commits actual source
fix **c26365e91f8f0810a531726937c6b2c4bd923837**. Its patch removes the ignored-
unblock early return from both fixtures; it does not change a comment, stamp,
expectation or runtime setting. The exact patch is `evidence/phase6/candidate-source.patch`.

`source /home/mignon/qnx800/qnxsdp-env.sh` and `make -C .local/phase6-fixed-source qnx`
used real qcc gcc_ntox86_64/C11/warnings-as-errors. Committed candidate source is
clean, digest99bc12092592dc0f0cf80bfd2b6fa5257f6a18c4a52e719fb24c4a7672e37c16.
The candidate keeps the generic runner/worker hashes from E011 and changes the
actual service binaries:

| Fixture | Original SHA256 | Fixed-source candidate SHA256 |
| --- | --- | --- |
| Sensor | 822baa8b52081104c594245f9f5565060a4981e84b106f9bc2da9c66e5e82df3 | 2018ef2ec63fbbc34f7c428d80f1bcd552c43255b794b1d46aee03353418d18c |
| Job | 377bce3f1741e742c57e3a7aa8642553f6f20f7bc808d2694e151a120dc72967 | 955bf528e9567c128fc12859365752810efa49c8e63f7cbd8779d785ec99fcd4 |

Executed `python3 tests/qnx/qualify-phase6.py --prefix p6gate3 --fixed-source .local/phase6-fixed-source`.
It invokes the product CLI with **--candidate-manifest** for every replay, uploads
the fixed executables to an exclusive owned deployment, then queries actual uname
(-p x86_64, -m x86pc) and independently SFTP-downloads/hashes runner/worker/fixture
before launch. The statically linked adapter hash must equal worker. Build IDs
are immutable content identities; actual deployment paths are resolved separately.

| Service / attempt | Explicit selection | Actual outcome | Comparison | Execution exit |
| --- | --- | --- | --- | --- |
| Sensor /2 | Original deployed build | FAIL: cancellation_not_completed, pending_state_not_released | still-failing; original obligations reproduced |1|
| Sensor /3 | Source-fixed candidate | PASS | fixed; original obligations not reproduced |0|
| Job /2 | Original deployed build | FAIL: cancellation_not_completed, pending_state_not_released | still-failing; original obligations reproduced |1|
| Job /3 | Source-fixed candidate | PASS | fixed; original obligations not reproduced |0|

The exact profile, operation parameters, scenario/reset/cycle settings, time bounds,
expectations and **fixture_mode=ignore-unblock** are unchanged. Each fresh run has
new run/attempt/instance identity, explicit original/candidate build identity and
actual target evidence. Switching corrected/defect flags within one binary was
not used to satisfy this gate. Each service's attempt4 deliberately selects an
internally consistent manifest with a wrong fixture hash: actual target readback
detects it, exit2, launch_requested=false, acknowledged=false and no target run
storage. Expected/observed hashes and both failed attempts remain preserved.
There is no automatic retry. Native inventory contains no residual project process.

### Artifacts and canonical evaluator

Reviewed text in `evidence/phase6/` retains original and replayed immutable bundles,
attempts, selected candidate manifests, actual hash checks, commands, comparisons,
patch/build records, mixed XML and inventories. Readback binaries/SDK/images/keys
stay local and ignored. Every bundle seals original raw bytes, plan/profile/build/
target snapshots, status, evaluated result, replay input, notes and hash marker.
Original and candidate source identities are explicit; clean/dirty is not guessed.

An exclusive directory preserves partial raw inputs before validation. Atomic
same-filesystem writes/fsync publish completed members; the final marker follows
cross-validation and read-only sealing. No final marker means incomplete evidence.
A complete artifact may correctly contain FAIL/ERROR/UNSUPPORTED. Integrity checks
reject unknown/missing/symlinked/corrupt members, duplicate keys or inconsistent
plan/result/replay/hash binding. They re-run the same canonical evaluator, whose
assertions now include reason, expected predicate, observed raw event/status values
and ordinal references. No private state is invented for missing probes.

### Export and negative validation

Parsed actual mixed JUnit: **32 cases /6 failures /4 errors /18 skipped**. This
includes original/reproduced failures, both source-fixed PASSes, an actual departure
ERROR, required unsupported capability and repeated retained-state failure with
17 NOT_RUN cycles. Three synthetic required-coverage/error cases prevent incomplete
or all-skipped suites from appearing green. XML is serialized by ElementTree;
case names are stable and retain bundle/assertion references.

Regenerating derived views and offline inspect left every sealed member's SHA256
unchanged. Offline inspect returned0 for valid red evidence without changing its
FAIL. Execution precedence130 >2 >3 >1 >0 is checked, including required unavailable
coverage taking precedence over FAIL. Comparisons distinguish fixed/still-failing/
newly-failing/still-passing/unsupported/incomparable/incomplete. Changed contract
or architecture is incomparable; an incomplete candidate cannot be fixed. Original
FAIL obligations determine reproduction, not any unrelated red result.

80 host tests pass, retaining the complete Phase5 outcome matrix. New checks cover
atomic publication failure, partial/raw preservation, missing final markers,
truncation/duplicate keys/symlinks/tampering, actual assertion-reference contents,
changed expectations unable to relabel saved native evidence, candidate ABI/version/
architecture/path/hash validation, comparison outcomes and mixed/all-unsupported
JUnit structure. Synthetic mutations are explicitly labelled; the new four native
replays and two actual target hash rejection checks are recorded independently.

The specialized replay transport reuses the intended lab and local authentication.
It does not yet implement Phase7's full target/deploy/run/status/collect/report
workflow or packaging outside a repository. No frontend, web service, database,
monitor changes, host reboot or broad process kill was introduced.

### E012 clean committed-host confirmation

Phase6 checkpoint **a96c62784dedd0f55abba45fb6b0c27f9ffd9528** was committed after
its full gate passed. With a clean working tree, `make qnx` and all80 host tests
passed, then the complete native replay gate ran again as **p6clean-life1**.
Every sealed marker and the index record that exact host revision, dirty=false,
source digest95a99f6e... . Both original-build replays remain FAIL/still-failing;
both explicitly selected source-fixed builds PASS/fixed; both wrong-hash preflights
refuse launch. Parsed mixed JUnit retains32/6/4/18 tests/failures/errors/skipped.
Immutable raw members were checked unchanged. Native original9d4a10d and candidate
c26365e identities remain separate; they were not relabelled with the host revision.
Reviewed text is in `evidence/phase6-clean/`; local binaries/readbacks stay ignored.

Completed debug deployment binary copies were additionally archived locally with
expected SHA256 plus target POSIX cksum/length verification before removing only
those redundant target binaries. Final Phase5/Phase6 deployments and evidence were
retained, as were old run-status guards and original SDK/images/authentication.
The next ordered work is Phase7; no Phase7 gate or external-service attachment is
claimed by this checkpoint.


## E013: Phase 7 complete host workflow on real QNX

**Date:** 2026-11-07. **Gate:** passed. Full command:
`source /home/mignon/qnx800/qnxsdp-env.sh` then
`python3 tests/qnx/qualify-phase7.py --prefix p7gate3` (exit0).
[Qualification index](evidence/phase7/qualification/index.json),
[actual commands/output](evidence/phase7/qualification/commands.json),
[reviewed copy inventory](evidence/phase7/curation.json) and
[95 passing host tests](evidence/phase7/p7-host95-final.txt) preserve the distinction
between host validation and native integration. Python was3.12.3. Added CI targets
Python3.10/3.12, host-only; no hosted CI execution is claimed.

The actual source was base557c313d53b65b912eb4bb32be6e2a54af11f106, dirty=true,
source SHA256 6a5aa7f33f89f11b806e3beda81d3a4ad4ec8131b838053f80421dfe7f9b6249. This is the precommit implementation, not a clean-base
native claim. The qualifier required identical start/end source identities.
Make used real qcc gcc_ntox86_64, C11, Wall/Wextra/Werror. Native records and each
bundle bind exact executable hashes and separate evaluator/source identities.
The existing KVM QNX8.0.0 x86_64/x86pc guest, SDP, image and local SSH credentials
were reused. Neither host services/firewall nor original SDK/images were changed.

### Complete workflow

The documented doctor/validate/build/deploy/run/replay/compare/report/verify commands
ran through argparse and the configured OpenSSH alias/SFTP route. Doctor observed
host/SDK/compiler variant, actual target uname/UID, command path, byte transfer and
deployed engine capabilities. Service-instance capability knowledge stayed UNKNOWN
until execution. Deployment transferred complete owned bundles, checked downloaded
SHA256/lengths, published final ownership markers and rechecked before launch.
A partial publication is rejected; unrelated storage is preserved.

There were75 distinct native case IDs (82 collected bundle copies including
same-ID recovery collections). The fixed sensor lifecycle passed all six families,
including20 same-instance reconnect cycles. The full broken lifecycle retained
FAIL/FAIL/ERROR/FAIL/PASS/FAIL and exit2; departure_unobserved remains an
infrastructure observation failure alongside independent service failures.
The fixed-mode replay passed, with comparison explicitly incomparable because its
fixture setting changed. New-directory collection preserved exact request and raw
bytes. Offline report and JUnit generation succeeded without changing verdicts.

The candidate workflow rebuilt/deployed committed source correction c26365e91f8f0810a531726937c6b2c4bd923837,
with actual fixture hashes changed and ignore-unblock/profile/timing unchanged.
Both before runs and same saved contracts retained their FAILs; explicit candidate
replays passed and comparisons were fixed. Original/candidate builds and the exact
[source patch](evidence/phase7/qualification/source-correction.patch) remain recorded.
This uses an actual handler correction, not only a defect-mode switch.

External-health attached through both registered profiles using actual O_RDONLY
worker FDs and recorded F_GETFL checks. Public normal/prepared/state/fresh-health
checks passed. The separate owner observed both original service PIDs still alive;
product launched/stopped no external fixture. Explicit owner STOP/reap was recorded
separately. All12 private lifecycle requests were UNSUPPORTED before service child
launch. Running external build/instance identity remains unverified; changed-build
external replay is unavailable without adapter identity support.

### Negative and recovery qualification

- Missing configured target, invalid profile/timing, occupied output, actual refused
  SSH route, wrong target processor and incompatible QNX release returned2. Existing
  unrelated bytes and an unknown remote session marker were preserved.
- Unavailable required capability returned3/UNSUPPORTED; no missing observation
  became PASS. Native unsupported cases launched no service workers.
- A proxy forwarded actual OpenSSH traffic and dropped the real native launch ACK.
  Initial exit2/uncertainty remained in history; status/collect recovered the same
  run and supervisor PID. No duplicate launch or replacement ACK was created.
- A separate real running status was observed before SIGINT of the exact local CLI.
  Exit130 and partial bytes were preserved. Collection recovered the same remote
  supervisor,20-cycle result and matching raw prefix. Local SSH termination/reaping
  did not authorize signalling persisted remote PIDs.
- With the local active-deployment receipt temporarily moved, status/collect
  bootstrapped the trusted local controller and recovered the stored remote request
  by ID. The original selection bytes were restored; no manual PID/plan reconstruction.
- An isolated lab injector published a self-consistent manifest with an intentionally
  wrong expected runner hash. Product SFTP verification detected actual byte mismatch
  before native launch. Incompatible build/target bindings likewise failed preflight.
- Independent FAIL reasons remain separate. Synthetic host mutation of an unknown
  signal child proves evidence_invalid/ERROR without erasing established service FAILs.
  This mutation is a host test, not claimed native fault execution.

`verify --suite release` completed36 exact expected outcomes:12 PASS,19 FAIL,
2 ERROR/departure_unobserved,3 UNSUPPORTED. Its exit0 qualifies the checker; the
underlying red service cases and later NOT_RUN repeat cycles remain unchanged.
Native before/after process inventories show no unresolved project children.
The full run retains actual status/reaping facts and bounded evidence channels.

### Failed experiment and storage maintenance

Earlier p7gate1 stopped with real targetctl errno28/ENOSPC while writing an external
session request. [Preserved failed execution](evidence/phase7/failed-inode-experiment/execution/result.json)
is incomplete/exit2, all six unlaunched cases NOT_RUN; it is not a passed gate or
service failure. The guest has3072 file entries and exhausted them despite free
blocks. D027 records verified archival of379 closed earlier native histories;
20 unestablished histories were untouched. Before the final stricter source rerun,
75 superseded p7gate2 native histories and50 bound session records were similarly
archived. Target cksum/length and local SHA256 were verified before removing only
redundant copied files. Exclusive native/session directory guards remain. No process
was signalled and the final p7gate3 histories remain on target. Archive indices are
under evidence/phase7/maintenance; complete original bytes remain local.

Reviewed copies omit generated binaries, machine-specific target/OpenSSH
configuration and redundant unsealed raw copies where sealed bundles retain the
same bytes. Evidence bytes were not edited. SDK, images, license and authentication
material remain outside Git. Phase7's exit gate passes; the next ordered work is
Phase8 detailed offline report and browser qualification.


## E014: Phase 8 offline report and browser qualification

**Date:** 2026-11-07. **Gate:** passed. Report implementation tested over
Phase7 checkpoint965c816152fe048b6f76e73007586ff086a15ef2, dirty=true,
source SHA256 1d71edda3545e44c0dfcc77c5a6835a48afc3f4341043966b9bcc73d0b8651df. No native C/header/build change was made for Phase8;
this is host presentation/comparison qualification, not new QNX execution.

[105 host tests](evidence/phase8/host-tests.txt) passed, including10 report-focused
regressions. The actual optional test-only browser command was:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/browser-binaries" .local/browser-test/bin/python tests/browser/qualify_reports.py --out docs/evidence/phase8
```

[Browser index](evidence/phase8/index.json) records15 reports /45 views with
Chromium156.0.8078.4 and Playwright1.64.1. Product runtime remains Python stdlib.
Every report opened via file URL at1440x1000 and390x844 with JavaScript, and1280x900
without JavaScript. Keyboard disclosures, optional filters, event-reference links,
all local artifact links, page bounds and source/JUnit preservation passed.
No external requests or page errors occurred. All1486 source artifact files were
SHA256-identical before/after; separately exported broken-suite JUnit was identical.

Actual previously qualified QNX bundles supplied fixed/broken/full replay, job,
external health,12 unsupported lifecycle cases, recovered transport and timeout
without optional signal observations. Older real unavailable-service, failed
cleanup and manager-interference streams were resealed/re-evaluated on the host
without changing a native byte. Their index explicitly identifies the old native
build and raw digest; they are not runs against this renderer revision. Empty and
hostile long-error samples are clearly SYNTHETIC formatting only.

The report answers what was tested, expected obligations, actual observations and
exact errors, reasons for the saved verdict, original-instance usability and how
to replay. Every required repeat cycle is visible; actual timeline records use
NDJSON references/target clock offsets and do not invent expiry or missing stages.
Partial/empty inputs remain INCOMPLETE/ERROR. Unsupported coverage, independent
cleanup facts, unverified external identity and post-restart recovery stay distinct.
No input string becomes executable markup; no raw JSON is embedded in scripts.
Tampered finalized bundles are rejected and derived outputs cannot overwrite raw,
partial, diagnostic or collection-history evidence.

Actual source-fix and changed-setting comparisons preserve fixed versus
incomparable labels and expose separate build, contract and target context. A
specific host comparison prerequisite was tightened: changed recorded target
metadata or IFS recipe is incomparable. Synthetic mutations prove that those
changes cannot claim fixed/reproduced; the real same-target before/after bundles
still compare fixed. This check does not change native results or require repeating
unchanged Phases1–6. Older comparison metadata with absent target context says unknown.

Screenshots were visually inspected. The first narrow layout exposed single-letter
headers despite passing automated overflow checks; minimum readable table widths
and horizontal scrolling corrected that issue before the final run. Comparison
identity JSON was moved into disclosure so outcomes/settings are visible first.
The final [case-list narrow view](evidence/phase8/screenshots/case-list-narrow.png),
[case detail laptop view](evidence/phase8/screenshots/case-detail-laptop.png),
[source comparison](evidence/phase8/screenshots/source-comparison-laptop.png) and
empty/failed-baseline/cleanup/long-error screenshots show the tested states.
[Additional inspection](evidence/phase8/visual-inspection.json) records the two
explicit left-aligned screenshots; they supplement the45 automated views.

[Fixed report](evidence/phase8/reports/fixed.html),
[broken report](evidence/phase8/reports/broken.html),
[source-fix comparison](evidence/phase8/reports/source-comparison.html) and
[readable guide](reports.md) are committed with local evidence links. HTML display
is self-contained; sharing the linked artifacts requires their accompanying tree.
No cross-browser/accessibility certification, new native gate or exhaustive
concurrency claim is implied. The Phase8 exit gate passes; Phase9 clean source
reproduction and release-candidate hardening are next.


## E015a: Phase9 input review before clean release qualification

**Date:** 2026-11-07. Full Phase9 gate is still pending. The focused
[QNX input gate](evidence/phase9-input-review/p9-input5/index.json) passed both
services using real qcc/SSH/SFTP and a native owner/probe, with actual source digest
and test-driver source/binary hashes. There are12 sensor and13 job exact API/error
checks plus same-instance state/fresh-client checks. All six direct children,
including service-facing preflight workers, were actually reaped. Parent never
executes the service operation or signals stored/unknown PIDs. Existing host
services, SDK, guest image and local credentials were preserved.

Actual errors were EINVAL22, EMSGSIZE240, EBADF9, ENOENT2 and framework EBADMSG77.
The service generation stayed1, pending state zero and fresh sensor42/job420
remained usable on the original fixture. Rejected commands require no reset.
Combined custom operations remain outside the fixed protocol; tested prefixes
were framework rejections and the custom tail was not observed executing.

Earlier p9-input1 lacked required fixture producer identity environment and exited
120; p9-input2 exposed the uninitialized transition output and an incorrect test
expectation for framework framing errors. It ended failed, with corrupted concurrent
failure output retained as raw bytes, never accepted as complete successful
observations. Actual generation changed to4 and a fresh read became pending;
that was a real defect in project fixture error handling, not a QNX vulnerability.
Initialization/bounds/access fixes then passed p9-input3 and the final stricter
p9-input5 gate. The owner now supervises even preoccupied-device stat and preserves
unknown wait state without guessing PID ownership.

[106 host tests](evidence/phase9-input-review/host106.txt) passed. A new host-only
regression checks oversized stderr from a fast local child; no native behavior is
inferred. Actual qcc -fanalyzer/Wall/Wextra/Werror object compilation covered16
owned C files with zero diagnostics (index.json in this evidence directory).
No target sanitizer, memory measurement or external developer review is claimed.
The official QNX APIs and boundary review are linked in release-review.md.

The final p7gate3 histories/sessions were subsequently copied through the owned
controller/SFTP and cksum/SHA256 verified before removing redundant target files.
75 native histories/50 sessions were archived, all directory start guards retained;
three no-status destinations were untouched. The archive index is preserved here,
full original bytes remain local and canonical Phase7 copies remain committed.
This is file retention maintenance, not process cleanup or a PASS for missing data.

Next: commit the input-hardening candidate, reproduce README/release verification
from a separate clean checkout against the explicitly reused target, and finish
the codelab/adapter/release records. A focused input gate does not finish Phase9.


## E015: Phase9 clean source reproduction and release candidate

**Date:** 2026-11-07. **Gate:** passed. The separate checkout
.local/phase9-reproduction was clean at d2e0a43872b80353480838665e754bafbacf11ae,
source SHA256 f13da86d12a15b4a1206e53019c7e9f406e57f23f4a3f9820214519f593cf81b.
Actual command after loading the existing SDP environment:

```sh
python3 tests/qnx/qualify-phase9.py --out /home/mignon/projects/resmgrcheck/.local/evidence/phase9-clean --fixed-source /home/mignon/projects/resmgrcheck/.local/phase9-fixed-source --input-prefix p9clean-input
```

[Clean gate index](evidence/phase9/qualification/index.json),
[actual commands/stdout/stderr](evidence/phase9/qualification/commands.json),
[106 clean-checkout host tests](evidence/phase9/clean-host106.txt) and the copied
native execution trees preserve actual source/build/evaluator identities.
The existing KVM QNX8.0.0 x86_64/x86pc guest was explicitly reused. No VM/image/SDK
recreation, host reboot/service/firewall change or authentication recreation took
place. Ignored local target metadata pointed to the existing verified OpenSSH route;
credentials/configuration contents were not copied into evidence. This is a clean
source build against a reused target, not a fresh-target reproduction.

The README sequence ran literally: initial doctor returned3 with UNKNOWN undeployed
checks; validation and real qcc gcc_ntox86_64 Make build succeeded; complete immutable
SFTP/readback-verified deployment and second doctor succeeded. Corrected sensor
lifecycle passed all six families; the explicit broken lifecycle exited2 with
preserved FAILs plus departure_unobserved ERROR. Fixed-mode replay passed and was
correctly incomparable because its setting changed. Compare, JUnit and offline HTML
succeeded. Git was identified as an implicit source-identity prerequisite and was
made explicit in README/dependencies. Manual startup/licensing/SSH setup stays explicit.

There were58 distinct canonical native case IDs across43 requests. Release verify
matched36 exact outcomes:12 PASS,19 FAIL,2 ERROR,3 UNSUPPORTED. Expected checker
success never changed those individual verdicts or withheld NOT_RUN cycles. Its
full native failure/corrected matrix covered both services/all six families.
The standard JUnit export retained81 tests,5 failures,4 errors,19 skipped; required
coverage errors remain visible. Final statuses establish observed cleanup with no
unresolved children. Before/after actual target/process/storage snapshots are saved.

The clean native input gate additionally proved25 exact accepted/rejected messages,
unchanged generation/pending state, original-instance fresh client42/420 and actual
reaping of all six owned preflight/probe/fixture children. Combined prefixes remain
framework rejections, not evidence that the custom tail executed. See E015a and
qualification/input-bounds; no unsupported raw-wire support was introduced.

Both saved single-timeout source-before cases exited1/FAIL. Separately committed
source fix3d0d7b1 removed only the intentional ignored-unblock early return in both
fixtures. Actual qcc build/deploy and explicit --candidate-manifest replay passed
both unchanged contracts/settings. Actual fixture hashes changed; runner/worker
remained generic and shared. Comparisons were fixed with equal recorded target/
recipe context, and original/candidate identities are preserved. The actual
[source patch](evidence/phase9/qualification/source-fix.patch) is used by the
[codelab](codelab.md). The worked job adapter guide lists exact files/boundaries.
No independent external developer review/adoption is claimed.

### Presentation-only follow-up

Review of a required-coverage result found that the HTML summary mapped every
exit3 to UNSUPPORTED, even with an independently established service FAIL and later
NOT_RUN cycles. The view now preserves the saved aggregate FAIL and its separate
incomplete-coverage warning. Canonical JSON/JUnit/CLI exits were not changed.
[107 host tests](evidence/phase9/host107-followup.txt) and
[four actual browser views](evidence/phase9/report-followup/index.json) passed for
that real retained-third result and a clean replay, at laptop/narrow widths with
and without JavaScript. No external requests/page overflow occurred.

[Source equivalence](evidence/phase9/native-source-equivalence.json) verifies every
native C/header, vendored C input, Make/build script and host engine module equals
the clean qualified checkout; only reports.py differs in runtime code. This host
presentation correction does not invalidate native IPC prerequisites. Its host
source digest is recorded separately from the frozen clean native/evaluator gate;
no old native evidence is relabelled as the follow-up revision.

The [review record](release-review.md) links current official QNX default-close,
unblock, devctl and message-boundary guidance. Actual qcc -fanalyzer/Wall/Wextra/
Werror compilation of16 owned C files emitted no diagnostics. Target sanitizers,
memory-leak absence, exhaustive concurrency and broad security auditing are not
claimed. Dependency/license/environment records and concrete limitations are current.
Reviewed text copies preserve exact native bytes; binaries/readbacks, SDK/images,
credentials and machine configuration remain ignored. The Phase9 exit gate passes.
Next: prepare and rehearse Phase10's concrete demonstration/submission package;
publication/submission remain separate authorization-dependent actions.


## E016: Phase10 actual QNX demonstration and local submission package

**Date:** 2026-11-07. **Preparation:** complete. Engineering complete; candidate
publication, public video URL, entrant attestations and confirmed submission remain
separate pending operator actions. Existing GitHub repository visibility was
observed public through its read-only connector; no remote mutation occurred.
The official rules were freshly fetched successfully and are linked in
submission/rules-check.md; no full rule text or website metadata is redistributed.

The final actual recording command used the installed local SDK/browser tooling:

```sh
source /home/mignon/qnx800/qnxsdp-env.sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/browser-binaries" .local/browser-test/bin/python tests/demo/record_demo.py --prefix p10demo2 --out .local/submission/demo2 --fixed-source .local/phase10-fixed-source
```

[Recording manifest](evidence/phase10/manifest.json),
[full actual command output](evidence/phase10/commands.json),
[qualification](evidence/phase10/qualification.json),
[ffprobe](evidence/phase10/ffprobe.json) and screenshots bind the result.
Original/host source was clean d9d2a1a36702488f3f40524f1ebf8cbd4ebc9357,
runtime SHA256 02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b.
The separately committed actual correction was39b99d7, removing the intentional
ignored-unblock early return from both fixtures. qcc force-builds/deployments and
actual SFTP/hash verification preceded execution. The existing QNX guest was reused.
No SDK reinstall, new credentials, host service/firewall change or reboot.

Five distinct native runs matched: corrected sensor PASS; intentional broken
sensor FAIL/exit1 with both cancellation_not_completed and pending_state_not_released;
unchanged-setting explicit candidate replay PASS/fixed; exact-worker departure
PASS with actual exit/default close/reap and original-instance fresh health;
job PASS with retained job/fresh420. The worker and runner hashes are shared across
both services and both builds; the fixture hash actually changed. All final statuses
have observed cleanup and no unresolved children. After recording, the original
main deployment was reselected and verified so the normal release workflow retains
its planted negative controls.

The capture streams actual host CLI output into a local browser viewer and opens
the generated offline report. Pending/unblock, expired result limit, separate
cleanup, source patch, native qcc build/replay, default close callbacks and shared
worker hash are readable in inspected frames. The final encoded MP4 is exactly
170.000 seconds, H.264,1280x720 at25 fps, with English on-screen explanation and no
audio/music. It is `.local/submission/demo2/demo.mp4`; its SHA256 is in
submission/demo-metadata.json. Optional narration/SRT and exact cues are committed.
The first170-second successful rehearsal remains local with its manifest; the final
take improves readability without rewriting native verdicts or reusing run IDs.
All actual raw/status/result/profile/build/replay bytes remain preserved. These
five current-runtime native cases supplement E015's full clean release gate; no
unchanged earlier phase was relabelled or claimed to run on a documentation successor.

E015 histories were later verified/archived to free the small guest filesystem for
capture:54 completed native histories and39 bound sessions, retaining all directory
guards and the four source-before/after histories. The typed controller, SFTP,
cksum/length and SHA256 checks preceded exact-file removal; no process was signalled.
Committed/offline copies preserve the full58-case gate. Unknown histories and
immutable original/candidate deployments were not removed. Retention index is
submission/retention-before-demo.json. Archived IDs need their offline copies.

Source/evidence/release text, codelab, worked adapter guide, evidence map, description,
metadata, readiness distinctions and a real local video are reviewable. A tracked
source scan checked4616 files at the capture candidate and found no ELF/private
paths or matched private-key/common-token signatures; this is not an exhaustive
secret-detection claim. Binaries, SDK/images, private configuration and authentication
material remain excluded. The final source review package has independent hashes.

No candidate push, YouTube upload, terms acceptance or contest submission was
performed. Public candidate/license/video/codelab verification and entrant fields
must be completed after operator authorization; submission success is not claimed.


## E017 — Portable jury review qualification

**Date:** 2026-11-07. **Gate:** passed for documentation/offline packaging.
Product checkpoint `7d8326a454ecf6a1c190413cb9695395c8d2d5cd` was verified on both
public `main` and `implementation/phase-1` before editing. No product runtime file
changed: source fingerprint remains
`02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b`.
This is not a new build, QNX execution, independent developer reproduction or
fresh-guest qualification. E013–E016 native identities/results remain unchanged.

[The jury guide](JURY_START_HERE.md) provides an approximately five-minute
no-QNX route and a separate own-licensed-SDK/guest reproduction route. The latter
covers actual CLI grammar, expected nonzero defect exits, frozen product checkout,
recorded ten-line source correction, explicit candidate selection, original-build
restoration, job test and release verification. It does not require the author's
private VPS/authenticated route. Public YouTube URL remains pending verification.

Dedicated ZIP: `.local/submission/jury-final/resmgrcheck-jury.zip`, 5,204,313 bytes,
SHA-256 `3b3347113656122216bc9e24de9e49b2db11c95a009a010503288aed74192497`.
It contains the entry HTML/Markdown, concise evidence/identity index, exact actual
39b99d7 patch, four existing HTML reports (before/after/comparison/job), three
complete sealed bundles and their root/case evidence/manifests, actual170s MP4/SRT,
license, package manifest and SHA256SUMS. Reports and sealed data are byte copies,
not new synthetic demonstrations or resealed presentation edits. All74 selected
original files match repository bytes;78 checksums cover everything except the
checksum file. Transport diagnostics/unrelated histories, private configuration,
SDK/runtime images and native executables are omitted. No sealed bundle redactions.

Actual commands, from the repository root:

```sh
python3 tests/jury/prepare_review.py --out .local/submission/jury-final --video .local/submission/demo2/demo.mp4
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/browser-binaries" .local/browser-test/bin/python tests/browser/qualify_jury.py --archive .local/submission/jury-final/resmgrcheck-jury.zip --out .local/evidence/jury-qualification-release
python3 -m unittest discover -s tests/host -q
```

[Qualification JSON](evidence/jury-review/qualification.json) and
[browser output](evidence/jury-review/browser-checks.txt) record:

- Fresh temporary ZIP extraction, CRC and all78 SHA-256 checks passed.
- All178 local HTML/Markdown references and fragments resolved inside extraction.
  Explicit online source references are distinguished from offline report resources.
- Three original seals, typed records and canonical evaluations validated; root
  execution bindings/exits and recomputed comparison matched. Both sensor cases
  retain profile/ignore-unblock settings and compatible target; fixture hash changed,
  runner/worker hashes remain shared with job. A disposable tampered extracted
  stream was rejected; original/archive evidence bytes remained unchanged.
- Six HTML documents opened offline in24 Chromium views:1440x1000 and390x844,
  each with JavaScript enabled and disabled. No external requests, load failures,
  page errors or page overflow. Keyboard disclosure and event navigation (with
  JS) passed. No-JS native details remain available. Screenshots are reviewed
  public report/guide content; narrow assertion tables use horizontal scrolling.
- Eight Bash blocks passed syntax checking;18 CLI commands passed current argparse
  parsing, two actual profiles validated,13 README links/anchors checked. The
  archived patch matches the actual39b99d7 commit and applies to the frozen runtime.
- Video checksum matched the original recording; ffprobe confirmed170.000 seconds
  and H.264. No video was generated, uploaded or changed in this task.
- [All107 host tests](evidence/jury-review/host-tests.txt) passed in13.903 seconds.
- Anonymous checks of all six pinned GitHub source links returned HTTP200;
  GitHub detected the public baseline's MIT license. The
  [public-source check](evidence/jury-review/public-source-check.json) preserves
  only URLs/status/license metadata, without authentication or response headers.
- All79 extracted files passed the explicit allowlist/content review (no ELF,
  matched private-key/common-token signatures, private machine paths or route
  configuration files). This is not an exhaustive secret-detection claim.

No qualification check failed. Native rebuild/integration matrices, fresh guest
setup, independent juror execution, YouTube changes/upload and Devpost submission
were **NOT_RUN** in this task. Documentation-only changes invalidate no native
prerequisite. The archive/MP4 stay outside Git; reviewed docs, patch/identity index,
small qualification records/screenshots and optional packaging/browser scripts are
intended public changes. GitHub documentation publication is explicitly authorized;
publication verification is recorded separately after the push.

**Observed publication:** jury documentation commit2720b8b was atomically
fast-forwarded to public main and implementation/phase-1 without force. Both
remote refs matched; anonymous README, guide, index and patch downloads returned
HTTP200 and matched local bytes. MIT license detection passed at that exact commit.
[Publication receipt](evidence/jury-review/publication.json) retains only safe
metadata. This receipt/status follow-up changes records only; the qualified ZIP
and runtime fingerprint remain unchanged. No video upload/channel change, artifact
release upload or Devpost submission was performed.
