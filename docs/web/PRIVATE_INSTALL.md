# Private production qualification handoff

Status: preparation code, not an executed production installation. Public deployment
remains withheld. The revised access gate passed W007; W009 records staging hardening
and the remaining root/UAT work. No SMTP is needed; AI is optional and disabled.

## Next external action

The development process is UID1000. `sudo -n true` still returns "a password is
required"; filesystem Full Access does not grant Linux root. Do not send a password
or protected configuration. A local administrator must review and execute the
dedicated private preparation command. From the clean implementation branch:

```sh
cd /home/mignon/projects/resmgrcheck
revision=$(git rev-parse HEAD)
python3 web/ops/production/prepare.py --revision "$revision"
# Review prepare.py, its unit files and database-grants.sql before this root action:
sudo /usr/bin/python3 web/ops/production/prepare.py --revision "$revision" --apply
```

The first command is a read-only resource plan. The root command refuses occupied
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
into chat. A root invocation has not yet been executed or qualified.

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
