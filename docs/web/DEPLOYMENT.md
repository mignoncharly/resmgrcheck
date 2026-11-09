# Deployment record

W021 current state (2026-11-09): immutable544f22c is active privately. The operator
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
mandatory administrator MFA and no public registration/email authentication.

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
