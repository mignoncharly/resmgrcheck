# Jury evidence index

All three cases were executed on the owned QNX 8.0.0 x86_64/x86pc lab for the
170-second Phase 10 recording. Packaging does not execute them again. The bundle
directories, root evidence and four existing HTML reports are copied unchanged.
Private transport diagnostics and unrelated histories are omitted, without editing
the sealed bundles. `SHA256SUMS` and `package-manifest.json` cover the portable
files; [identities.json](identities.json) records the complete source/build hashes.
Hashes establish integrity/provenance, not malicious-target attestation.

## Read these in order

| Item | Result | Evidence |
| --- | --- | --- |
| Sensor before | FAIL; two independent cancellation obligations | [Report](../evidence/phase10/executions/p10demo2-broken/report.html) |
| Sensor after actual source fix | PASS; same contract and ignore-unblock setting | [Report](../evidence/phase10/executions/p10demo2-after/report.html) |
| Comparison | fixed; compatible target, changed fixture hash | [Report](../evidence/phase10/comparison/report.html) |
| Job, same generic engine | PASS; waiter released, job retained and freshly retrieved | [Report](../evidence/phase10/executions/p10demo2-job/report.html) |

The exact case IDs are `p10demo2-broken-timeout` (attempt1),
`p10demo2-after-timeout` (attempt2) and `p10demo2-job-timeout` (attempt1).
Before bundle ID: `58db59fec146ed83b1a56cf422c7c9f3be02abb111a347a9cfb9273a25d49b96`.
After: `f5a1d7c3ee52dd4cb170fe576195539aafc69ec7e53493226f5eee93de07fdc3`.
Job: `d3cc556eff8ecb945c932072db8d4789b020528f9fb48d9eca91895b3ec4fdac`.

## Exact observations

Event references are **zero-based JSONL record positions**, including the native
manifest as record 0. The report's assertion links select these timeline entries.
An editor using one-based line numbers displays event N at line N+1.

Before-fix: records 110/111/112 establish pending/arming/live unblock; record 114
supports cancellation not completing; record 122 observes pending state still 1.
The service fails both `cancellation_not_completed` and `pending_state_not_released`.
Fresh-client health is NOT_RUN (record 128), rather than inferred from cleanup.
The owned-process cleanup assertion is separately PASS; status has `cleanup_ok=true`
and no unresolved owned children.

After-fix: records 110/111/112 establish the same pending/trigger precondition;
114/115 observe the terminal reply; 119 records the timed result (ETIMEDOUT 260);
129 observes pending zero; 161 records fresh-client value 42. Original-instance
health is observed before that case's cleanup, not supplied by restarting the
earlier defective fixture.

Job: records 126/127/128 establish pending/arming/live unblock; 135 records timed
completion; 145 observes `pending=0`, `job_exists=1`, `job_ready=0`; 178 records
fresh-client retrieval of job 1/value 420. Each assertion carries its expected
facts and the original observed event objects in the sealed `result.json`.

## Source and build identities

Original native source: `d9d2a1a36702488f3f40524f1ebf8cbd4ebc9357`, clean,
runtime digest `02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b`.
Frozen published checkpoint `7d8326a454ecf6a1c190413cb9695395c8d2d5cd` shares that
runtime digest. Later documentation publication does not relabel the original runs.

Actual correction: `39b99d7a163c21c88d831456cc438e3c02a56ac9`, clean,
runtime digest `08b20033edf22f6e0427b75b754a96d8f9fcdb358b8bbea51d224a4cc9e7e041`.
The [recorded patch](source-fix.patch) removes only the ten intentional early-return
lines in the sensor/job unblock handlers. Both versions use qcc/gcc_ntox86_64.

Every selected case has runner SHA-256
`2e33a3fb14996fca493117ff7429f4e91cb36887e0c595ffd2aae75cbc95e334` and worker SHA-256
`d90e77e28be08e6dcbab2697586a5305b4b189365ab83425f43b0cd253d23c43`.
The sensor fixture changes from
`020e50040f9993d37efa6dd5e6773a56dab51bbb8ec2545ac56330372b552174` to
`99a511d86617ab807efc3ec1ac9b4d100b8c42fec8a4c358bff908562a48078e`.
Both sensor runs retain profile hash and fixture setting, as the comparison records.
The QNX recipe hash is provenance of the recorded guest, not a configuration to
copy onto a different guest. Use your own IFS hash for reproduction.

## Offline opening and integrity

Extract everything before opening `START_HERE.html`. Reports embed CSS and optional
filter JavaScript, require no server/network and retain native disclosures without
JavaScript. Local raw links require the included directory structure. The guide's
explicit GitHub source references require a network; they are not report resources.

From the extracted package root on Linux:

```sh
sha256sum -c SHA256SUMS
```

In a product checkout, `inspect` additionally validates the bundle seal, typed
records and canonical evaluation; valid FAIL evidence still processes successfully:

```sh
python3 -m resmgrcheck inspect docs/evidence/phase10/executions/p10demo2-broken/cases/timeout/bundle
```

This is a scoped developer-lab result, not universal adapter support, measured
memory-leak absence, exhaustive scheduling or safety certification. See the five
verdict definitions in [the entry guide](../JURY_START_HERE.md).
