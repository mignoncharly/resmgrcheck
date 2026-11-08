# Private production qualification handoff

Status (2026-11-08, W011): the clone failure has been passed by an operator retry.
The private web socket is active but the web service fails during ExecStartPre with
`RMC_WEB_SECRET_KEY credential file permissions/type invalid`. No successful runtime
isolation or readiness is claimed. Public deployment remains withheld. W007/W009
record access/staging gates and W010 records the earlier clone correction. No SMTP
is needed; AI is optional and disabled.

## Next external action: temporary in-unit credential metadata capture

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
