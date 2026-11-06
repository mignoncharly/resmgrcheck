# ResMgrCheck implementation instructions

Read `docs/STATUS.md`, `docs/AGENT_HANDOFF.md`, and the applicable sections of `docs/IMPLEMENTATION_PLAN.md` before changing files. Inspect the working tree and preserve unrelated work.

The project owner has selected the new repository `mignoncharly/resmgrcheck`. Continue here on the Ubuntu development host. The previous Windows workspace is not a prerequisite for this repository.

- Work on `implementation/phase-1` for the remaining Phase 1 work. Commit coherent checkpoints. Follow the ten phases in order, continuing autonomously after each passing gate.
- Keep status, decisions, actual test evidence, and limitations current. A file existing or a host-only test passing does not complete a native gate.
- Reuse the installed QNX SDP and the verified QEMU environment. Keep account authentication local. Do not request or expose passwords, tokens, license keys, private SSH keys, environment-file contents, or protected configuration.
- Use `qcc` for QNX builds. Never substitute the Linux compiler and label its output a native QNX result.
- Keep the native implementation in C11 with necessary QNX extensions, the build in Make, and the host application in Python 3.10+ using the standard library, as specified in the plan.
- Add components when their phase needs them. Do not scaffold a frontend, web service, database, or fake transport.
- Limit target access to the intended lab. Inspect and preserve existing host services. Do not reboot the host, change its firewall, disable unrelated monitoring, or use broad process-kill commands as routine setup.
- Keep SDK contents, generated QNX images, compiled binaries, license material, and machine-specific authenticated configuration outside Git. The MIT license covers original project material.
- Distinguish operator-provided bootstrap evidence from commands you execute against the repository revision. Record actual outcomes without fabricating native observations.
- Finish the basic target connection/transfer route and native capability inventory before calling Phase 1 complete. Full host CLI automation is Phase 7.

