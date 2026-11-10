# Reviewed immutable navigation deployment

Owner authorized deployment on2026-11-10. Current pointer is the security-page
release21a6f571195af35593996d7f9e7b8bb77d843c35. Navigation candidate is exactly
dfe1060e6a517b686d4948f8cea2fc848fcd0956. No navigation activation has run.

Use deploy_navigation.py, not the earlier deploy_security_page.py. This is a
separately pinned instance of the same reviewed immutable release procedure. Its
activation/recovery logic is identical; the baseline, candidate, twelve-file
navigation scope, journal path and journal kind differ. The earlier driver and
completed security-page/HTTPS/executor journals remain unchanged.

From the clean repository, replace DRIVER_SHA with this deployment-driver
checkpoint's full SHA. Review the unprivileged plan:

```sh
/usr/bin/python3 -I -B web/ops/production/deploy_navigation.py \
  --driver-revision DRIVER_SHA
```

The local operator applies it with one resumable command:

```sh
sudo /usr/bin/python3 -I -B web/ops/production/deploy_navigation.py \
  --driver-revision DRIVER_SHA --apply
```

The agent's sudo session requires a password. Authentication must remain local;
no password or protected configuration should be pasted into chat.

The driver stages a new immutable candidate with the existing shared virtualenv,
requires a fresh encrypted snapshot and isolated restore, checks native idleness,
stops new web requests, verifies idleness again, and then performs a bounded
web/socket/executor maintenance interruption. It switches the current pointer,
verifies schema without migrations, publishes separate immutable static assets,
validates actual web isolation/private readiness and updates only the own Nginx
static alias. Syntax/TLS/public CSS identity and audited temporary-account browser
acceptance are required. No native test, target approval, permission grant, password
change, AI/customer-runner activation, unit edit or unrelated vhost change occurs.

The existing UI browser workflow qualifies password/code sessions, CSRF/origin,
tenant boundaries and desktop/no-JS mobile routes. Native selection is deliberately
not requested for this UI-only release; actual W036 native evidence is retained.
Navigation itself already has67 local regression tests plus6 refreshed navigation
tests and32 administrator/restricted browser views in the candidate evidence.

Protected state, diagnostic and acceptance output are isolated under
/var/lib/resmgrcheck/private/operator/navigation-release. Old immutable releases,
encrypted backups, keys, native IDs/evidence and all prior deployment history remain.
Unknown pointer/site/unit/queue/source/journal state refuses activation. Failures
restore only exact recognized original resources; incomplete stages remain for
review. Interrupted activation resumes by first restoring the recognized baseline.
Retry the same driver SHA, without deleting or editing records. A verified release
is revalidated and reused instead of repeating acceptance.

Thirty-three release-helper tests passed; root/service changes are modeled and
temporary-file checks are real. Production activation, backup/restore and browser
outcomes are pending operator execution. Full application rollback has not been
drilled by this change and independent external UAT remains open. Do not claim
production navigation passed until actual activation/acceptance output exists.
