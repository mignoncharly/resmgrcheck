# Known limitations

Updated: 2026-11-07.

- Phases 1–9 have passed their stated gates. The Phase 5 terminal qualification covers both real services and all six scenario families. Immutable evidence, explicit candidate replay, comparison and JUnit passed E012. Phase7 adds the complete lab CLI; Phase8 adds the detailed offline report.
- Each expanded plan selects exactly one family. Repeat plans run 1–20 cycles (default20) on the same fixture, with no service reset between cycles. Independent family runs use a new instance. External lifecycle is UNSUPPORTED; explicit read-only health attachment is supported with unverified build/instance identity; automatic-restart signal mode is UNSUPPORTED. Required missing capabilities never PASS.
- The job fixture has one lab job slot and up to eight waiters, with non-consuming completed results until explicit resubmission. Retained jobs and leaked waiters are observed separately. This is a fixture, not a general scheduler.
- Departure and duplicate-FD/final-OCB bookkeeping passed on this single-dispatch-thread fixture. Observed close callbacks had nonzero receive IDs; the synthetic rcvid==0 branch is guarded and delegated but was not observed natively. Concurrent multithreaded OCB access is not qualified.
- Directed completion/cancellation barriers, an obsolete real notification and a real unmatched control cancellation were exercised. These checks do not cover all receive-ID reuse patterns or exhaustive concurrency. Reconnect success and bounded counters do not establish absence of memory leaks; no memory measurement was performed.
- The Phase 2 text/C-classified spike remains a regression reference. The generic path uses structured events and one Python evaluator. Phase 4's complete native failure matrix passed E009, including sink/full-filesystem containment, failed cleanup/dependent quarantine, unknown ownership, fixture interference and SSH recovery. Explicit lab fault controls qualify those paths; they are not externally observed product defects. No real server-monitor policy was present or tested.
- Build/source/artifact declarations are bound and validated on the host and checked by SFTP readback during qualification; they are not native cryptographic attestation. cJSON's review is integration-focused, not a complete upstream security audit.
- The earlier read-only filesystem/socket restrictions were resolved by Full Access; E002–E004 retain historical failures. No license reinstall or credential recreation was needed.
- The dedicated lab reuses an existing host key, uses root in a local non-production guest, and exposes SSH only on loopback. This recipe is intended for the owned lab, not production hardening.
- No server-monitor/slm was running in the recorded lab snapshot. Recheck the final image and any external target rather than assuming the same policy.
- TCG inspection of the older image reported an SSH startup memory fault; the working dedicated KVM image did not. TCG transport is not qualified.
- The complete SDK update level is not established by the baseline package or compiler version. Record observed versions; do not claim SDP 8.0.5.
- Generated images, key material, binaries, and raw local state remain ignored. Reviewed text evidence is committed separately.
- QEMU behavior does not establish hardware worst-case timing, safety certification, or production readiness.

- Persistent run status is the last recorded observation, not live-process identity/cleanup authority or crash/power-loss attestation. Closing SSH, an acknowledgement, and collector exit-code declarations are separate from service assertions and observed child reaping. An unresponsive VM/filesystem can still prevent target progress.

- Recovery journaling is bounded to 512 frames / 2 MiB for legacy timeout/signal, 2048 / 4 MiB for extended single cases and 8192 / 8 MiB for repeated runs and depends on a separate writable descriptor and supervisor memory. Simultaneous/global storage failure, supervisor death or a stalled VM can prevent sealing; the host must report infrastructure ERROR and cannot infer successful remote cleanup. No power-loss durability or hard real-time scheduling guarantee is claimed.
- The cleanup-failure experiment withholds the measured fixture-stop escape and records a real unresolved original cleanup, followed by separate owned lab recovery. Unknown ownership is tested by deliberately discarding wait status. Neither experiment authorizes cleanup using stale persisted PIDs, nor does recovery supply original-instance health.

- The Phase7 CLI uses a configured OpenSSH alias and one qualified QNX8.0.0 x86_64/x86pc lab layout under /data/resmgrcheck. It verifies target compatibility and actual SFTP artifact hashes. Other architectures/releases, arbitrary remote applications and dynamic adapters are not supported. VM startup, SDK licensing and SSH authentication remain manual prerequisites.
- Native replay changes a committed qualification fixture source branch (c26365e) while preserving the original ignore-unblock setting and contract. Main keeps its deliberate defect controls. This proves changed-build reproduction/fix behavior for both fixtures, without guaranteeing scheduler interleaving or arbitrary production-service portability.
- Evidence bundle hashes/read-only modes detect changes and bind identities; they are not malicious-target attestation, trusted timestamps or power-loss guarantees. Git copies preserve evidence bytes but do not enforce runtime read-only file permissions. The repository form currently records evaluator Git/source identity; packaging outside a Git checkout is later distribution work.
- All currently expanded families/cycles are required. Optional scenario names do not execute optional cases, and no export option waives required coverage. JUnit emits skipped plus suite-level error for unavailable required coverage. Native lab fault controls are not portable replay settings and are rejected by replay.
- A lost replay launch acknowledgement preserves the request/run ID and partial observations when reachable; it does not prove that nothing launched. There is no automatic relaunch. Phase7 status/collect retrieves the exact stored request by ID, including loss of local deployment selection. It cannot guarantee recovery after VM/storage loss. Native persistent status/SSH-loss recovery stays qualified from Phase4.

- Doctor observes actual host tools, compiler variant discovery, target uname/UID,
  SSH command path, SFTP roundtrip and deployed compiled-engine capabilities.
  Service-instance capabilities remain UNKNOWN until execution observes them.
  Before first deployment, UNKNOWN readiness may return3 and require build/deploy.
- External-health uses only registered read-only operations. Private lifecycle
  observers and running external-service build identity are unavailable, so full
  lifecycle and candidate-build replay remain UNSUPPORTED. Public health does not
  establish original-instance survival, absence of restart or private queue cleanup.
- The reused guest data filesystem has3072 file entries; inode exhaustion occurred
  during qualification with free data blocks remaining. Historical completed logs
  were verified/archived locally before removing redundant target file copies.
  Native start-directory guards remain. Archived IDs require their offline copies;
  status/collect cannot recover bytes removed from the target. There is no automatic
  retention/garbage collector. Monitor `df -g /data` before large release matrices.
- Published deployment modes/host readback hashes are integrity checks in a trusted
  lab, without malicious-root attestation. A partially published deployment is
  preserved and rejected. Metadata bootstrap writes a fresh owned helper directory;
  it does not clean up unknown storage or infer process ownership.
- Host-only CI is provided for Python3.10/3.12; no hosted run is claimed until the
  workflow actually executes. Local qualification used the installed Python version.

- HTML is self-contained for display; raw artifact links require the accompanying
  local evidence tree. Browser validation uses Chromium headless shell at laptop
  and narrow widths, plus JavaScript-disabled views; it is not cross-browser or
  assistive-technology certification. Tables scroll horizontally on narrow screens.
- Comparison context is conservative: a changed recorded QNX target fingerprint or
  IFS recipe makes the runs incomparable even with unchanged service contract.
  Only recorded fields are compared; this is not target attestation. A comparison
  HTML view displays saved derived metadata and discloses that source bundle
  verification is separate. Older metadata with absent target fields stays unknown.

- Custom fixture devctl wire operations use a fixed uncombined protocol. Combined
  custom operations are rejected; tested combined prefixes returned framework
  EBADMSG before the custom tail ran. No combined-tail execution/support claim.
  Native input review now checks lengths, actual reply capacity, access mode and
  unchanged state after errors. It does not make this a general security scanner.
- Completed p7gate3 target histories/sessions were subsequently verified/archived
  for Phase9 storage. Their committed/offline copies remain available; exclusive
  start guards are retained. Status/collect cannot retrieve archived target bytes.

- E015 clean source reproduction reused the existing guest and local authentication;
  it did not recreate a fresh target. Native/build/engine files are bound to clean
  d2e0a43. A report-only summary correction has separate107-host/four-view browser
  evidence and explicit source equivalence, without relabelling native observations.

- Phase10's real local video is170 seconds with English on-screen explanation and
  no audio/music. Its SDK/native runs are actual; the capture surface is the host
  CLI viewer and generated offline report. Public YouTube upload, new candidate
  publication/license detection, codelab URL and submission confirmation are pending.
- For demo storage,54 completed Phase9 histories/39 sessions were verified/archived,
  retaining start guards and all four source-before/after histories. Offline/Git
  evidence remains; archived on-target IDs cannot be collected as present bytes.
