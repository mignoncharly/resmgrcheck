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
