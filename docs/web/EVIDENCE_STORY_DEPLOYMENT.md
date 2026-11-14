# Evidence explanation release and compatible rollback

Owner authorized the six hackathon improvement priorities on 2026-11-14.
W043 completion (2026-11-14): the operator's final result confirms this procedure
passed. Agent checks separately confirm active application
7ecb81231cbce91dfe866d515a6458073b0d0e0e, healthy web/executor services and readable
public case pages. Protected receipts were not reread. Do not repeat the completed
rollout/backup/rollback. Independent external UAT remains pending; evidence is in
[evidence-story-release](evidence/evidence-story-release/operator-result.json).

The procedure below is retained for provenance/recovery. Its original application
was dfe1060e6a517b686d4948f8cea2fc848fcd0956; the exact presentation candidate
was 7ecb81231cbce91dfe866d515a6458073b0d0e0e.
Its only application changes are the report renderer, shared assertion-story
module, case template and presentation filter. Native C/evaluator/authorization,
migrations, dependencies, canonical units and customer/AI policy are unchanged.

The new driver is `web/ops/production/deploy_evidence_story.py`. It has a separate
protected journal under `/var/lib/resmgrcheck/private/operator/evidence-story-release`.
Historical HTTPS/navigation/native acceptance records are retained. Choose the
exact committed driver SHA recorded in the current handoff; do not use a moving
branch name. From a clean repository:

```sh
python3 -I -B web/ops/production/deploy_evidence_story.py --driver-revision DRIVER_SHA
sudo python3 -I -B web/ops/production/deploy_evidence_story.py --driver-revision DRIVER_SHA --apply
```

The first command is read-only. The second needs local sudo authentication;
never paste a password or protected configuration into chat. The agent has no
noninteractive sudo authentication and has not performed this production drill.

The procedure verifies exact source ancestry/scope, canonical units, known pointer
and own Nginx site, current native idleness, and a fresh encrypted backup with an
isolated restore. It temporarily quiesces only the ResMgrCheck web/socket/executor.
Existing unrelated applications, database contents, audit history, keys, images,
native builds and evidence are preserved. No native QNX tests are launched.

It then performs this actual application round trip:

1. Activate the immutable candidate and its exact static alias; verify runtime,
   TLS, readiness, password/code authorization and browser journeys.
2. Quiesce and confirm no pending/active native work. Restore the previous
   application/static alias. Verify old readiness and authenticated browser journeys.
3. Quiesce and confirm idleness again. Restore the candidate and verify runtime,
   TLS, readiness and a separate final browser journey.

Separate protected acceptance directories preserve candidate-before-rollback,
rollback and candidate-after-rollback receipts. Successful temporary accounts/codes
are disabled/revoked with audit retained. Unknown state refuses changes. A failure
attempts restoration only to the recognized original application, retaining the
failure and incomplete stages for investigation. It performs no reverse migrations,
database replacement, arbitrary release selection or data deletion.

The local24 release-helper tests passed with real temporary files and modeled root/
service changes. W043 adds the actual operator `full_application_rollback: passed`
result and separately corroborated active delivery. Independent external UAT remains
a separate uncompleted gate.
