# Implementation status

Updated:2026-11-07. Branch:implementation/phase-1.

| Item | Actual state |
| --- | --- |
| Engineering | Complete within the documented lab/adapters/contracts |
| Phases1–6 | Previously passed; affected prerequisites rechecked when changed |
| Phase7 | Passed965c816/E013:75 native IDs,36 exact release expectations,95 host tests |
| Phase8 | Passed73e8bea/E014:15 reports,45 browser views,105 host tests |
| Phase9 | Passed9020e1e/E015: clean source/reused-target workflow,58 native IDs,36 exact release expectations,106 clean host tests |
| Report follow-up |107 host tests/four browser views; preserves known FAIL with withheld NOT_RUN cycles; native/build/engine equivalence recorded |
| Phase10 | Local preparation complete E016: actual170s video, native evidence, source/codelab/evidence map, submission/release copy and review package |
| Jury review | E017: dedicated offline ZIP, two-route guide, 24 browser views/178 local references/78 checksums/3 sealed bundles; 107 host tests passed; no native rebuild |
| Submission-ready | No: verified final public video URL, operator fields and final submission review pending |
| Published/submitted | Product checkpoint7d8326a verified on public main and implementation/phase-1; jury documentation publication authorized in this task; video/submission pending |
| Technical blocker | None |

The existing QNX8.0.0 x86_64/x86pc KVM guest, installed licensed SDP and local
OpenSSH/SFTP route were reused. No fresh-target, SDK reinstall or credential
recreation is claimed. No host reboot/firewall/unrelated service changes.
Native code stays C11/QNX extensions, Make/qcc and a standard-library Python host.

Both real services use the same generic runner/worker/evaluator. Baselines, timeout,
non-restart signal, exact-worker departure/default OCB bookkeeping,20 same-instance
reconnect cycles and both directed orders are qualified. Known defects remain FAIL;
infrastructure/uncertainty stays ERROR, unavailable capability UNSUPPORTED and
withheld work NOT_RUN. Release checker success preserves12 PASS/19 FAIL/2 ERROR/
3 UNSUPPORTED. Cleanup/recovery facts never satisfy original-instance health.

E015's clean source was d2e0a43, runtime digestf13da86d12a15b4a1206e53019c7e9f406e57f23f4a3f9820214519f593cf81b.
It passed the complete CLI/release/source-candidate workflow against the explicitly
reused guest. Native input review fixed uninitialized rejected-command transitions,
current-message/reply bounds and writable-OCB checks;25 actual message checks and
all six owned child reaps passed. Combined custom wire operations remain unsupported;
framework rejection does not claim execution of their tail. qcc static analysis of
16 owned C files emitted no diagnostics; no memory/exhaustive-concurrency claim.

E016's final current-runtime recording is clean d9d2a1a, runtime digest
02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b, correction39b99d7.
Five native cases matched: normal PASS, explicit defect FAIL, source-fixed replay
PASS, departure PASS and job PASS. Contract/settings stayed unchanged; actual fixture
hash changed and runner/worker remained shared. The170s H.264 local video is
.local/submission/demo2/demo.mp4. The original main deployment was restored/verified.
Later records/package edits do not relabel these actual execution identities.

The small guest has3072 file entries. D027/E013/E015/E016 record verified archival
before exact redundant-file removal; start guards and immutable builds remain.
Four Phase9 source-before/after histories and current demo runs remain on target.
Older archived IDs require their committed/local copies; missing status is not PASS.
Keep credentials, SDK/images/binaries and machine configuration outside Git.

The jury entry point is docs/JURY_START_HERE.md. The portable archive is
.local/submission/jury-final/resmgrcheck-jury.zip; E017 records its checksum and
exact scope. It contains the actual170s video, unchanged before/after/job reports,
comparison and evidence. A juror needs no private VPS access for offline review;
reproduction requires their own licensed SDK and compatible lab.

This task authorizes the reviewed documentation commit's GitHub publication only.
Video upload/channel changes, entrant attestations and Devpost submission remain
outside scope. See docs/submission/publication-handoff.md. The historical E016
readiness snapshot predates product publication; it is preserved as evidence.
