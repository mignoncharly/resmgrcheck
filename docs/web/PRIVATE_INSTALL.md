# Private production qualification handoff

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. Actual private release remains544f22c; corrected immutable
activation/public acceptance is pending. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

W021 current state (2026-11-09): immutable544f22c is active privately. The operator
confirms HTTP200, nonroot/isolation and encrypted isolated restore/audit proof.
[HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md) supersedes the historical multi-command
public handoffs below with one reviewed operator command that installs only the
ResMgrCheck HTTPS settings, validates/reloads, proves rollback and runs real HTTPS
browser acceptance. Customer runner/AI remain disabled and off-server DR deferred.
Actual privileged/public/native acceptance results must still be recorded.


W015 (2026-11-09) supersedes W014's pending observations below: the operator
activated3821952, obtained private HTTP200/nonroot runtime success and completed
the actual encrypted isolated restore with audit UPDATE/DELETE rejection. Preserve
the release, snapshot and receipt; no repeat recovery is required. Customer-runner
enrollment is new staging work, disabled by default. The old restore-only recovery
helper intentionally rejects this broader change. Do not bypass its scope guard.
No privileged runner deployment is ready yet: additive tables, least-privilege
grants and a separate signing credential need immutable migration/rollback review
and qualification. Existing keys, data, units and isolation remain unchanged.

Status (2026-11-08, W014): active immutable release is 59158ad. The production backup
service succeeded and preserved `/var/backups/resmgrcheck/snapshot_20261108T224711Z.rmc`,
but its isolated restore failed `backup_restored_audit_trigger_unproven`. The old
row-level UPDATE probe cannot fire on an empty table; that failure is reproduced
with a valid restored trigger/function. The correction is prepared/tested. The
protected production archive's actual audit count/trigger state still require the
operator inspection below, and real corrected production restore remains pending.
P8 is IN PROGRESS; no public deployment is authorized by this correction.

## Next operator action: immutable restore-verifier upgrade

Use the clean committed correction checkout. Do not patch current in place, edit
prior manifests/markers, rotate keys, regenerate/overwrite the snapshot or change
the live audit table/trigger. The new procedure accepts only the verified 59158ad
installation and a descendant commit changing the restore verifier/command/helper
plus tests/docs. It rejects schema/migration, grant, credential, unit, dependency,
web assets, engine or native changes. No service reload is needed: all units and
the working socket/credential configuration are unchanged.

```sh
cd /home/mignon/projects/resmgrcheck
git status --short
rmc_revision=$(git rev-parse HEAD)
python3 -B web/ops/production/recover_restore_drill.py --revision "$rmc_revision"
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service &&
sudo /usr/bin/python3 -B web/ops/production/recover_restore_drill.py \
  --revision "$rmc_revision" --apply
```

Stop on any failure. The helper verifies the original preparation, credential and
socket deployment records; clean original code/index and shared virtualenv; unchanged
web/socket/backup units with no overrides; source-key metadata without opening their
contents; and inactive dedicated web/worker/timer units. Unexpected activity causes
refusal, never automatic stopping of other jobs. The private database stays running.
It never reads backups or DB contents, runs migrations/restores or starts services.

An exclusive existing release lock and a protected exact-target RESTORE_RELEASE
intent govern independent `.restore-stage-SHA-random` clones. A verified protected
`.restore-release.json` and clean Git tree are published to a new commit directory
with atomic no-replace semantics; only current is switched. Original releases,
indices, packages, snapshots/receipts/keys, database/audit, config/static paths and
units are preserved. Interrupted attempts remain; retry the same SHA to validate/
reuse a completed release or stage a fresh attempt. Unknown or modified resources
are refused, never removed or permission-repaired. A different target needs separate
review, not edited records. This is a specific upgrade, not a general migration tool.

## Inspect the preserved encrypted snapshot without an audit mutation probe

Use the root operator profile (resmgr_owner/CREATEDB), not the SELECT-only backup
profile. Authentication precedes extraction, member hashes and canonical evidence
validation remain mandatory, and each command creates/restores/drops its own exact
new random `resmgrcheck_restore_*` database. It never restores over live data.

```sh
sudo /opt/resmgrcheck/current/.venv/bin/python -B \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/operator.json manage.py backup_snapshot inspect-restore \
  --archive /var/backups/resmgrcheck/snapshot_20261108T224711Z.rmc \
  --key-file /etc/resmgrcheck/keys/backup-key
```

The result reports only restored audit row count, trigger/function presence,
definition-match/enabled/replication-role facts and definition hashes. It never
prints archived audit rows, function source, dump contents or keys. An empty audit
table with valid metadata confirms the zero-row failure for this archive. Missing/
disabled/changed metadata identifies a different protection problem: stop and
investigate, rather than recreating/enabling a trigger to force the gate through.
Inspection intentionally returns `passed:false`, `diagnostic_only:true` and
`audit_behavior_tested:false`, even for correct metadata. Exit 0 means inspection
completed; metadata presence alone never qualifies append-only protection.

## Prove the restored audit guard, including an initially empty table

```sh
sudo /opt/resmgrcheck/current/.venv/bin/python -B \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/operator.json manage.py backup_snapshot restore-drill \
  --archive /var/backups/resmgrcheck/snapshot_20261108T224711Z.rmc \
  --key-file /etc/resmgrcheck/keys/backup-key
```

The verifier first requires the exact new DB connection, canonical enabled BEFORE
ROW UPDATE/DELETE trigger linked to the known PL/pgSQL append-only function, with
no WHEN/column filters or unexpected properties. It inserts a new synthetic UUID
row only in that isolated DB within a forced-rollback transaction, attempts a real
action change and deletion in separate savepoints, and requires exact SQLSTATE
P0001 plus the expected append-only exception for both. Permission errors or an
UPDATE affecting zero rows are not proof. It then rolls back the probe and verifies
original row count, probe absence and complete database identity. Existing restored
audit records are never selected as mutation targets. No live audit write occurs.

Require `passed:true`, `diagnostic_only:false`, `audit_behavior_tested:true`, both
`audit_update_denied`/`audit_delete_denied:true`, `audit_probe_rolled_back:true`, equal
audit counts before/after rollback, verified metadata, database identity and exact
temporary-DB cleanup. The encrypted archive hash must match the preserved snapshot.
A failed cleanup raises an error instead of returning success. Do not use FORCE,
broad session termination or guessed database deletion if cleanup fails; retain
the exact diagnostic and inspect only the created temporary DB locally.

Only after the real isolated restore succeeds, restart private web and recheck
its current-invocation runtime_check and Unix readiness using the qualification
procedure below. Do not expose it publicly or enable other unfinished gates.

```sh
sudo systemctl reset-failed resmgrcheck-web.socket resmgrcheck-web.service &&
sudo systemctl start resmgrcheck-web.socket resmgrcheck-web.service
```

If recovery requires rollback, keep web stopped and switch only to the preserved
59158ad code. This leaves all data/keys/snapshots/units unchanged, but restores the
known flawed audit-verification algorithm and does not qualify the restore gate:

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service &&
sudo /usr/bin/python3 -B web/ops/production/recover_restore_drill.py \
  --revision "$rmc_revision" --rollback --apply
```

The development tests used real encrypted pg_dump/pg_restore copies and transactions
in the private development cluster. They did not inspect the protected production
archive or run privileged deployment. Record the actual operator inspection/drill
JSON before advancing this P8 gate; other operational/HTTPS/UAT gates still apply.

## Historical socket correction (W013)

Status at W013: the credential correction works on immutable release
`d6513ba2ccaf13fa4c7491b5cac095d5ab572a16`; the operator reports actual runtime_check
success under resmgr-web and the expected role/credential/network denials. Gunicorn
then fails with EBADF and readiness times out (HTTP000). The duplicate FD consumption
is now reproduced/confirmed and corrected. Production activation/readiness of the
new release remain pending; P8 is IN PROGRESS and public deployment is withheld.

## Next external action: immutable socket-activation correction

Gunicorn26.2.0 combines integer `--bind fd://3` entries with the descriptors found
through systemd LISTEN_PID/LISTEN_FDS. With both paths identifying3, the list is
`[3,3]`: the first wrapper closes the original descriptor and the second raises
EBADF. A valid descriptor exists before Gunicorn executes; this is duplicate
consumption, not loss at Python startup. The correction removes only the explicit
bind argument from the web unit. Gunicorn's configuration disables its default
TCP bind and validates one live AF_UNIX listening stream at the exact private
socket path for this PID, preserving fd3 and LISTEN_* for automatic discovery.

Review the clean committed correction checkout and its read-only plan. Run the
root commands locally only; the agent has not deployed or restarted production:

```sh
cd /home/mignon/projects/resmgrcheck
git status --short
rmc_revision=$(git rev-parse HEAD)
python3 -B web/ops/production/recover_socket_activation.py --revision "$rmc_revision"
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service &&
sudo /usr/bin/python3 -B web/ops/production/recover_socket_activation.py \
  --revision "$rmc_revision" --apply &&
sudo systemctl daemon-reload &&
sudo systemctl reset-failed resmgrcheck-web.socket resmgrcheck-web.service
```

Stop on any nonzero result; keep web stopped on an incomplete apply. This procedure
accepts only the verified d6513ba credential release and its unchanged preparation/
credential records and shared original virtualenv. It verifies the clean original
release/manifests, source-key metadata without opening contents, known canonical
web/socket unit contents, no overrides and inactive dedicated web/worker/timer units.
Unexpected activity or changes cause refusal, never automatic cleanup or repair.

The new commit is staged in an independent `.socket-stage-SHA-random` clone, sealed
with a protected `.socket-release.json`, and published at a fresh release directory
with atomic no-replace semantics. The original releases and virtualenv remain.
It records a root-owned exact-target SOCKET_RELEASE.json intent, atomically updates
only the known web unit's ExecStart suffix, and switches current. The socket unit,
all other web unit directives, LoadCredential, user/group, sandbox/network policy,
settings/credential validator, configs/static path, dependencies, DB/schema/audit,
keys, QNX and SSH material are preserved. No service starts/reloads in the helper;
the explicit daemon-reload above is necessary for the changed web ExecStart.

Unit replacement and pointer replacement are individually atomic while web is
stopped. Repeating the same SHA/apply validates and completes either known partial
combination. Failed clone attempts are retained and retried in fresh directories;
unknown/modified releases, unit contents, overrides, intents or pointers are refused.
The original preparation marker and CREDENTIAL_RELEASE record are never edited.
An exclusive shared release lock prevents competing recovery commands. This is a
specific second private-install correction, not a general updater or power-loss
qualification. Do not invoke the earlier credential recovery helper against a
socket-corrected current pointer.

## Qualify both production activation paths

First explicitly start both dedicated units, then require private readiness:

```sh
sudo systemctl start resmgrcheck-web.socket resmgrcheck-web.service &&
sudo curl --fail --silent --show-error --max-time 10 \
  --unix-socket /run/resmgrcheck-web/application.sock \
  -H 'Host: qnx-resmgrcheck.gestionatech.de' -H 'X-Forwarded-Proto: https' \
  --write-out '\nHTTP %{http_code}\n' http://localhost/readyz/
```

Capture the exact current invocation's properties and safe startup facts:

```sh
readlink -f /opt/resmgrcheck/current
sudo systemctl show --property=ActiveState,SubState,Result,User,Group,MainPID,ExecStartPre,ExecStart \
  resmgrcheck-web.service
rmc_explicit_invocation=$(systemctl show --value --property=InvocationID resmgrcheck-web.service)
sudo journalctl --no-pager -o cat "_SYSTEMD_INVOCATION_ID=$rmc_explicit_invocation" \
  --grep='Validated systemd Unix listener|nonroot_process' -n 10
```

Require the new SHA, active/running resmgr-web service, successful runtime_check,
the validated fd3/count1 discovery marker, and readyz `{"status":"ready"}` HTTP200.
The identity, DB-role, private-credential, home/evidence and IP-socket denial checks
must all retain their expected values. Unit activity or a listener alone is not
readiness. A timeout, HTTP000/503, stale/missing invocation or process failure does
not pass. Keep unrelated logs/configs local; share only these metadata/results.

Then stop only web, start **only its socket**, and issue the same private request
to trigger service startup:

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service &&
sudo systemctl reset-failed resmgrcheck-web.socket resmgrcheck-web.service &&
sudo systemctl start resmgrcheck-web.socket &&
sudo curl --fail --silent --show-error --max-time 10 \
  --unix-socket /run/resmgrcheck-web/application.sock \
  -H 'Host: qnx-resmgrcheck.gestionatech.de' -H 'X-Forwarded-Proto: https' \
  --write-out '\nHTTP %{http_code}\n' http://localhost/readyz/
```

Repeat the property/journal capture for the new InvocationID (different from the
explicit-start attempt). Both modes must pass. The four unprivileged user-manager
tests used real Gunicorn/systemd/AF_UNIX and confirmed fd3 handoff and IP-socket
denial, but used a synthetic WSGI app and UID1000. They do not qualify production
UID982, real keys/DB, namespace/BPF containment or production readiness.

If diagnosis requires rollback, keep web stopped and use the same correction SHA:

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service &&
sudo /usr/bin/python3 -B web/ops/production/recover_socket_activation.py \
  --revision "$rmc_revision" --rollback --apply &&
sudo systemctl daemon-reload
```

Rollback restores the exact d6513ba pointer and old web unit, preserving all data
and both releases. That release has the **known socket integration failure**;
leave web stopped. No healthy rollback or production P8 pass is claimed. Resume
remaining P8/P9/P10 work only after independent corrected runtime/activation/HTTP200
and relevant isolation verification; later HTTPS/backup/restore/UAT gates still apply.

## Historical credential correction (W012)

Status at W012: the operator confirmed the credential incompatibility
inside the real ExecStartPre context. Both runtime files are root:root0440 regular
files with owner read, named UID982 read, owning group none, mask read, other none.
The old validator mistakes the ACL mask for an insecure group permission grant.
Source keys remain root:root0600; the temporary diagnostic was removed successfully
and the canonical unit is unchanged. The correction and immutable-release recovery
are prepared/tested; actual corrected production startup/isolation/readiness remain
pending. Public deployment is withheld. No SMTP is needed; AI is disabled.

## Next external action: activate the immutable credential correction

Use the committed correction checkout on `feature/production-web-ai`. Do not patch
`/opt/resmgrcheck/current`, overwrite the installed4ed4855 release, reset its
preparation marker or rerun prepare.py with a newer SHA. The narrowly scoped
`recover_credentials.py` procedure accepts only this original private installation
and a reviewed descendant commit whose runtime changes are confined to credential
validation and the related operation scripts. Dependencies, templates/assets,
models/migrations, database grants, unit files and engine must be unchanged.

The corrected validator keeps ordinary files private (`0400`/`0600`, trusted owner,
no access ACL, single regular inode, maximum4096 bytes). It adds an exact systemd
path: the expected credential ID under the role's fixed `/run/credentials/...`
directory, matching CREDENTIALS_DIRECTORY, nonroot effective UID matching the
dedicated account, root:root0440 file and precisely the observed read-only ACL for
that UID. The root-owned0550 store must also grant only that UID read/search via
its matching ACL. All path components are opened without following symlinks.
Ordinary0440 files, unrelated ACL principals, writes, other access, unexpected
ownership/entries, hardlinks, invalid ACL/UTF-8/NUL and oversized input fail closed.
The original source keys, LoadCredential, nonroot service and runtime_check stay intact.

Review the read-only plan, then run the explicit root action locally:
Run reset-failed/start only after the apply command exits0. If apply fails, keep
web stopped, preserve the diagnostic/staging state and inspect the failure locally.

```sh
cd /home/mignon/projects/resmgrcheck
git status --short                       # verify the reviewed checkout is clean
rmc_revision=$(git rev-parse HEAD)         # full committed correction SHA
python3 -B web/ops/production/recover_credentials.py --revision "$rmc_revision"
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service
sudo /usr/bin/python3 -B web/ops/production/recover_credentials.py \
  --revision "$rmc_revision" --apply
sudo systemctl reset-failed resmgrcheck-web.service
sudo systemctl start resmgrcheck-web.socket resmgrcheck-web.service
```

The helper verifies the original marker/clone receipt and clean source, root-owned
source-key metadata without opening their contents, unchanged canonical web unit,
removed diagnostics/overrides and inactive dedicated web/executor/AI/backup/status
units/timers. It refuses unexpected activity instead of stopping other units. The
dedicated database stays running. No daemon-reload is needed: no unit changes.

It reserves an exact root-owned `CREDENTIAL_RELEASE.json` intent, stages an independent
Git clone in a fresh `.credential-stage-SHA-random` directory, validates the exact
commit/clean tree and a protected `.credential-release.json` completion manifest,
then publishes `/opt/resmgrcheck/releases/SHA` and atomically switches `current`.
Linux no-replace publication preserves even an empty destination created during
publication; an occupied release directory is never replaced.
The release reuses the unchanged original `.venv` through an exact root-owned
symlink. Keep that original release: the correction depends on its pinned packages.
Existing static-root configuration still selects the unchanged original static
assets. No pip install, migration, key rotation, database/config/grant/unit write,
service start/reload or QNX contact occurs in the Python helper.

An exclusive release lock serializes operators. Retry the **same command/SHA** after
an interruption. Completed releases are validated/reused; failed staging attempts
are retained and a retry uses a fresh attempt. Unknown occupied destinations,
modified tracked files, unexpected ignored/untracked content, mismatched manifests,
pointer/marker changes or a different recorded release stop recovery. Nothing
unknown is removed or permission-repaired. Repeated retained attempts can consume
disk; staging requires1GiB spare and does not delete earlier evidence. This is a
single-purpose initial-install correction, not a general cross-version updater or
power-loss/disaster-recovery qualification.

## Verify the actual corrected private runtime before advancing

After a successful start, inspect only current-invocation metadata and readiness:

```sh
readlink -f /opt/resmgrcheck/current
sudo systemctl show --property=ActiveState,SubState,Result,User,Group,ExecStartPre,MainPID \
  resmgrcheck-web.service
rmc_invocation=$(systemctl show --value --property=InvocationID resmgrcheck-web.service)
sudo journalctl --no-pager -o cat "_SYSTEMD_INVOCATION_ID=$rmc_invocation" \
  --grep='"nonroot_process"' -n 1
sudo curl --fail --silent --show-error --max-time 10 \
  --unix-socket /run/resmgrcheck-web/application.sock \
  -H 'Host: qnx-resmgrcheck.gestionatech.de' -H 'X-Forwarded-Proto: https' \
  --write-out '\nHTTP %{http_code}\n' http://localhost/readyz/
```

Require the exact new SHA pointer, active/running service with nonzero MainPID,
User/Group=resmgr-web, successful ExecStartPre (exit0), a current-invocation
runtime_check JSON that passes every original isolation/role condition, and
`{"status":"ready"}` with HTTP200 from Gunicorn. Missing output or an old invocation
does not pass. These observations confirm both consumers loaded the real credentials
without printing them. Share only the unit properties, runtime_check JSON and
readiness response; inspect any other failure locally without dumping keys/configs.
Fresh-subprocess compatibility tests simulate UID982/ACLs and DB/sandbox facts;
they do not establish actual OS isolation. No actual corrected service qualification
has yet been performed by the agent or reported by the operator.

If startup fails, keep the dedicated web socket/service stopped and preserve the
new release and all data for diagnosis. A reviewed pointer-only rollback is:

```sh
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service
sudo /usr/bin/python3 -B web/ops/production/recover_credentials.py \
  --revision "$rmc_revision" --rollback --apply
```

Rollback preserves both releases, keys, database/audit, configurations and units.
It returns to the original **known-failing credential validator**; leave web stopped.
It makes no healthy-runtime or database-restore claim. Keep the recorded intent;
the same correction can be reapplied after review. A different release needs a
separately reviewed procedure, not an edited/removed marker or receipt.

P8 stays IN PROGRESS until independent private-runtime verification and its remaining
HTTPS, backup/restore/off-host custody, quota/retention and rollback gates pass.
Only then proceed to P9 independent acceptance and P10 public deployment. Nginx,
other PostgreSQL instances, QNX guests, SSH material and original evidence are untouched.

## Historical temporary diagnostic (W011, completed by operator)

The instructions below record the earlier diagnostic stage. The operator has
captured the metadata and removed it; do not reinstall it for normal recovery.

The source keys must remain root:root `0600`. Do not change their permissions,
values, ownership, LoadCredential directives or the service user. Inspection of
`/run/credentials/resmgrcheck-web.service` between attempts cannot determine the
files' in-unit metadata: the directory follows the unit lifecycle and sandbox.

The likely incompatibility is systemd255's root-owned file plus a named service-UID
read ACL. Its ACL mask appears as `0440` to stat even when the owning group has no
access; Django's current `mode & 077` rejects that. Systemd also supports ownership
fallback with `0400`. **The real production UID/GID/mode/ACL has not been captured,
so the root cause is not yet confirmed and the validator correction is withheld.**

The standalone `credential_diagnostic.py` below has no Django dependency. Its
temporary runtime drop-in inserts a metadata observer before the original
`manage.py runtime_check`, and sets `Restart=no` for one attempt. All service
identity, LoadCredential, environment, sandbox, ExecStart and runtime_check
directives remain effective. The observer uses stat/fgetxattr only: it never reads,
hashes or prints credential contents. Its JSON contains only credential identifiers,
file UID/GID/mode/type and access ACL metadata (numeric permissions: read=4,
write=2, execute/search=1), or a fixed metadata error with errno.

Run these commands **locally as the operator**, from the committed diagnostic
checkout. No privileged commands were run by the agent. The first Python command
is a plan. Stop only the dedicated web socket/service; leave PostgreSQL, Nginx,
QNX and other VPS applications running.

```sh
cd /home/mignon/projects/resmgrcheck
python3 web/ops/production/credential_diagnostic.py
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service
sudo /usr/bin/python3 web/ops/production/credential_diagnostic.py --install
sudo systemctl daemon-reload
sudo systemctl reset-failed resmgrcheck-web.service
sudo systemctl start resmgrcheck-web.socket resmgrcheck-web.service
```

The final start may fail at the unchanged runtime_check. **Continue with capture
and cleanup even if it returns nonzero.** Capture only the observer's JSON:

```sh
sudo journalctl -u resmgrcheck-web.service -b --no-pager -o cat \
  --grep='resmgrcheck-credential-metadata' -n 1
sudo systemctl stop resmgrcheck-web.socket resmgrcheck-web.service
sudo /usr/bin/python3 web/ops/production/credential_diagnostic.py --remove
sudo systemctl daemon-reload
```

Share only that JSON line. Keep unrelated logs/configuration and secrets local.
The temporary files are `/run/resmgrcheck-credential-diagnostic.py` and
`/run/systemd/system/resmgrcheck-web.service.d/50-resmgrcheck-credential-diagnostic.conf`.
Install/remove refuses unknown occupied files, links, existing overrides, changed
canonical unit contents and active web units. It is repeatable after its own partial
installation, never overwrites the canonical web unit, and removes only its exact
known files; an empty override directory may remain. No service is started/reloaded
by the Python script. Source keys, database, release/current pointer, preparation
marker and other units are untouched. The temporary override also disappears on
reboot; do not reboot as a diagnostic step.

Leave the failed web service/socket stopped after cleanup until the metadata is
reviewed and the smallest correction is committed. No application upgrade,
cross-revision prepare run, database recreation, key regeneration or preparation
marker edit is needed to capture metadata. **Do not rerun prepare.py with a newer
SHA over this partial installation.** After confirmation, a separately reviewed
correction must preserve the existing keys/config/database and qualify the actual
systemd runtime_check and Unix-socket readiness before any production-ready claim.

## Historical clone recovery (W010)

The development process is UID1000. `sudo -n true` still returns "a password is
required"; filesystem Full Access does not grant Linux root. Do not send a password
or protected configuration. A local administrator must review and execute the
dedicated private preparation command. For this failed installation, use the corrected
script from the committed `feature/production-web-ai` checkout, retaining the original
application revision below. The installer driver and the application revision are
deliberately different: changing the requested revision to the correction's HEAD
would conflict with the existing protected preparation marker. Do not edit that
marker or delete partially created resources to bypass the check.

```sh
cd /home/mignon/projects/resmgrcheck
revision=4ed4855f7633176baea06f2be53154630a9d4d1f
python3 web/ops/production/prepare.py --revision "$revision"
# Review prepare.py, its unit files and database-grants.sql before this root action:
sudo /usr/bin/python3 web/ops/production/prepare.py --revision "$revision" --apply
```

The first Python command is a read-only resource plan, not a privileged resource
validation. The root command verifies the protected marker and known early-install
layout before resuming this same revision. For a genuinely fresh host only, select
an exact reviewed application SHA instead. The root command refuses occupied
unmarked resources/accounts/groups, creates only dedicated `resmgr-*` identities,
`/etc/resmgrcheck`, `/opt/resmgrcheck`, `/var/lib/resmgrcheck`,
`/var/backups/resmgrcheck` and named `resmgrcheck-*` units. It checks spare memory/
disk, clones exact immutable source commits without hardlinks, installs only the
hash-pinned wheels, creates a separate socket-only PostgreSQL16 cluster and
nonowner runtime roles, migrates a new empty database and collects public static
assets. Existing staging data/evidence is preserved separately, not seeded as
production user activity. Existing app/MFA/backup keys are never replaced.

Only the new private PostgreSQL service and Unix-socket web service start. Nothing
listens publicly; no Nginx/DNS/TLS/firewall configuration is changed. Executor/AI
and timers are not started/enabled. The script does not reinstall QNX, source the
SDK, generate SSH credentials or modify the guest. Preparation is not an upgrade
tool: a different existing release is refused. After a partial failure, inspect
`/etc/resmgrcheck/prepare-error.log` locally; preserve resources/evidence, fix the
precise issue and resume the same reviewed revision. Never dump that log or configs
into chat. The reported root invocation failed; successful root preparation and
service isolation remain unqualified. This correction has not been applied as root.

## Clone failure and partial-install recovery

Git's source worktree trust is insufficient for this root-run clone. The local
transport's `upload-pack` checks `/home/mignon/projects/resmgrcheck/.git` separately,
and a top-level `git -c safe.directory=... clone` does not supply that child with
the exception. The corrected driver uses `--no-local` and an explicit, shell-quoted
`upload-pack` command with `safe.directory` set to exactly that source metadata
directory. Clone itself trusts only the exact source worktree. Each command resets
inherited safe-directory entries first; no global Git configuration is written,
no wildcard is added and no ownership check is disabled. The transport creates
independent objects without hardlinks. Checkout still selects the exact requested
commit, even when source HEAD is newer.

Read-only inspection found the dedicated accounts/groups, protected log and marker,
role/private/evidence/state directories and empty release parent already present.
The application release, its Git metadata, engine, database, static tree and current
pointer are absent. All nine dedicated units are absent/inactive. The development
user could not read the log/marker or list protected directories: `sudo -n` still
requires local authentication. The operator supplied the dubious-ownership diagnosis;
the exact protected log content was not independently read. Inspect it locally before
retrying; do not send secrets or the raw log. W010 records the precise observed scope.

On retry, existing directories must have the expected owner/group/mode; the driver
does not repair an unknown directory by changing its ownership/permissions. Early
recovery refuses unexpected entries, links and unexpected units/socket directories.
The root-run checks must confirm the marker and protected directories that the
development user could not inspect. Unknown resources remain untouched.

Each completed new clone gets a root-owned `0600` sibling completion receipt.
Subsequent attempts require that receipt, matching source/revision, clean tracked
files and expected ownership. An occupied destination without a receipt (including
an interrupted clone/checkout), mismatched receipt, missing completed clone or
modified tracked file stops recovery. Preserve it for separately reviewed local
inspection; the driver never deletes/replaces it or automatically adopts it.
The observed failure left no destination, so it needs no clone cleanup. These checks
qualify recovery of this early failure in disposable tests; they do not claim general
recovery from every interrupted database/migration stage.

## Verify the private runtime

Check only the dedicated units, not other VPS applications:

```sh
sudo systemctl status resmgrcheck-db.service resmgrcheck-web.socket resmgrcheck-web.service
sudo journalctl -u resmgrcheck-web.service -n 40 --no-pager
sudo curl --fail --unix-socket /run/resmgrcheck-web/application.sock \
  -H 'Host: qnx-resmgrcheck.gestionatech.de' -H 'X-Forwarded-Proto: https' \
  http://localhost/readyz/
```

`runtime_check` runs before each web/executor/AI service starts. It requires a
nonroot process, nonprivileged/nonowner database role without privileged role
membership/schema creation, and inaccessible unrelated private credentials. This
must pass under the actual unit identities; staging superuser results cannot
substitute for it. Production web has Unix sockets only and no registry/provider
config. Executor has only the approved loopback network and private route; AI has
no QNX route/SDK access. systemd namespace/BPF restrictions still require actual
root-run validation on this host.

The public vhost examples are intentionally not installed. Their isolated Nginx
syntax check used high loopback ports and a disposable test certificate. That is
not trusted TLS or public HTTPS verification. Complete private TLS/browser tests,
certificate/domain checks, P8 and independent P9 UAT before enabling public access.
Never weaken production cookie/origin checks to make a private HTTP test pass.

## Provision the administrator and target locally

```sh
sudo /opt/resmgrcheck/current/.venv/bin/python \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/operator.json manage.py \
  provision_administrator --username first-admin
```

The password is entered through getpass, never argv/chat. Enroll administrator
TOTP over the qualified private HTTPS route before privileged browser access.
Only an explicitly requested `--platform-owner` has cross-organization authority.
Protected recovery uses the same wrapper with `recover_administrator --username`
and explicit `--reset-mfa` only when necessary. There is no email/SMTP recovery.

Follow [CUSTOMER_TARGETS.md](CUSTOMER_TARGETS.md) for organization/project and exact
operator target/build approval. Reuse the existing working QNX route, pinned host
keys and deployed manifests; do not create new QNX credentials. Production must
use dedicated private copies of only that approved route/key/known-host material
under `/etc/resmgrcheck/executor` with executor ownership/private permissions.
Do not give the web/AI identities access to the development user's home or SDK.
The registry uses `/opt/resmgrcheck/engine` and exact manifest/config paths; its
`.local/state` is bound to `/var/lib/resmgrcheck/engine-state`. No QNX build is
triggered by HTTP. After actual inventory/compatibility verification, issue a
scoped live code, start only `resmgrcheck-executor.service`, and qualify both
fixtures plus same-ID loss recovery/source-corrected replay under the real role.
AI stays disabled unless separately configured/consented/qualified.

## Backup, retention and monitoring

```sh
# The operator configuration has CREATEDB only for an exact isolated restore drill.
# The nightly backup uses the separate SELECT-only resmgr_backup database role.
sudo systemctl start resmgrcheck-backup.service
sudo /opt/resmgrcheck/current/.venv/bin/python \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/operator.json manage.py backup_snapshot restore-drill \
  --archive /var/backups/resmgrcheck/EXACT_SNAPSHOT.rmc \
  --key-file /etc/resmgrcheck/keys/backup-key
sudo /opt/resmgrcheck/current/.venv/bin/python \
  /opt/resmgrcheck/current/web/ops/production/runtime.py \
  --config /etc/resmgrcheck/backup.json manage.py operations_status
```

The archive is streamed with authenticated AES-256-GCM, a fresh nonce and a separate
32-byte key; its PostgreSQL snapshot/evidence inventory is consistent with retention
excluded by an advisory lock. Restore authenticates first, rejects links/traversal/
unknown members, creates an exact new temporary database, verifies identities,
artifact hashes/canonical evidence and append-only audit, then drops only that
database. It never restores over live data or contacts QNX. The default4GiB/100000-file
bound fails explicitly rather than omitting required files. Backup receipts do not
claim a successful restore. External application/MFA encryption-key files, provider/SSH credentials, SDK and
binaries are outside the data archive. The encrypted database itself contains
password hashes, encrypted MFA data, code verifiers and sessions; treat it as sensitive. Key custody and an independently protected off-host encrypted
copy/restore must be qualified before production acceptance. Never delete the only
verified backup; no off-host location is configured by this script.

The root snapshot/status wrappers are bounded, have no capabilities/home/IP-network/
QNX access and use a SELECT-only DB role; root is retained for protected backup-key
custody and local peer authentication. Other services run as dedicated nonroot
users. No blanket runtime schema ownership/DDL/audit rewrite is granted. The current
default is not a claim that this complete containment has already run on this host.

After actual restore/key-custody and operational tests, enable only the dedicated
backup/status timers. Status checks report queue ages, expired leases, quarantine,
free disk, backup-receipt age and unit activity. They fail on missing/stale facts;
they never equate receipt freshness/unit activity with restored data or native
service health. Monitor their journal/failed-unit state and establish the operator's
external alert/uptime route. No SMTP dependency or automatic provider message exists.
Evidence retention remains explicit `manage.py maintain` dry run / `--apply`, under
the executor identity and validated exact tree. Never use broad target cleanup.

## Rollback and remaining gates

For initial private preparation, executor/AI have not started and no native cleanup
is claimed. Rollback stops only `resmgrcheck-web.service`, its socket and the new
database after preserving a verified backup; leave evidence/configuration for
investigation. Do not stop another PostgreSQL/Nginx/QEMU service or remove unknown
resources. Once native execution is enabled, drain/withhold new work and inspect
exact owned run IDs/cleanup before stopping workers. Unknown target state requires
quarantine and same-ID recovery, not a new launch or guessed PID kill.

A later release change needs an explicitly reviewed migration/restore and atomic
release/static-pointer procedure. No automated cross-version upgrade/downgrade or
completed production rollback drill is claimed by prepare.py. P8 must qualify the
actual service roles, HTTPS/cookies/CSRF, backup/restore/off-host key custody, quotas,
retention and rollback. P9 must then run clean-release/native/browser acceptance
and independent operator UAT. Only after these gates may P10 install the dedicated
reviewed vhost, obtain/verify trusted TLS, reload Nginx after `nginx -t`, and verify
the public URL and real operations externally. No public deployment has occurred.

Implementation references: [PostgreSQL synchronized dump snapshots](https://www.postgresql.org/docs/16/app-pgdump.html),
[systemd containment](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html),
[Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## W016 — staged runner job and evidence route (2026-11-09)

W016 adds additive migrations0018/0019 and narrow runner-table grants. A real development migration roundtrip preserved existing audit rows and restored a pre-runner-schema encrypted archive. New snapshots account for the complete runner schema; partial schemas fail closed. Production rollback must preserve additive tables/customer records, not reverse migrations after enrollment, and keep executors stopped while old code lacks customer routing guards. No broad production activation command is ready: actual new-runner QNX/browser, separate-host and immutable upgrade/rollback qualification remain. Keep3821952 and its verified backup/keys intact; do not use the old restore-only upgrade helper for this broader scope.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 current qualification

The active private release is still3821952. Four actual QNX timeout cases completed
through the staged outbound route, including a real source-corrected mailbox replay
and exact-ID upload reconnection. This used a runner process on the same VPS, not
a separate customer machine or root production units. Automated browser MFA/code/
comparison/download/mobile/revocation checks passed in a recorded-only continuation;
the original driver's later CA error remains visible. Do not repeat the successful
production restore or native runs merely to repair unrelated test presentation.
The expanded release still needs a reviewed additive immutable upgrade and actual
private runtime acceptance before any public deployment. No privileged command has
been run automatically and the original keys/database/snapshot are unchanged.

## W019 operator-only expanded private upgrade

[PRIVATE_UPGRADE.md](PRIVATE_UPGRADE.md) provides exact stage, fresh encrypted backup,
isolated restore proof, atomic additive preparation, private activation and guarded
rollback commands from3821952. It preserves keys/units/configs/engine and keeps runner
endpoints/AI disabled. No privileged deployment was performed by the agent.

## W020 customer-local SSH trust binding (2026-11-09)

The runner now binds effective ssh -G configuration and bounded public known-host/
revocation-file hashes into its local route fingerprint. It refuses writable files,
links, unexpected owners/types, unpinned/dynamic trust, command-dependent Match/
Include configs, multiplexing and forwarding. Private key contents are not part
of this inventory and public pin/config contents never leave the customer. Use a
dedicated stable Host configuration and public pin files without group/other write.
A changed trust root cannot retain an old runner binding or obtain a launch grant.
Existing staged bindings are deliberately not rewritten; retain their journals and
evidence, revoke the old target and enroll/approve a new identity when adopting
this stronger binding. Production machine endpoints remain disabled.

Seven direct local tests passed in0.856s;48 affected signed TLS/enrollment/job/work/
trust regressions passed in11.734s. Real discovery reached the existing approved
QNX VM, verified compatibility/owned transfer and all three compiled adapters using
a new dedicated600 public-pin copy. The inherited known_hosts file was0664 and
correctly refused; original SSH configuration/pins were preserved unchanged. This
new route is not centrally enrolled/approved and no native lifecycle was repeated.
The four W018 runs retain their original route/source scope; do not relabel them
as executions after W020 hardening. Discovery is not lifecycle/cleanup qualification.
See evidence/runner-trust for results. Separate customer host, actual new private
release/isolation/rollback, public TLS/HTTPS and independent acceptance remain.

## W022 legacy own-log permissions and failed-driver resumption

The first operator-run f8a6009 workflow stopped at own_log_protection before HTTPS
installation and retained/restored the original configuration. Metadata-only
inspection confirms access.log root:root0640 and error.log root:root0644, both
regular single-link files with ordinary ACLs. No log contents were inspected.

The corrected helper opens only the two dedicated names with O_NOFOLLOW, validates
type/owner/trusted group/link count/ACL and reduces eligible modes by intersection
with0640. It never reads/truncates/chowns their data or broadens0600. Unknown links,
named ACLs, ownership, groups or world-write are refused. Tightened log protection
persists across config rollback; it never restores public-read logging permissions.
All unrelated logs and original secrets stay unchanged.

Only the specifically recorded rolled-back f8a6009 driver may transition to its
reviewed descendant with the same app/candidate hashes and exact original files
restored. Original backups stay unchanged and a protected old-driver history copy
is retained. A verified or concurrently edited deployment cannot be adopted by
this recovery. Eighteen focused regressions pass; see evidence/https-log-recovery.
The corrected privileged operation/public acceptance is pending the operator's
same single workflow command with the new driver SHA. No marker deletion, manual
chmod or extra diagnostic commands are required. P8–P10 do not advance yet.

## W023 private redirect cache policy and reviewed recovery

The e1ef88c operator run reported private_response_cacheable and successful own
rollback. Keep immutable application544f22c, keys, database and private service.
W023 corrects the HTTPS boundary to no-store for all dynamic responses and safely
transitions the known rolled-back driver using its committed payload hashes and
original backups. No manual marker deletion, log chmod or release replacement is
needed. Run the single reviewed command in HTTPS_DEPLOYMENT.md with the newly
committed driver SHA. Operator sudo is required for root-owned configuration and
Nginx reload; the agent must not execute privileged deployment automatically.
P8 remains IN_PROGRESS until actual production qualification succeeds.

## W024 graceful reload and strict rollback verification

The8000144 attempt completed its Certbot dry run but its immediate rollback
verification raced signal-based Nginx reload. Read-only inspection confirms the
HTTP-only originals are restored and private readiness remains200 on544f22c.
W024 adds bounded strict HTTP404/ACME verification after exact file/mode/link checks
and verified-TLS retries on reactivation. The known failed record can resume with
the corrected committed driver, retaining backups/history and completed same-cert
renewal proof. Do not patch /opt/resmgrcheck/current, replace credentials, delete
state or repeat the8000144 command. Use the one reviewed command with the new
full driver revision in HTTPS_DEPLOYMENT.md. No privileged deployment has been
executed by the agent; actual production acceptance is still pending.

## W025 Unix proxy identity and immutable authentication recovery

Do not repeat cf15209 against544f22c. Rollback is working; browser login403 comes
from allauth's missing Unix transport peer identity. W025 adds production-only
trust of Nginx's overwritten X-Real-IP and needs a new immutable application release.
The single recover_https_auth.py command in HTTPS_DEPLOYMENT.md stages that new
release, binds a fresh encrypted backup/isolated restore, restarts only dedicated
web/socket around an atomic pointer switch, creates/validates new static assets
without migration or grants, and requires private runtime/readiness before HTTPS.
It preserves source keys/configs/old release/DB/audits/evidence/native approvals.
Known cf15209 HTTPS state/history is retained and explicitly rebound after exact
old hashes/original restoration are proven. Same-cert renewal proof is reused;
rollback is requalified for the new alias. Failures restore the old private release
only after verified own HTTP restoration; unknown edits require review. Retry the
same reviewed SHAs after interruption; never delete state or unknown resources.
Actual new private/HTTPS qualification remains pending operator execution.

The committed authentication application is325f367c803b44e2f5ac5f4bb3264a7abfb7f08f.
Its immutable recovery plan passed unprivileged review. Actual current remains544f22c;
use the reviewed driver SHA from the handoff with this application revision.

## W026 password-only administrators and preserved recovery state

Use the current password-only application/driver SHAs in HTTPS_DEPLOYMENT.md, not
the old325f367/e6890b0 command. Its previous preparation failed release inventory
before backup/staging, independently of MFA. The new helper preserves the exact
prepared journal in history, validates original tracked files and any retained
cache against committed source, and refuses unknown resources. Existing secrets,
MFA authenticators, DB/audit/evidence and original544 directory remain intact.

The single reviewed root command stages a new immutable directory/static tree,
creates/binds an encrypted snapshot and isolated restore proof, switches only the
private web/socket, verifies nonroot runtime/readiness and then runs strict HTTPS/
rollback/password/code acceptance. It does not migrate schema, change units/grants,
create QNX routes, enable customer endpoints/AI, patch current in place or reset
protected state. Same-command retry and --rollback retain all records/releases.
Exact protected caches and actual new service/public acceptance remain operator
gates; unprivileged test success does not complete P8.

The committed password-only application is3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58.
Its unprivileged immutable recovery plan passed. Actual production is still544f22c;
use the reviewed driver SHA from the handoff. No privileged deployment ran by the agent.
