# Reproduce a cancellation failure and replay its correction

This codelab uses an explicit intentional defect in the project-owned fixture.
It does not describe a vulnerability in QNX or a third-party service. The observed
release reproduction used clean source d2e0a43 and source correction3d0d7b1, the
same saved contracts/settings, real qcc builds and the explicitly reused QNX lab.
See E015 for exact manifests, outputs and limitations.

## 1. Prepare the declared lab

Follow README's manual prerequisites: installed/licensed SDP, already booted owned
QNX8.0.0 x86_64/x86pc guest, existing locally authenticated OpenSSH alias/SFTP,
verified host keys and ignored target metadata. The CLI does not create these.
Use a Git checkout, Python3.10+, Make and OpenSSH. Run from the repository root:

```sh
source /home/mignon/qnx800/qnxsdp-env.sh
python3 -m resmgrcheck doctor --target lab
python3 -m resmgrcheck validate profiles/sensor.json
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
python3 -m resmgrcheck doctor --target lab
```

The initial doctor can return3 with UNKNOWN deployment/transfer/capability checks.
After build/deploy, repeat it. UNKNOWN is not a passed prerequisite. Use new output
paths and run IDs; do not remove unrelated storage to reuse an example name.

## 2. Understand and exercise the obligation

`profiles/sensor.json` selects sensor-v1/sample, expected value42, observable
pending/unblock/state/health, zero pending after cancellation, a500 ms operation
timeout and2000 ms cancellation allowance. Setup/probe/cleanup bounds are separate.
The tool first checks ordinary read, prepared _IO_READ/MsgSendv and deferred release.
It then confirms pending before cancellation, inspects state and uses a new client
before stopping the same service instance. A long-looking call alone is insufficient.

```sh
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite profile --fixture-mode fixed --out runs/normal
python3 -m resmgrcheck report runs/normal --out runs/normal/report.html
```

Expected fixed result: PASS/all_obligations_satisfied. The normal baselines are
part of this timeout family. For all six families and20 reconnect cycles, use
`--suite lifecycle`; release verification covers both services and negative controls.

## 3. Save the explicit failure

```sh
python3 -m resmgrcheck run --target lab --profile profiles/sensor.json --suite profile --fixture-mode ignore-unblock --out runs/source-before
resmgrcheck_before_exit=$?
test "$resmgrcheck_before_exit" -eq 1
python3 -m resmgrcheck report runs/source-before --out runs/source-before/report.html
```

Observed in the clean reproduction: FAIL with both `cancellation_not_completed`
and `pending_state_not_released`, exit1 for this single timeout family. The full
broken lifecycle can exit2 because departure evidence is independently unestablished.
The checker preserves those distinctions; it does not discard one reason to pick
another. Report generation returns0 when it successfully renders valid red evidence.

Open the case details: compare the cancellation allowance/pending-zero contract
with actual pending/unblock observations, result/limit, public state, health and
cleanup. Event links point to the actual target stream; a configured deadline is
not itself a measured expiry. Missing required observations remain explicit.
Keep `request.json`, `replay.json` and all sealed case bundles intact. If SSH is
lost, recover this run's ID with status/collect; do not start a duplicate.

## 4. Apply the real source correction in a separate checkout/branch

`native/fixtures/sensor.c:sensor_unblock()` already delegates default bookkeeping,
checks a current MsgInfo unblock and matches the pending owner. The intentional
`if (ignore_unblock)` block logs the ignored request and returns NOREPLY before the
original request is completed. Remove that early-return block. Preserve default
handling, live-owner checks, terminal bookkeeping and removal after MsgError.
The analogous correction is in `native/fixtures/job.c:job_unblock()`.

The recorded actual two-file patch is in
[the clean qualification evidence](evidence/phase9/qualification/source-fix.patch).
It removes10 lines, without changing the profile, timing or saved fixture setting.
For an isolated demonstration checkout that contains the original defect:

```sh
git switch -c demo/fix-unblock
git apply --check docs/evidence/phase9/qualification/source-fix.patch
git apply docs/evidence/phase9/qualification/source-fix.patch
git add native/fixtures/sensor.c native/fixtures/job.c
git commit -m 'Complete live owned unblock requests'
make qnx QNX_VARIANT=gcc_ntox86_64
python3 -m resmgrcheck deploy --target lab --build build/qnx-x86_64
```

Original runs remain in the original checkout; use their actual absolute replay
path if the corrected checkout is elsewhere. Authentication/target routing stays
local. Native build records include actual revision/dirty state and file hashes.
Do not relabel Linux output or a mode switch as a source correction.

## 5. Select the candidate explicitly and inspect the next client

```sh
python3 -m resmgrcheck replay runs/source-before/replay.json --target lab --candidate-manifest build/qnx-x86_64/manifest.json --out runs/source-after
python3 -m resmgrcheck compare runs/source-before runs/source-after --out runs/source-comparison
python3 -m resmgrcheck report runs/source-after --out runs/source-after/report.html
python3 -m resmgrcheck report runs/source-comparison --out runs/source-comparison/report.html
```

The recorded source-corrected replay passed with unchanged ignore-unblock setting
and contract; comparison was fixed. The actual fixture hash/source changed while
original/candidate identities were preserved. The report shows native ETIMEDOUT260,
pending zero, and a successful fresh-client result42 on that run's original
fixture, before cleanup. Restart/recovery cannot supply that health assertion.
The broken earlier fixture is not silently restarted as proof of its own survival.

Without an explicit candidate, workflow replay selects the original immutable
build. A `--fixture-mode fixed` control contrast changes settings and is labelled
incomparable; it is a separate demonstration. Keep both builds/results and every
attempt. Run the planted-defect release matrix in the unmodified main checkout;
the source-corrected branch intentionally changes the old negative control.

## 6. Check integration beyond one service

The clean gate also ran job-v1 through the identical runner/worker/evaluator, with
ordinary devctl versus prepared _IO_DEVCTL/MsgSendv. Its pending waiter cancellation
retains job_exists1/job_ready0, followed by completion and fresh retrieval of job1,
value420. Forced waiter departure/reconnect/ordering are in the release matrix.
See the worked job adapter steps in adapters.md and E015's unchanged generic
runner/worker hashes. No external developer adoption or memory-leak absence is
claimed. Results are bounded directed tests on this lab, not exhaustive concurrency.
