# Operations record

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. W028: immutable application `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`
is active. Production password/code/browser acceptance passed; an independent
external public fetch returned HTTPS 200. W030: executor registry provisioning and
the actual service-context probe passed in the operator workflow. Native acceptance
passed root plan selection, then stopped at native form confirmation because the
web role lacked dispatch-mutex permissions. W031 corrects this without web deployment.
Actual native and independent authenticated acceptance remain pending.
P8 is IN PROGRESS. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

W021 historical state (2026-11-09; superseded by W028): immutable544f22c is active privately. The operator
confirms HTTP200, nonroot/isolation and encrypted isolated restore/audit proof.
[HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md) supersedes the historical multi-command
public handoffs below with one reviewed operator command that installs only the
ResMgrCheck HTTPS settings, validates/reloads, proves rollback and runs real HTTPS
browser acceptance. Customer runner/AI remain disabled and off-server DR deferred.
Actual privileged/public/native acceptance results must still be recorded.


Private production runs at3821952 (W015): private HTTP200/nonroot runtime/actual
encrypted isolated restore are operator-confirmed. Public HTTPS, customer-runner
and independent acceptance remain unqualified. Maintain separate liveness, database readiness,
worker heartbeat, queue backlog, target quarantine, disk and backup-age signals.
Unknown target status is not health; restarting a fixture does not establish the
health of an original instance. Native cleanup and host job cancellation differ.

Staged outbound enrollment is disabled in production. An MFA project administrator
issues a600s credential for one new target, then separately approves its exact
public key/inventory. Heartbeats every30s become disconnected after90s. Changed
inventory/route quarantines; revoked devices require a new identity. Connection is
not lifecycle qualification. SSH keys and legally licensed QNX configuration stay
with the customer. See CUSTOMER_RUNNER.md. Do not repeat successful restore merely
for documentation. Off-server disaster-recovery automation is deferred, not passed:
loss of this server and local archive/key custody may prevent recovery.

The existing QNX guest has a small filesystem: P0 observed 415 free file entries
and 2992 available 4096-byte blocks. Before new native qualification, budget cases
and preserve evidence. Never remove unknown histories, deployment/start guards or
signal PIDs from persisted status. Only the existing qualified ownership/reaping
path may claim process cleanup.

Secrets remain in private runtime configuration and systemd credentials. Log only
safe event IDs and error classes. Do not print environment files or authentication.
Back up PostgreSQL plus sealed evidence and encryption-key custody separately;
restore drills go to an isolated resource, never over live or unrelated databases.

No YouTube changes or Devpost submission are authorized in this task.

Local evidence maintenance uses `manage.py maintain` (dry run) or the explicit
`manage.py maintain --apply` operator/timer invocation. It is bounded to20 eligible
runs per invocation, validates the exact owned tree before deletion, and never
contacts QNX. Holds, active replay dependencies, unknown files, ownership,
incomplete integrity or native cleanup prevent removal. A partial local purge is
marked unavailable and audited; metadata and artifact hashes remain. Organization
retention is7–3650 days/default30. The superseded public account deletion task is
removed; historical identity/request rows are archival provenance. Separate backup
retention/key custody remains a production requirement. No native history was
deleted during the access-model migration.

An encrypted private staging checkpoint/restore was also exercised during P6
preservation. It restored into an exact new temporary database on the task-owned
socket-only cluster, verified140 artifact hashes/eight collected execution records
and the restored append-only audit trigger, then removed only that temporary DB.
Seven records contain actual QNX cases; one is the no-native-launch failed transfer.
The encrypted checkpoint/key and full receipt remain under ignored .local/web;
the original database and evidence were preserved. This is not the P8 production
backup role/off-host/key-custody qualification. MFA encryption-key custody remains
separate from the data archive. No private backup or key is published.

`manage.py seal_evidence --run-id WEB_UUID` verifies one completed collection and
adds a v2 inventory for earlier collection history. Existing v1 inventories and
native bundles remain unchanged. It cannot launch or collect QNX work. Never use
this to overwrite a changed artifact; a conflict requires investigation.

## Administrator provisioning and recovery

There is no public administrator signup, email verification/reset, invitation or
SMTP configuration. Regular developers/testers have no password accounts. See
[ACCESS_MODEL.md](ACCESS_MODEL.md) for the approved replacement decision.

In this task-owned private staging environment, run from the repository root:

```sh
.local/web/venv/bin/python web/ops/staging.py manage.py provision_administrator --username first-admin
```

The command prompts twice without echo, validates the password and writes an
Argon2 hash. Never put a password in argv, shell history, chat or source. An
automation-only `--password-file /protected/file` accepts an owned0600 regular
file, refuses symlinks and bounds its size. Remove that temporary file securely
under the operator's storage policy. Do not replace existing application/MFA keys.

For an additional scoped administrator, supply `--organization ORGANIZATION_UUID`
(repeatable) and optionally `--role owner`; default role is admin. This does not
create organizations or grant global access. The first administrator can create
their organization after login. `--platform-owner` is an explicit local elevation
with cross-organization powers; avoid it for routine scoped administration.

Open `/administrator/login/` and enter the local username/password. MFA is deferred;
no enrollment is required for this release. Password changes and "revoke all sessions"
retain password confirmation; privileged workflows request recent password
reauthentication when stale. Administrators can inspect/revoke browser sessions.
A lost password requires the protected local operator procedure:

```sh
.local/web/venv/bin/python web/ops/staging.py manage.py recover_administrator --username first-admin
# Deferred MFA records and encryption keys must remain intact.
```

Recovery changes the password, increments the session version, revokes existing
sessions and appends an audit event. Deferred MFA records remain intact; --reset-mfa
is refused in this release. Production commands require
the root operator and the dedicated production configuration/venv, not this staging
launcher. The development exception also checks the owned checkout and exact
private socket, port and staging/test database name; changing the environment
label cannot authorize production recovery. Production paths/service provisioning
are still subject to the P8 deployment gate.

Explicit adoption of a historical staging identity uses `--adopt-user UUID`.
`--preserve-existing-password` is allowed only with explicit adoption. This keeps
the immutable author ID and existing MFA, clears the unused email and revokes
sessions. Unprovisioned legacy accounts stay disabled. Never automatically promote
historical users or delete referenced authors/audit records.

## Issue and revoke developer access

As an MFA-authenticated organization administrator, open Team → Manage access codes.
Choose a description, explicit projects, targets and existing evidence, download
permission, optional expiry/redemption maximum and active-session maximum. The
live-QNX and AI flags are separate opt-ins. Future/all-evidence access is explicit;
without it a code sees selected existing evidence and its own later runs only.
Save, copy the value from the one-time no-store creation response and deliver it
through your approved private channel. Reloading cannot recover it. Never enter
the raw value in descriptions, audit notes, URLs, configuration or API headers.

Developers redeem the code at `/access/`. Their opaque browser cookie carries no
code, and later requests recheck current authorization. Sessions expire after12h,
30min idle or an earlier code expiry. Sign-out releases active-session capacity
but does not refund a lifetime redemption. A leaked/lost code must be revoked and
reissued. Revocation is irreversible, invalidates its sessions immediately and
blocks queued work. Policy edits also revoke existing sessions. Revoke one browser
from the code's session list when other authorized sessions should remain valid.

The code detail records uses, last access and audit events without the plaintext
secret. No code authorizes arbitrary hosts, shell commands, credential uploads or
unqualified customer lifecycle tests. Public `/demo/` is recorded playback and has
no live-execution permission. Disabled AI does not block deterministic QNX work.

Already-started native supervision may finish bounded cleanup and collection
after browser authority is revoked. Inspect the exact run/cleanup facts; do not
interpret revocation as a QNX process kill. Queued work is reauthorized before
owned child creation. Same-ID recovery collects existing evidence under service
authority and must not launch a replacement. Unknown target state stays quarantined.

## Encrypted snapshot and local status tools

`manage.py backup_snapshot create --archive EXACT_NEW_PATH --key-file PRIVATE_KEY`
requires the protected local operator, a private destination directory and a
separate owned/private32-byte key. Existing destinations are refused. It streams
an authenticated encrypted PostgreSQL/evidence snapshot; it never contacts QNX.
`restore-drill` with the same arguments authenticates and restores only into an
exact new temporary DB, verifies identities/hashes/canonical histories and audit,
then drops only that DB. It does not overwrite the live database. Keep external
application/MFA keys separately; the encrypted data still contains sensitive DB
authentication state. Do not print it or the backup key. Production retention/
off-host copy/key-custody and actual least-privilege service drills remain required.

`manage.py operations_status --backup-dir PRIVATE_DIRECTORY` emits local queue,
lease/quarantine/disk/backup-receipt facts and explicit concerns, with no QNX probe.
Receipt age is not restore proof; unit activity is not native service health.
Missing/stale facts cause a nonzero exit. Actual staging use passed with no queued
work, expired lease or quarantine. Production unit/HTTPS alerts are not qualified
until the dedicated root installation runs. [PRIVATE_INSTALL.md](PRIVATE_INSTALL.md)
provides the exact next root command and service/backup/rollback qualification steps.

## W016 — staged runner job and evidence route (2026-11-09)

Customer `work` polls every30s; --once performs one job poll. Preserve device/job journals: reconnect collects the same native ID or resumes the same archive, never removes state to relaunch. The private `dispatch` ingests received evidence before local lab work; customer targets never route through server SSH. Defaults are two queued/active requests,20 daily requests and one native job in flight per target. Storage is bounded to256MiB outstanding uploads/64MiB per job, three retained ingestion attempts and a1GiB disk reserve. Failed stages remain for review; only this invocation's verified successful stage/chunks are cleaned after sealing. Keep quarantine until actual identity/native cleanup can be reviewed. No source data, keys or production units were changed.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 preserved staging qualification

Do not rerun the four native cases merely to fix presentation tests. Evidence under
evidence/runner-native retains original IDs and the original partially failed
browser driver; the continuation is explicitly recorded-only. The approved existing
QEMU guest was started without rebooting the host or modifying trust/firewall; new
build directories and histories are retained, original lab selection is unchanged.
No target history is deleted to recover disk space. Keep the runner's device key,
binding, launch/upload journals and archives across connection loss. Reconcile the
same run ID; an uncertain launch never authorizes a second launch or implies cleanup.
Separate customer-host and private/public production acceptance are still required.

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

If the safe failure JSON reports private_response_cacheable with successful
rollback from e1ef88c, retain all protected state and original backups. The reviewed
W023 command handles this known transition; do not delete markers or patch the
immutable application. Every dynamic HTTPS response now has no-store, including
anonymous private redirects. Existing static caching is unchanged. The one-command
workflow still validates/test-reloads, verifies HTTPS, renewal and own rollback,
then attempts authenticated browser/native acceptance. Record actual outcomes;
customer endpoints and AI stay disabled, off-server DR stays deferred.

## W024 graceful reload and strict rollback verification

For8000144's rollback_original_http_not_restored with own_changes_rolled_back:true,
read-only protected inspection confirmed actual original restoration and completed
Certbot renewal qualification. No state, marker or backup should be deleted. The
new reviewed driver accepts this exact known rolled-back predecessor only after
checking its committed candidate hashes, original backups/files and application
identity. It retains old driver history and the completed renewal proof (same
certificate only), and redoes the rollback drill using bounded strict HTTP/ACME
verification after graceful reload. Public HTTPS remains unqualified until this
new operator-run workflow and independent checks pass. Use the single command in
HTTPS_DEPLOYMENT.md with the new full driver SHA; no manual Nginx edits/restarts or
individual diagnostics are needed. Remaining acceptance still includes actual
HTTPS administrator/MFA, scoped codes/revocation, desktop/mobile, approved native
workflow and independent UAT. AI/customer endpoints stay disabled; off-server DR
is deferred.

## W025 Unix proxy identity and immutable authentication recovery

The cf15209 browser failure safely disabled the temporary identity/codes and
restored HTTP404/private readiness200. Do not reset state or repeat that deployment.
Use the W025 immutable auth recovery command in HTTPS_DEPLOYMENT.md. Its receipt
tracks backup/restore, private pointer and HTTPS binding for same-SHA recovery.
Unknown resources are preserved/refused. Original keys, config, units and database
schema/grants stay unchanged. New failures publish safe operator-cleanup.json even
when browser execution fails; browser-report.json records known password/MFA POST
status/stage only. Never request raw protected diagnostics, credentials or cookies.
The independent production-native blocker is approved_executor_registry_missing;
resolve only through a separately reviewed lab custody/approval workflow. Customer
runner endpoints and AI remain disabled; off-server DR stays deferred.

## W026 password-only administrators and preserved recovery state

Administrator login and privileged workflows require username/password only;
MFA is deferred. Do not remove authenticators or application/MFA/backup keys.
Local password recovery revokes sessions and preserves MFA data; --reset-mfa is
refused in current mode. Stale privileged sessions reauthenticate by password;
idle30 minutes/absolute12 hours expire independently of MFA. Developer/jury codes
remain scoped, expirable/revocable and auditable without personal accounts.

The previous root recovery stopped at strict untracked-content validation before
staging/backup. Do not clear state, remove caches or edit the old release. The new
single command validates derived caches against trusted committed source and
preserves prior preparation history before new immutable activation. Safe step/
failed_check JSON identifies failures; operator-cleanup metadata remains available
even after browser failure. Production-native registry remains missing; customer
host and AI qualification are still deferred/disabled. Preserve encrypted local
backups; off-server recovery automation is deferred, not passed.

## W027 exact derived-cache proof and recovery correction

The bytecode_payload_differs error from55daf08 is a cold-serialization false
positive for a genuine source-derived contracts.pyc. All14 protected cache hashes
can be reproduced from exact Git source and CPython3.12.3. Use the newly reviewed
recovery driver with unchanged3f4bafb application; do not delete caches or journal
history and do not retry55daf08. The recovery preserves the known unstarted attempt,
revalidates source/modes/header/full payload and continues only after proof.
Future unrecognized payloads still fail before staging/backup/services; retain them
for local investigation instead of weakening checks. inspect_release_bytecode.py
is read-only and emits metadata, known file paths and trusted-compile match status,
never contents. Nginx/auth/QNX permissions and unrelated services were not changed.
Actual private544/HTTP200 and HTTP-only404 restoration remain healthy; public HTTPS
and password/code/native independent acceptance remain unqualified.

## W028 active HTTPS release and distinct executor blocker

Active3f4bafb is healthy; operator1ee18b6 completed immutable recovery and production
HTTPS password/code/browser checks. Temporary acceptance principal disabled and codes
revoked; existing users/audit/evidence retained. No recovery retry is needed. Public
reachability is independently observed with a fresh remote HTTP200. Native acceptance
is blocked before execution because the approved production registry does not exist;
this is not a web service startup or password problem. Do not start workers or invent
registry entries. Keep the private executor identity, exact organization/project/
target/build/route binding and existing SSH trust requirements. Reviewed provisioning
and native before/after/job acceptance are the next operations gate. The HTTPS
configuration rollback drill is a completed workflow prerequisite; this turn did not
exercise full new-application rollback. Independent authenticated UAT and full release
rollback remain open, as do separate-host qualification and off-server DR. Customer
endpoints and AI stay disabled. No privileged action ran by the agent this turn.

## W029 one executor provisioning/native qualification workflow

[PRODUCTION_EXECUTOR.md](PRODUCTION_EXECUTOR.md) replaces individual diagnostic
requests with a reviewed fixed-scope operator command. It checks private custody,
installs mutation-denying lock-only DB guards, probes the actual canonical executor
context and then drives three HTTPS dashboard cases. Safe receipts include native
IDs, evaluator outcomes, downloads, observed cleanup, recovery and revocation facts.
No deployment/HTTPS/authentication change is required.74 tests passed; actual
production executor execution is pending. Current application3f4bafb /readyz/ is200.

Unknown files/approvals/overrides are retained and refused; same-driver completed
native receipts are revalidated/reused. Uncertain active work is not killed/reset.
Keep all existing QNX history: the lab has148 free entries. The final guarded idle
executor stop/start is not full application rollback qualification. Independent
[UAT](INDEPENDENT_UAT.md), compatible rollback and remaining P8 gates stay open.
Customer endpoints/AI remain disabled; off-server DR deferred.

## W030 selector failure after successful provisioning

The canonical executor is active and web readiness remains200. Operatorce97 passed the
actual probe and approvals but root acceptance misapplied the worker ownership rule.
The revised command preserves completed resources and resumes only this exact failure
with a protected history snapshot. It leaves an already-running idle dispatcher active
and rechecks locks/approval/custody read-only. No HTTPS/authentication change or data/key
replacement. Safe stage/failure JSON remains available; no individual diagnostic commands
are requested. Native verdicts/cleanup, guarded rehearsal and independent UAT remain open.

## W031 prequeue permission error

Journal metadata confirms the browser's30s wait followed a control_executorslot
permission error. The new driver checks each form POST status and reports its action
immediately. One revised command archives885, verifies no old DB runs/principal
authority remain and prepares the empty lock-only dispatch mutex. Dispatcher, private
keys and completed probe/registry/approvals are preserved. Unknown or active work
is never reset.86 tests passed; actual native outcomes/cleanup and full rollback/UAT
remain unverified. Current HTTPS readiness200, same3f4bafb, own services active.

## W032 collection investigation

The45bde2e attempt created nativew274989f6c30645818f and stopped at collect-sensor
with observer ValueError. Registry and mutex provisioning passed. Do not rerun
provisioning or queue another batch: reconcile the existing identity first. The
one read-only probe in PRODUCTION_EXECUTOR.md checks protected run/evidence metadata
without target I/O or mutations. Agent sudo authentication is unavailable; the
first operator probe had a split filename and executed no inspection. Actual native
cleanup/verdict remain unconfirmed. Temporary account disabled/codes revoked are
authorization cleanup only. HTTPS remains200, own services active, same3f4bafb.
