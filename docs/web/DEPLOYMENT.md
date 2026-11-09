# Deployment record

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. W028: immutable application `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`
is active. Production password/code/browser acceptance passed; an independent
external public fetch returned HTTPS 200. W030: executor registry provisioning and
the actual service-context probe passed in the operator workflow. Native acceptance
stopped at root plan selection; its correction/resume is prepared. Independent
authenticated acceptance remains pending.
P8 is IN PROGRESS. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

W021 historical state (2026-11-09; superseded by W028): immutable544f22c is active privately. The operator
confirms HTTP200, nonroot/isolation and encrypted isolated restore/audit proof.
[HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md) supersedes the historical multi-command
public handoffs below with one reviewed operator command that installs only the
ResMgrCheck HTTPS settings, validates/reloads, proves rollback and runs real HTTPS
browser acceptance. Customer runner/AI remain disabled and off-server DR deferred.
Actual privileged/public/native acceptance results must still be recorded.


Requested URL: `https://qnx-resmgrcheck.gestionatech.de`. Public HTTPS unverified.
W015 private pointer:3821952. Operator-confirmed private HTTP200/nonroot runtime/
isolated encrypted restore are accepted, not repeated. Read-only metadata confirms
active private web/socket/DB. External fetch could not access the URL, establishing
neither a valid certificate nor an HTTP result. No Nginx or root-service change ran.

Customer-runner enrollment is staged/disabled by default. Its additive migrations,
runtime grants, separate signing credential and immutable rollback are not yet
production-qualified. No broader deployment command is ready. The owner has no
separate runner host yet; separate-host native onboarding and independent endpoint
review remain public-release gates. Off-server disaster-recovery automation is
deferred for the hackathon, not passed. Preserve encrypted local backups and record
the single-server-loss/key-custody recovery limitation.
Read-only P0 inventory found 12 enabled Nginx sites, no matching vhost, many live
applications and PostgreSQL instances, Python 3.12.3, Nginx 1.24.0 and available
loopback port 8431. At P0 the requested DNS name did not resolve; a later read-only check found it resolves, without an application vhost or verified HTTPS. No existing site,
firewall, database, guest or host service was modified.

Staging uses a separate private Unix-socket PostgreSQL cluster and virtualenv
under ignored `.local/web`, with the app bound only to loopback. This isolates
test data from all existing databases without requiring root or borrowing secrets.
It is not a production OS isolation or public HTTPS acceptance result.

Production requires the dedicated accounts/directories/database, constrained
executor credential access, root-owned systemd units, reviewed vhost, valid TLS,
the revised administrator/access-code gate, backup/restore and rollback proofs. Provisioning and
external DNS/TLS changes must wait for the contract's applicable readiness gates.
[PRIVATE_INSTALL.md](PRIVATE_INSTALL.md) contains the concrete private root
preparation command, dedicated resources, tests and remaining gates. The script
starts no public listener and never touches Nginx/DNS/TLS. It is prepared, not
root-executed or production-qualified. Never send passwords/private configuration
or keys in chat.

Rollback baseline is the preserved published branch/revision `ca4f74e`. Web work
is isolated on `feature/production-web-ai`; removal/stop actions may name only the
new dedicated ResMgrCheck resources. Existing engine binaries/evidence and other
applications must survive a rollback.

The former SMTP prerequisite is superseded by ACCESS_MODEL.md. Production uses
protected local administrator provisioning/recovery, scoped access-code sessions,
password-only administrator authentication (MFA deferred) and no public registration/email authentication.

## W016 — staged runner job and evidence route (2026-11-09)

Signed job delivery, one-launch journals, same-ID recovery, bounded upload and private ingestion are staged.108 focused regressions plus one actual additive migration/legacy encrypted restore test passed. The real loopback TLS evidence-upload journey imports genuine recorded QNX bytes and retains their original native ID; it does not establish new native activity. Production pointer remains3821952. No new code/schema/key/grant was deployed. Additional native/browser and immutable release checks continue; public activation still requires separate-host customer qualification and independent acceptance.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 release boundary

Actual local TLS/browser/QNX staging is recorded under evidence/runner-native. It
is not public deployment evidence. The current private release remains3821952 with
operator-confirmed runtime/readiness/restore. The old restore-only recovery helper
must not deploy this broader schema/runner/native change. New code requires a new
immutable directory, additive migrations/grants, new static assets, protected
pre-upgrade snapshot and explicit compatible rollback qualification. Preserve all
existing keys and releases; never patch current or reverse migrations containing
customer data. No public vhost or TLS change is justified until separate-host,
intended-origin authentication/native/isolation and independent gates pass.

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

The e1ef88c rollout automatically rolled back on private_response_cacheable.
W023 enforces no-store at the dynamic HTTPS boundary and tests the exact deployment
probes against real isolated Django/Nginx. Use the newly reviewed driver command
in HTTPS_DEPLOYMENT.md with existing immutable application544f22c. It preserves
original backups and known failed-driver history, verifies the old committed
payload and restored originals, and then installs only the corrected own payload.
No public acceptance or production completion is inferred from isolated tests.

## W024 graceful reload and strict rollback verification

W024 confirms8000144 restored original HTTP-only configuration and preserved the
healthy private544f22c release. The completed Certbot dry run was not the failure;
the one-shot HTTP rollback probe raced Nginx's asynchronous worker reload. The
reviewed replacement checks exact originals/modes/link and waits boundedly for
HTTP404 plus ACME, preserving strict TLS/security checks on reactivation. Persistent
wrong behavior still fails. It accepts the known rolled-back8000144 record with
verified hashes/backups/history and reuses the completed unchanged-certificate
renewal proof. Use the new driver SHA in the single HTTPS_DEPLOYMENT.md command.
No deployment success is claimed from isolated tests or restored HTTP behavior.

## W025 Unix proxy identity and immutable authentication recovery

W025 replaces the old HTTPS-only retry with recover_https_auth.py: the actual
failure is allauth client-IP discovery on the private Unix listener. A new immutable
settings correction is necessary; never patch current or publish544f22c again as
an authenticated acceptance attempt. HTTPS_DEPLOYMENT.md gives the single reviewed
operator command and rollback variant. New-release scope, frozen units/native code,
fresh encrypted backup/isolated restore, private readiness/isolation, retained
failed-driver history and completed same-cert renewal proof are checked. Customer
registry absence remains a blocker, not permission to provision credentials/routes.
No corrected production activation has been performed by the agent.

## W026 password-only administrators and preserved recovery state

The current approved application uses password-only administrators with dormant
MFA preserved. The previous recovery failure was untracked-content validation,
not MFA. Follow HTTPS_DEPLOYMENT.md's updated single immutable recovery command;
known prepared325f367/e6890b0 history and original544 are retained. Derived caches
must match exact trusted compilation; new root launchers prevent bytecode writes.
Unknown content or changed state remains a blocker and is never deleted to force
retry.392 regressions and actual isolated Gunicorn/Nginx browser checks pass;
actual systemd/new release/public HTTPS/independent acceptance remain pending.

## W027 exact derived-cache proof and recovery correction

W027 changes only recovery tooling/tests/docs. Application3f4bafb, authentication,
Nginx candidate bytes, units, dependencies and native permissions are unchanged.
The prior55daf08 preflight rejected a legitimate CPython serialization; exact full
hash reconstruction now proves all14 caches. A reviewed driver transition retains
the unstarted/no-backup attempt and re-runs strict source/cache checks before any
staging/action. Use HTTPS_DEPLOYMENT.md's same application with the new driver SHA.
No privileged deployment was executed by the agent; actual P8 acceptance is pending.

## W028 production activation and bounded public acceptance

Operator driver1ee18b6 completed immutable application3f4bafb activation. The original
544 release and all keys/data/history remain preserved. The operator workflow passed
original-cache validation, fresh backup/isolated restore, private runtime and HTTPS
checks before actual production browser acceptance. Agent pointer/unit checks confirm
the new release and active own services. HTTPS200/certificate/security headers passed
from the VPS; a fresh independent Firecrawl public landing fetch also returned200.
Actual password/code/browser acceptance passed46 views/12 zero-violation scans.

This is not full production completion: production native runs=0, missing approved
executor registry BLOCKED; independent authenticated UAT and full new-application
rollback remain pending. No repeat of the successful deployment is requested. No
runtime source, Nginx configuration, unit, database, credential or execution grant
was changed by this evidence-only checkpoint. Customer endpoints/AI remain disabled;
off-server DR remains deferred. P8 IN_PROGRESS.

## W029 executor qualification prepared without web deployment

Active application3f4bafb, dedicated HTTPS and password/code acceptance from W028
remain unchanged. Fresh VPS-origin trusted HTTPS /readyz/ returned200. Both approved
QNX deployments and ten native file hashes were verified read-only as development
UID1000; this does not qualify production UID981/GID973 or systemd.

The new [executor-only operator workflow](PRODUCTION_EXECUTOR.md) is staged/tested,
including guarded lock-only DB permissions, private registry/route custody, an actual
service-context probe, three dashboard cases and idle stop/start rehearsal.74 tests
pass with real disposable PG/files and modeled privileged effects. No root apply,
production native run or full application rollback occurred. P8 remains IN_PROGRESS.
[Independent UAT](INDEPENDENT_UAT.md) remains NOT_RUN; AI/customer endpoints disabled.

## W030 acceptance-only resume; no application deployment

Operatorce97 installed the executor registry, passed its actual systemd probe and
published scoped approvals. The root plan selector then failed before native work.
The correction changes coordinator tooling/tests only and retains active3f4bafb,
Nginx/authentication configuration, units, keys, DB records and historical evidence.
78 tests passed and current HTTPS readiness is200. The reviewed new driver privately
verifies and archives the exact failed state, reuses the probe/approvals and resumes
acceptance. Actual production native IDs and P8 completion remain pending.
