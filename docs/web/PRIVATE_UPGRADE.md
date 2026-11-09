# Initial expanded private release from3821952

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. Actual private release remains544f22c; corrected immutable
activation/public acceptance is pending. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

This is an operator-run private upgrade, not authorization to expose HTTPS. Keep
P8 IN PROGRESS. The initial expanded release keeps customer machine endpoints and
AI disabled, preserves canonical units/LoadCredential/nonroot execution, and never
starts services itself. Separate-host/customer/public/independent gates remain.
Do not use prepare.py or the older narrowly scoped recovery drivers for this change.
Do not patch /opt/resmgrcheck/current, edit existing manifests or reverse migrations.

## Review and stage

Use the final clean committed feature/production-web-ai checkout. Replace the SHA
below with the exact full source revision supplied in the handoff; review its diff
from3821952. The unprivileged plan checks commit ancestry and freezes historical
migrations, dependencies, runtime launcher and canonical systemd units. The apply
path also verifies original preparation/credential/socket/restore records, old
release/index/virtualenv, known current pointer, source-key metadata and unchanged
units/no drop-ins. An exclusive release lock prevents concurrent operators.

```sh
cd /home/mignon/projects/resmgrcheck
rmc_revision=$(git rev-parse HEAD)
git status --short
python3 -B web/ops/production/upgrade_private.py --revision "$rmc_revision"
```

Stop if the working tree is not clean or the source revision differs from the
reviewed handoff. Stop only dedicated ResMgrCheck web/jobs/timers; the dedicated
DB and all unrelated VPS applications stay running. Do not stop a backup in flight:
wait for its protected completion first. No timer/service is automatically restored
until its previous state is recorded and the new private runtime passes.

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service \
  resmgrcheck-executor.service resmgrcheck-ai.service \
  resmgrcheck-backup.timer resmgrcheck-status.timer resmgrcheck-status.service
sudo /usr/bin/python3 -B web/ops/production/upgrade_private.py \
  --revision "$rmc_revision" --operation stage --apply
```

Use a shell that stops on failure, or execute/check each command separately. Stage
clones independently with the existing exact Git trust fix, retains interrupted
attempts, and atomically publishes only a protected, clean, completed new release.
Occupied unknown/modified resources are refused. It does not switch current, install
packages, alter the preserved engine or open key contents. It reuses the existing
hash-pinned virtualenv because dependencies are unchanged. All source keys stay
root-owned0600. The active release remains3821952 at this point.

## Fresh backup, isolated proof and additive preparation

Keep the existing successful snapshot/receipt unchanged. Create a *new* uniquely
named encrypted snapshot using the still-active release and the existing backup
key. Never use a shell overwrite or delete a prior archive to retry.

```sh
rmc_archive="/var/backups/resmgrcheck/snapshot_$(date -u +%Y%m%dT%H%M%SZ).rmc"
sudo /opt/resmgrcheck/current/.venv/bin/python -B \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/backup.json manage.py backup_snapshot create \
  --archive "$rmc_archive" --key-file /etc/resmgrcheck/keys/backup-key
sudo /usr/bin/python3 -B web/ops/production/upgrade_private.py \
  --revision "$rmc_revision" --operation prepare --archive "$rmc_archive" --apply
```

Preparation binds the fresh root-owned600 archive/receipt by encrypted hash before
any DB mutation. It uses the new verifier to perform an actual isolated temporary
restore, requires authentication/hashes/evidence validation, UPDATE/DELETE rejection
on a synthetic audit row, rollback, preserved source identity and exact cleanup.
It records proof only after successful cleanup. This new snapshot proof qualifies
the upgrade recovery point; the previously successful production drill is retained.
Retry uses the *same* bound archive and saved proof, including after24hours; never
replace the bound archive or delete intent/proof records to bypass a failure.

Only reviewed additive control migrations0018–0020 and runner-grants.sql execute,
in one PostgreSQL transaction with an advisory lock. Missing0017, unknown/backwards
plans, inconsistent history, unexpected role flags/memberships/ownership or excess
permissions fail closed. Existing audit/user/project/run identities remain. No
runtime role owns a relation or gains DDL/audit rewrite. Static assets are collected
to a fresh hash-inventoried /var/lib/resmgrcheck/static/SHA tree with atomic no-replace
publication. Old static paths/configs are preserved. A failed collection retains its
attempt and does not switch current; retry verifies/reuses only completed trees.

## Activate privately and qualify

```sh
sudo /usr/bin/python3 -B web/ops/production/upgrade_private.py \
  --revision "$rmc_revision" --operation activate --apply
sudo systemctl reset-failed resmgrcheck-web.socket resmgrcheck-web.service
sudo systemctl start resmgrcheck-web.socket
sudo curl --fail --silent --show-error --max-time 10 \
  --unix-socket /run/resmgrcheck-web/application.sock \
  -H 'Host: qnx-resmgrcheck.gestionatech.de' -H 'X-Forwarded-Proto: https' \
  --write-out '\nHTTP %{http_code}\n' http://localhost/readyz/
readlink -f /opt/resmgrcheck/current
sudo systemctl show --property=ActiveState,SubState,Result,User,Group,MainPID,ExecStartPre,ExecStart \
  resmgrcheck-web.service
rmc_invocation=$(systemctl show --value --property=InvocationID resmgrcheck-web.service)
sudo journalctl --no-pager -o cat "_SYSTEMD_INVOCATION_ID=$rmc_invocation" \
  --grep='Validated systemd Unix listener|nonroot_process' -n 10
```

Activation rechecks live schema/effective grants/static hashes and all installation
records before an atomic pointer switch. No unit change or daemon-reload is needed.
Require the exact new revision, socket-triggered Gunicorn startup, current-invocation
nonroot runtime_check with every existing isolation result, and readyz HTTP200.
Follow PRIVATE_INSTALL.md's explicit-start qualification too. A listener or active
unit alone does not pass. Do not dump protected logs/configs or secret values.

The new static directory is staged for a future separately reviewed private/public
proxy test. Existing protected env STATIC_ROOT still names the old tree; this does
not serve static assets from Gunicorn and must not cause collectstatic into that
old tree. Future approved Nginx configuration must explicitly select the new static
SHA. This workflow does not edit or reload any Nginx site or expose a listener.
Actual intended-origin MFA/codes/browser/mobile/native/isolation acceptance is still
pending. Do not restart/enable executor/AI automatically: first review its unchanged
registry and runtime context. Never put customer SSH credentials on the server.

## Safe rollback and retries

With only these dedicated web/jobs/timers quiet again:

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service
sudo /usr/bin/python3 -B web/ops/production/upgrade_private.py \
  --revision "$rmc_revision" --operation rollback --apply
```

Rollback preserves all releases/static trees, DB/schema, keys, encrypted backups,
audit and deployment records. It runs no reverse migration, restores no DB over the
live one and deletes nothing. A live DB gate refuses the old application if *any*
runner/enrollment/nonce/job/chunk, customer-runner target, mailbox run or mailbox
build exists. Preserve those records and use a compatible forward repair instead;
revocation or deleting histories is not a rollback strategy. Review the gate result
before restarting the old socket and requiring its readiness/runtime again.

If preparation fails before activation, current remains old; preserve the bound
snapshot, partial attempts and protected diagnostics. Retry stage/prepare with the
same exact revision/archive after fixing the reviewed cause. Do not activate after
any failed proof. A pointer interruption can safely repeat activate; modified or
unknown resources are refused. The helper is deliberately limited to this initial
upgrade from3821952, not arbitrary future rolling deployments.

## Customer feature enablement remains a separate gate

The new signing credential is deliberately not created by this initial procedure.
Production machine endpoints remain404 while RUNNER_ENABLED is false. A subsequent
review must provision a new independent root-owned600 Ed25519 seed locally, delegate
it only to the web unit using LoadCredential=runner-key, retain all existing sandbox
lines, and qualify its strict ACL validator/runtime under resmgr-web. Never reuse
application/MFA/backup or unrelated provider keys. Local operator enrollment, separate
customer-host/TLS/authenticated jobs/tenant tests and customer-owned SDK/target proof
must pass before advertising onboarding. Existing executor isolation must independently
qualify bounded private ingestion. No such production/separate-host result is claimed.
