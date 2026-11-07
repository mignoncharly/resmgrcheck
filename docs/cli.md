# Host workflow

Run from the repository root with Python3.10+ and OpenSSH. QNX programs require
the installed SDP environment and the owned lab guest already running. The CLI
does not install QNX, create credentials, start a VM, change host services or alter
SSH host keys. Authentication stays in the operator's local OpenSSH configuration.

## Local target setup

`lab` is a configuration name. Copy `config/targets.example.json` to ignored
`config/target.local.json` and set its existing SSH alias/configuration path,
expected remote UID, QNX release/processor/machine, and the SHA256 recipe identity
of the known booted lab IFS. The supplied example's all-zero recipe is a placeholder.
The tested lab uses the existing `.local/ssh_config`, UID0 in the non-production
QNX8.0.0 x86_64/x86pc guest and `/data/resmgrcheck`. Configuration contains routing
and compatibility metadata; it has no password/token/private-key fields. This
version intentionally limits native storage to that lab root. Do not put this
machine-specific file in Git.

```sh
source /home/mignon/qnx800/qnxsdp-env.sh
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck validate profiles/sensor.json
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck doctor --target lab
```

Before the first build/deployment, doctor can return3 with UNKNOWN transfer or
compiled-capability checks. Build/deploy then repeat it. UNKNOWN never becomes
PASS. Doctor distinguishes host tools, SDK environment, available compiler
variant, actual SSH reachability, QNX processor/board/release/UID, command path,
actual SFTP byte roundtrip, and actual deployed-engine capability declarations.
Service-instance capabilities remain UNKNOWN until a run observes them; doctor
never infers private service state. SDK readiness/variant discovery is separate
from the successful real compiler invocation in Make. `--profile PATH` checks
required capabilities against the actual deployed engine and returns3 when absent.
`--out PATH` records JSON; `--verbose` shows full details.

## Build deployment

Deploy validates the complete local build/source record, creates a fresh owned
stage, transfers every executable, downloads and checks their actual bytes, then
publishes a content-identified read-only deployment. The native targetctl helper
checks UID, directory/file types, no-follow paths, exclusive publication and final
ownership markers. Existing complete builds are reverified/reused; an unknown or
incomplete directory is never overwritten or removed. Every attempt remains in
ignored `.local/state/lab/`. The local build's `manifest.json` selects the published
build; native build identity and the file-management helper's identity are separate.
Older source-fixed candidates may use the current independently verified helper.

The remote directory is `/data/resmgrcheck/b-<identity-prefix>`. Full identities
are in the manifest. The small management surface contains no service operations,
process signalling or recursive removal. OpenSSH argument arrays and fixed quoted
remote commands preserve strict host-key checking. Profiles never supply commands.

## Run, status and collect

All output directories must be new for run/replay. These examples intentionally
include a nonzero defective service run; do not assume all commands exit0:

```sh
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite lifecycle --fixture-mode fixed --out runs/sensor-fixed
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite lifecycle --fixture-mode ignore-unblock --out runs/sensor-broken
resmgrcheck_broken_exit=$?
test "$resmgrcheck_broken_exit" -eq 2
python3 -m resmgrcheck replay runs/sensor-broken/replay.json --target lab --fixture-mode fixed --out runs/sensor-replay
python3 -m resmgrcheck compare runs/sensor-broken runs/sensor-replay --out runs/comparison
python3 -m resmgrcheck report runs/sensor-replay --out runs/sensor-replay/report.html
python3 -m resmgrcheck verify --target lab --suite release
```

`fixed` maps to the reviewed `corrected` native fixture mode. Lifecycle expands the
profile into timeout, non-restart signal, departure,20-cycle repeat, completion-
first and cancellation-first, with exact per-case contracts saved. It promotes
required observers, never drops a requested capability. Each family starts a new
fixture; every repeat cycle uses the same fixture and a fresh client. Normal
baselines are within each family. `--suite profile` executes exactly the supplied
family and cycle count. A single broken timeout case exits1; the complete broken
lifecycle exits2 because bounded departure-unobserved ERROR accompanies preserved
contract FAILs and NOT_RUN obligations. Every case outcome stays recorded.

The CLI prints its strict run ID before connecting. An optional `--run-id` accepts
1–40 letters/digits/underscore/hyphen; native case IDs are derived and bounded.
The output retains request.json, replay.json, state/result JSON, diagnostics and
immutable `cases/FAMILY/bundle/` evidence. Root reports are derived; they cannot
overwrite request/raw/result/history files or immutable case members.

A remote `/data/resmgrcheck/sessions/RUN_ID/` stores the owned request, exact plans,
launch-intent receipts and acknowledgements when received. Native case storage
remains `/data/resmgrcheck/runs/CASE_RUN_ID/`. Creation is exclusive. A failed/
uncertain launch never authorizes automatic retry or a new run.

```sh
python3 -m resmgrcheck status --target lab --run-id SAVED_ID
python3 -m resmgrcheck collect --target lab --run-id SAVED_ID --out runs/recovered --wait
python3 -m resmgrcheck inspect runs/recovered
python3 -m resmgrcheck junit runs/recovered --output runs/recovered/results.xml
```

Status means actual collection progress, not a passing service. Collect launches
nothing. It can use a new output or update the same matching request; prior host
states/results/partial bytes are preserved in numbered history snapshots. A lost
acknowledgement is distinct from subsequently observed status. Existing evidence
and original run/supervisor identity are verified before sealing. With no local
deployment-selection receipt, the existing locally built targetctl can be verified
and bootstrapped to recover the remote request by ID. Local target routing and
trusted controller/SDK prerequisites are still required; no service PID or plan is
manually reconstructed. Interrupted multi-family orchestration may leave later
cases NOT_RUN. Collection does not launch those withheld cases.

## External services

Use an explicit registered adapter profile, such as `profiles/sensor-external.json`
or `profiles/job-external.json`, with `service.mode=external-attach` and its explicit
`/dev/resmgrcheck-...` lab device. `--suite health` is a read-only diagnostic:
supervised workers query state, issue normal/prepared operations and use a fresh
health connection. It never submits/releases work, restarts/reconfigures a service,
or gives the supervisor a blocking operation. Cleanup signals only owned workers.

This scope records service build/instance identity as unverified. It does not claim
cancellation, original-instance survival or private queue cleanup. Full external
lifecycle requests return UNSUPPORTED because run-bound pending/unblock observer
feeds are not implemented. Required coverage is never replaced with a health PASS.
Changed-build external replay is likewise unavailable without an adapter mechanism
that identifies the actual running service. Add a real adapter/instrumentation
boundary before claiming that capability for another service.

## Candidate replay and exit meanings

Without a candidate selection, replay uses the original immutable deployment even
if another build is currently selected. `--fixture-mode fixed` explicitly changes
the disclosed control setting. Comparison labels that contrast incomparable; it is
not a source-fix claim. A real fix uses a new Make/qcc build, deploys it and selects
its manifest explicitly while retaining the original contract/settings:

```sh
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck replay runs/source-before/replay.json --target lab --candidate-manifest build/qnx-x86_64/manifest.json --out runs/source-after
python3 -m resmgrcheck compare runs/source-before runs/source-after --out runs/source-comparison
```

The recorded qualification uses a separate committed fixture correction, with the
saved ignore-unblock setting unchanged and different actual fixture hashes. Main's
intentional negative controls stay intact. Each replay reserves/preserves an attempt
ordinal under `.local/state/replays/ORIGINAL_REQUEST_HASH`; failed preflight attempts
are retained. There is no automatic rerun-until-pass.

Execution precedence is130 interruption,2 input/environment/harness/evidence/cleanup
error,3 unavailable required coverage,1 completed contract FAIL,0 complete required
PASS. Offline inspect/report/compare/JUnit return0 when they process valid red
artifacts successfully. `verify --suite release` checks36 exact expected outcomes
on both services and may return0 while planted defect runs remain FAIL. Its own
result explicitly says checker qualification. Failed cleanup/unknown state stops
its dependent sequence. `--help`, `--verbose` and `--debug` are available; detailed
tracebacks require the explicit debug option.

## Offline report

`report EXECUTION_OR_BUNDLE --out FILE.html` renders canonical saved outcomes,
required cycles, obligations, exact observations/event references, actual timeline,
replay instructions and evidence links. `report COMPARISON_DIRECTORY --out FILE.html`
shows changed build/contract/target context. Empty/partial collection stays
INCOMPLETE/ERROR; corrupted finalized bundles are rejected. See [reports.md](reports.md)
for interpretation, offline sharing and browser qualification. The optional filter
script never recalculates verdicts. Product dependencies remain Python stdlib.
