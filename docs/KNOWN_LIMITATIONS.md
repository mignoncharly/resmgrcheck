# Known limitations

Updated: 2026-11-06.

- Phases 1 and 2 have passed on the recorded x86_64 QNX 8.0.0/KVM image. The deferred sensor fixture, client and supervisor are a native spike, with two actual defect/correction replays. This is not the complete application: versioned adapters, job service, deterministic host evaluator, full suite, replay product and reports remain subsequent gates.
- Only ordinary read, explicit deferred release and timeout cancellation are qualified here. Signal interruption, client-departure service obligations, duplicate-FD/concurrent-close behavior, and repetition suites are not yet validated. Observing reply-blocked client cleanup is not the full client-departure scenario gate.
- Phase 2 emits bounded text events and an initial C verdict for the native spike. The final versioned schemas, producer completion/error model, host-only evaluator and report exporters do not exist yet. Phase 4 must broaden fault handling, contamination and transport recovery tests.
- The earlier read-only filesystem/socket restrictions were resolved by Full Access; E002–E004 retain historical failures. No license reinstall or credential recreation was needed.
- The dedicated lab reuses an existing host key, uses root in a local non-production guest, and exposes SSH only on loopback. This recipe is intended for the owned lab, not production hardening.
- No server-monitor/slm was running in the recorded lab snapshot. Recheck the final image and any external target rather than assuming the same policy.
- TCG inspection of the older image reported an SSH startup memory fault; the working dedicated KVM image did not. TCG transport is not qualified.
- The complete SDK update level is not established by the baseline package or compiler version. Record observed versions; do not claim SDP 8.0.5.
- Generated images, key material, binaries, and raw local state remain ignored. Reviewed text evidence is committed separately.
- QEMU behavior does not establish hardware worst-case timing, safety certification, or production readiness.
