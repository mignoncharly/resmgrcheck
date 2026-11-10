# Reviewed immutable administrator settings release

User authorized deployment on2026-11-10. Application candidate is exactly
21a6f571195af35593996d7f9e7b8bb77d843c35; baseline is
3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58. No privileged activation has run.
The session has no noninteractive sudo authorization; passwords must remain local.

The earlier recovery installers are pinned to different baselines and inactive
workers. Do not run them for this change. deploy_security_page.py composes their
existing immutable staging, original virtualenv, release lock, fresh encrypted
backup/isolated restore, static inventory, private/runtime isolation, HTTPS and
audited temporary browser-principal helpers for this exact application release.

From the clean repository, use the deployment-driver checkpoint SHA as DRIVER_SHA:

```sh
/usr/bin/python3 -I -B web/ops/production/deploy_security_page.py \
  --driver-revision DRIVER_SHA
```

This is the read-only scope plan. The authorized local operator applies the same
exact revision with:

```sh
sudo /usr/bin/python3 -I -B web/ops/production/deploy_security_page.py \
  --driver-revision DRIVER_SHA --apply
```

The fixed application candidate is separate from the driver commit. Root rereads
the protected original/candidate manifests and exact canonical unit/vhost bytes.
The candidate is cloned and published into a new /opt/resmgrcheck/releases/SHA;
the old tree, private keys, virtualenv, deployment histories, backups and native
evidence remain. No /opt/resmgrcheck/current source file is patched.

Only the reviewed own Nginx site's immutable static alias changes; HTTP security
configuration, renewal hook, all unrelated vhosts and units are preserved. Web/socket
and executor have a bounded maintenance interruption. Web requests stop before the
final idle checks; active/queued/held native work refuses activation. AI remains
disabled. No database migration, permission grant, native execution/approval, user
password change or customer-runner change is performed. Existing authenticated
browser acceptance provisions and disables only its own audited temporary identity.
It deliberately does not select or run native cases; W036 evidence is retained.

A private journal, diagnostic and acceptance report live under
/var/lib/resmgrcheck/private/operator/security-page-release. The original HTTPS
and executor deployment journals are not rebound or overwritten. On failure the
driver restores only recognized original pointer/site bytes and original services,
leaving failed stages and encrypted backup intact. Unknown state refuses repair.
An interruption after activation starts first restores the recognized baseline on
retry. Retry the same driver SHA; do not delete journals or replace files manually.
Completed verified deployments are checked and reused without repeating acceptance.

Thirty focused release/settings/helper tests pass (root/service effects modeled;
disposable PostgreSQL and actual temporary-file helpers). W037's53 application
security tests and responsive/axe screenshots remain applicable to the fixed
candidate. Actual production backup/restore, activation and browser qualification
are still pending local root execution. Full application rollback has not been
drilled by this change; automatic failure restoration is tested with modeled
services, not claimed as an actual production rollback. Independent UAT remains open.
