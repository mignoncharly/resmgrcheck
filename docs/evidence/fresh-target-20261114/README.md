# Fresh QNX target reproduction, 14 November 2026

This is agent-executed reproduction on a newly built QNX image, not an independent
developer result. The existing SDK/client authentication were reused; image host
keys and writable guest state were newly generated. No author-bootstrap image or
guest host keys were copied. KVM guest: QNX8.0.0 x86_64/x86pc,1CPU/1GiB,
loopback-only SSH on a previously unused port. The original lab was preserved.

| Case | Actual outcome | Evidence |
| --- | --- | --- |
| Sensor baseline/timeout | PASS | [Bundle](normal/bundle/bundle.json) |
| Intentional sensor cancellation defect | FAIL | [Bundle](broken/bundle/bundle.json) |
| Same-contract source-corrected replay | PASS | [Bundle](after/bundle/bundle.json) |
| Job service | PASS | [Bundle](job/bundle/bundle.json) |

Original source7ecb81231cbce91dfe866d515a6458073b0d0e0e; actual committed source
correction570a95696dbf17cb3d1a2848a2e6db1341b99e75. Both build using real qcc.
The [patch](source-fix.patch) removes the same explicit ignored-unblock early return
in the two fixtures. [Comparison](comparison.json) is fixed: saved contract/settings
unchanged, changed fixture hash. All four native cases have observed cleanup with
no unresolved owned children. Exact IDs/builds/hashes are in [index.json](index.json).

The actual sequence was configure with a distinct target name; create/verify the
private target root; doctor(exit3 before deployment); qcc Make build and immutable
readback-verified deploy; doctor(exit0); normal/broken/job runs; actual corrected
checkout qcc build/deploy; explicit candidate replay; compare; reports; canonical
bundle inspection. Runtime checks do not establish hardware worst-case timing.

Fresh execution exposed two onboarding omissions, now documented: the guest's
private `/data/resmgrcheck` root must exist with correct ownership/type, and a second
lab in one checkout needs its own target name as well as a separate config path.
The first orchestration attempt stopped after root creation due to a local progress
logger Path serialization error, before any native case/deployment. Its logs remain
local. A separate output retains the corrected full sequence and original attempt.

After checking native cleanup, the exact new guest was shut down; its listener
closed, while the original22220 listener remained. Images, binaries, keys, configs,
transport diagnostics and full local commands stay outside Git. These43 selected
files were copied unchanged; SHA256SUMS permits integrity checking. The independent
exercise and fresh-user feedback still require an external participant.
