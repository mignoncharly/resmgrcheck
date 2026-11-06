# Known limitations

Updated: 2026-11-06.

- Phases 1–3 have passed their stated native gates. Versioned profiles/contracts, strict host validation, pinned cJSON, generic adapters/runner/worker, the job service and initial shared evaluator are implemented. Production supervision and the complete application remain later gates.
- Only one timeout case per expanded plan is currently supported. Multiple cycles, signal/departure/repetition scenarios, external attach, transport recovery, product replay/comparison and JSON/JUnit/HTML presentation are not yet qualified or implemented as appropriate. Known unsupported capabilities/modes never become PASS.
- The job fixture has one lab job slot and up to eight waiters, with non-consuming completed results until explicit resubmission. This is the documented integration proof, not a general job scheduler. Duplicate-FD/concurrent-close and client-departure obligations remain Phase 5 work.
- The Phase 2 text/C-classified spike remains a regression reference. The Phase 3 path uses structured events and one Python evaluator. Phase 4 persistence, abrupt SSH loss/reconnect and duplicate guards passed a focused QNX subgate; the complete crash/start/probe/frame/sink/cleanup-contamination matrix remains open. Fatal event-sink failure containment still needs work; no cleanup success for that failure is claimed.
- Build/source/artifact declarations are bound and validated on the host and checked by SFTP readback during qualification; they are not native cryptographic attestation. cJSON's review is integration-focused, not a complete upstream security audit.
- The earlier read-only filesystem/socket restrictions were resolved by Full Access; E002–E004 retain historical failures. No license reinstall or credential recreation was needed.
- The dedicated lab reuses an existing host key, uses root in a local non-production guest, and exposes SSH only on loopback. This recipe is intended for the owned lab, not production hardening.
- No server-monitor/slm was running in the recorded lab snapshot. Recheck the final image and any external target rather than assuming the same policy.
- TCG inspection of the older image reported an SSH startup memory fault; the working dedicated KVM image did not. TCG transport is not qualified.
- The complete SDK update level is not established by the baseline package or compiler version. Record observed versions; do not claim SDP 8.0.5.
- Generated images, key material, binaries, and raw local state remain ignored. Reviewed text evidence is committed separately.
- QEMU behavior does not establish hardware worst-case timing, safety certification, or production readiness.

- Persistent run status is the last recorded observation, not live-process identity/cleanup authority or crash/power-loss attestation. Closing SSH, an acknowledgement, and collector exit-code declarations are separate from service assertions and observed child reaping. An unresponsive VM/filesystem can still prevent target progress.
