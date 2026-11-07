# Continue into Phase 8

Read AGENTS.md, STATUS.md, Phase8 in IMPLEMENTATION_PLAN.md, E013 in
TEST_EVIDENCE.md, DECISIONS.md, KNOWN_LIMITATIONS.md, cli.md and formats-v1.md.
Branch remains implementation/phase-1. Preserve unrelated changes.

Phases1–7 passed. Do not repeat them unless a change invalidates a prerequisite.
E013 records actual source/binary/evaluator identities,75 distinct native case IDs,
36 expected release outcomes and95 host tests. Qualification source was dirty over
557c313 with the exact digest in evidence/phase7/qualification/index.json; do not
relabel those bytes as a clean base run. Published checkpoint follows the full gate.

Reuse the installed /home/mignon/qnx800/qnxsdp-env.sh, qcc and existing KVM lab.
The ignored config/target.local.json selects the existing .local/ssh_config alias.
Keep credentials/config contents, SDK, generated binaries and images outside Git.
No reinstall, host reboot/firewall change or broad process-name killing.

CLI: doctor/validate/deploy/run/status/collect/replay/compare/report/verify. See
README and cli.md for exact setup and tested workflow. Request identity and launch
intent precede one remote launch. Lost ACK stays uncertain; status/collect recover
by the same ID, even without local selection state. History keeps prior uncertainty,
interruption and partial bytes. Stored PIDs never authorize cleanup. Native exact
ownership, service-facing workers and dependent quarantine remain unchanged.

The current report is a minimal offline HTML view. Phase8 must add summary,
case/cycle details, actual event timeline, expected/observed values, replay and
artifact links, accessible/no-JS presentation and honest comparison context. Use
saved canonical outcomes; do not recalculate verdicts in JavaScript. Render actual
QNX bundles in evidence/phase7, preserve JSON/JUnit, escape every input, make
incomplete/unsupported obvious and inspect laptop/narrow screens in a browser.

Browser test tooling is installed only in ignored .local/browser-test (Playwright)
and .local/browser-binaries (Chromium headless shell). Product stays Python stdlib,
no server/framework/network assets. Browser readiness was observed, not yet a
Phase8 report gate. Document any synthetic formatting cases separately.

Target data storage has3072 file entries. D027/E013 record the real inode ENOSPC
experiment and verified archival of closed histories; empty start guards remain.
Final p7gate3 native/status/session evidence is retained on target. Do not overwrite,
remove unknown directories or infer old archived IDs passed. Monitor df -g /data
before another large native matrix. Complete archives remain .local/evidence.

The committed source-fixed candidate remains .local/phase6-fixed-source at c26365e;
main keeps intentional negative controls. Explicit candidate-manifest replay proves
source fixes; changing fixture-mode is a disclosed incomparable contrast. External
attachment only supports read-only health with unverified build/instance identity;
full lifecycle/candidate replay remains UNSUPPORTED without adapter observers.

No push performed. Follow gates in order and commit coherent checkpoints.
