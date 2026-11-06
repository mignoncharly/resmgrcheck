# Known limitations

Updated: 2026-11-06.

- Phases 1–4 have passed their stated native gates. Versioned profiles/contracts, strict host validation, pinned cJSON, generic adapters/runner/worker, the job service and initial shared evaluator are implemented. The complete scenario suite and application remain later gates.
- One explicit timeout or non-restart signal case per expanded plan is supported. Phase 5 signal interruption passed E010 on both services, including targeted negative controls. Client departure, 20-cycle same-instance repetition, directed ordering, external attach, application transport commands, product replay/comparison and JSON/JUnit/HTML presentation remain unqualified or unimplemented. Known unsupported capabilities/modes never become PASS. Automatic-restart signal mode is explicitly UNSUPPORTED.
- The job fixture has one lab job slot and up to eight waiters, with non-consuming completed results until explicit resubmission. This is the documented integration proof, not a general job scheduler. Duplicate-FD/concurrent-close and client-departure obligations remain Phase 5 work.
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

- Recovery journaling is bounded to 512 frames / 2 MiB and depends on a separate writable descriptor and supervisor memory. Simultaneous/global storage failure, supervisor death or a stalled VM can prevent sealing; the host must report infrastructure ERROR and cannot infer successful remote cleanup. No power-loss durability or hard real-time scheduling guarantee is claimed.
- The cleanup-failure experiment withholds the measured fixture-stop escape and records a real unresolved original cleanup, followed by separate owned lab recovery. Unknown ownership is tested by deliberately discarding wait status. Neither experiment authorizes cleanup using stale persisted PIDs, nor does recovery supply original-instance health.
