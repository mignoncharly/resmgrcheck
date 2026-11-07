# ResMgrCheck

Test declared cancellation and client-lifecycle contracts on QNX 8.0, preserve
native evidence, and replay the same inputs against an explicitly selected fix.
The sensor and job examples use one generic C11 runner/worker and Python evaluator.

## Start Here

- [Five-minute review without QNX](docs/JURY_START_HERE.md#route-a-review-without-qnx-about-five-minutes): real before/after HTML reports, comparison, job evidence and the portable jury ZIP's 170-second demo.
- [Complete hands-on QNX reproduction](docs/JURY_START_HERE.md#route-b-reproduce-on-qnx): your own licensed SDK/guest, build/deploy, deliberate failure, recorded source patch and candidate replay.
- [Real QNX evidence and identities](docs/jury/EVIDENCE_INDEX.md), [full test record](docs/TEST_EVIDENCE.md), and [codelab](docs/codelab.md).
- Final public demonstration video: **URL pending verification**. The actual MP4 is included in the offline jury package; no YouTube URL is invented.

Phases 1–9 have passed their stated gates. Phase 10 local preparation is complete; see
[current status](docs/STATUS.md) and [actual evidence](docs/TEST_EVIDENCE.md).
The [implementation plan](docs/IMPLEMENTATION_PLAN.md) defines the gates.
The [submission handoff](docs/submission/publication-handoff.md) links the reviewable
local demo/package and separates preparation from authorized publication/submission.
The [codelab](docs/codelab.md) walks through an actual source correction;
[dependencies/environment](docs/dependencies.md) and [release review](docs/release-review.md)
state the supported boundary. E015 records clean source/reused-target reproduction.
The [offline report guide](docs/reports.md) explains cases, timelines, replay and
comparison context; E014 records browser inspection.

## Web application branch

`feature/production-web-ai` adds a separate Django/PostgreSQL control plane around
the existing engine. Its [gate status](docs/web/STATUS.md), [actual web/native test
record](docs/web/TEST_EVIDENCE.md), [architecture](docs/web/ARCHITECTURE.md) and
[optional AI controls](docs/web/AI.md) distinguish private staging from production.
The requested public HTTPS application is **not deployed yet**. The revised administrator/access-code gate,
production isolation/hardening and release acceptance remain pending; no frontend rendering result substitutes for those gates.
The CLI and original evidence below remain independently usable.

## Prerequisites

Use Python 3.10+, Git, Make and OpenSSH on Linux, an installed locally licensed QNX SDP
8.0 with `qcc`/`gcc_ntox86_64`, and the already booted owned QNX 8.0.0 x86_64/x86pc
lab guest. This CLI does not install the SDK, start the VM, create credentials or
configure SSH authentication. Keep SDK files, images, keys and generated binaries
outside Git. The qualified guest uses root, SSH on host loopback and a writable
`/data/resmgrcheck`; it is a non-production lab.

Set up the existing OpenSSH alias with verified host keys and working SFTP.
Copy [config/targets.example.json](config/targets.example.json) to ignored
`config/target.local.json`; supply the existing alias/configuration path, expected
remote UID and the actual booted IFS recipe SHA256. The example's zero hash is a
placeholder. See [target configuration and command details](docs/cli.md) and
[QNX setup](docs/setup-qnx.md). Do not copy private configuration into evidence.

## Tested quickstart

Run from the repository root in a fresh shell, after those manual prerequisites:

```bash
source /home/mignon/qnx800/qnxsdp-env.sh
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck validate profiles/sensor.json
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite lifecycle --fixture-mode fixed --out runs/sensor-fixed
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite lifecycle --fixture-mode ignore-unblock --out runs/sensor-broken
resmgrcheck_broken_exit=$?
test "$resmgrcheck_broken_exit" -eq 2
python3 -m resmgrcheck replay runs/sensor-broken/replay.json --target lab --fixture-mode fixed --out runs/sensor-replay
python3 -m resmgrcheck compare runs/sensor-broken runs/sensor-replay --out runs/comparison
python3 -m resmgrcheck report runs/sensor-replay --out runs/sensor-replay/report.html
python3 -m resmgrcheck verify --target lab --suite release
```

Doctor can return 3 with UNKNOWN transfer/engine capability checks before the first
deployment. Build/deploy, then repeat doctor. Output directories for run/replay must
be new. The deliberately broken lifecycle run exits 2: its service FAILs coexist
with a bounded departure-observation ERROR. A single completed timeout defect
exits 1. Release verification can exit 0 while its expected service failures remain
FAIL. It checks the harness's expected outcomes, including unavailable coverage;
it never changes an individual verdict.

The lifecycle suite runs timeout, signal, exact-worker departure, 20 reconnect
cycles on one instance, and both directed completion/cancellation orders.
The shown fixed-mode replay discloses a control-setting change; comparison labels
it incomparable. To prove a source fix, retain the recorded profile/settings, build
and deploy the corrected source, then select the candidate explicitly:

```bash
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck replay runs/source-before/replay.json --target lab --candidate-manifest build/qnx-x86_64/manifest.json --out runs/source-after
python3 -m resmgrcheck compare runs/source-before runs/source-after --out runs/source-comparison
```

`runs/source-before` must be an existing recorded failure from the before-fix
source. Both original and candidate deployments, identities and hashes are kept.
E012/E013 document the actual committed source correction on both fixtures; main
keeps its deliberate defect modes.

## Recover and inspect

Run prints its exact run ID and result location. After lost SSH, use that ID:

```bash
python3 -m resmgrcheck status --target lab --run-id SAVED_RUN_ID
python3 -m resmgrcheck collect --target lab --run-id SAVED_RUN_ID --out runs/recovered
python3 -m resmgrcheck inspect runs/recovered
python3 -m resmgrcheck report runs/recovered --out runs/recovered/report.html
```

Status/collect inspect the existing request. They do not launch it again or signal
stored PIDs. An uncertain launch stays uncertain until evidence establishes its
state; initial partial observations remain in collection history.
Managed fixtures are the default. Explicit external profiles support a read-only
health diagnostic with unverified service build/instance identity. External
lifecycle and changed-build verification remain UNSUPPORTED without the required
adapter observers/identity mechanism. See [adapters](docs/adapters.md).

## Validation and scope

```bash
python3 -m unittest discover -s tests/host -q
python3 tests/qnx/qualify-phase7.py --prefix UNIQUE_RUN_PREFIX
```

The second command requires the configured live lab and SDK and consumes target
storage. It performs the real deployment, execution, recovery, negative and
expected-outcome matrix. Host CI only tests Python logic; it does not run QNX.

See [formats](docs/formats-v1.md), [supported scenarios](docs/supported-scenarios.md),
[reason codes](docs/reason-codes.md), [architecture](docs/architecture.md) and
[limitations](docs/KNOWN_LIMITATIONS.md). Results establish only the recorded
conditions, without exhaustive concurrency, memory-leak absence, hardware timing
or safety-certification claims. Original code is [MIT licensed](LICENSE); QNX
proprietary inputs are excluded.
