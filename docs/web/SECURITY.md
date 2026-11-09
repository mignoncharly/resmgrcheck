# Security boundaries and review

W015 enrollment is staged/disabled by default.256-bit600s one-use enrollment
credentials are HMAC-verifier-only in the DB, bound to a precreated exact target;
they never approve execution. A customer-local Ed25519 device key signs discovery/
requests; a separate central seed signs replies, using the strict existing private
file/systemd ACL validator. TLS trust, hostname verification and the pinned server
key are mandatory. Requests have60s freshness and unique125s-retained nonces plus
rate/capacity limits. The machine-only CSRF exemption refuses browser cookies;
administrator mutations retain MFA/tenant/CSRF checks. PG guards prevent identity/
tenant substitution and revoked-key resurrection. Changed discovery quarantines;
stale heartbeat means disconnected, never healthy. Customer SSH/license material
does not enter enrollment or central storage.68 checks include actual loopback TLS
and PostgreSQL, with modeled discovery. Separate-host/native/public qualification
and independent exposed-endpoint review remain pending. Do not activate production
before new credential/grant/migration/rollback checks.

Baseline: [OWASP ASVS 5.0](https://asvs.owasp.org/) Level 2 requirements where
applicable and the [multi-tenant cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html).
These are review checklists, not certification.

Threats include account takeover, cross-tenant object access, CSRF, uploaded source
injection, path traversal/symlinks, forged candidate identity, queue duplication,
stale job authorization, target contamination, resource exhaustion, AI data egress
and public execution of privileged lab operations. Fail closed on missing approval,
required capability, evidence, ownership or transport certainty.

Controls to qualify: locally provisioned administrator usernames, Argon2 passwords,
mandatory administrator MFA, scoped access-code browser sessions, secure sessions and invalidation, CSRF, shared rate limits, explicit
membership scoping, fixed profile/route/build allowlists, bounded subprocesses,
original run-ID recovery, target leases/quarantine, immutable artifact verification,
safe downloads and report sandboxing, audited roles/exports, retention and backups.
AI needs project opt-in and per-request consent, redacted bounded inputs, validated
event citations and reserved cost budgets. Treat source/logs as data, not instructions.

P0 findings: no passwordless administration; requested DNS absent; no dedicated
ResMgrCheck OS/database/provider provisioning yet. Dedicated OS/database/HTTPS
requirements remain production blockers,
not reasons to weaken isolation or borrow another application's credentials.
The existing QNX root login is loopback-only and may be reached only by the approved
private executor. Never expose it or hand its credential to a public web process.

Security results and unresolved findings belong in TEST_EVIDENCE.md. No production
security or independent penetration-test claim is made from unit tests alone.

P5 evidence inventories are closed/immutable through PostgreSQL triggers. Every
authenticated download verifies safe no-follow components, regular/non-hardlink
type, byte length and SHA-256 against the inventory and canonical engine evidence.
Malformed/changed required evidence withholds the conclusion, report and archive.
Authorized project membership is required on every object; no anonymous private
sharing links exist. Retention removes only a validated exact owned local tree;
unknown files/directories, unresolved native cleanup, holds and active derivatives
stop removal. These are integrity controls, not hardware WORM certification.

P6 AI uses explicit project opt-in plus signed per-request consent, immutable packet
identity, narrow original-source handling, best-effort redaction, exact reference
validation, output hashing/escaping, conservative cost ledgers and a bounded private
child. Data/source instructions never gain tool or mutation permission. Missing or
unavailable AI does not gate native execution. Provider credentials are read only
by its separate worker; production OS enforcement is still a P8 requirement. Real
provider results, account access and retention approval remain unverified until
the dedicated integration is actually exercised. See AI.md; mocks are not proof.

The owner-approved access decision supersedes historical email gates. No public
registration/email verification/reset/invitation or SMTP dependency remains. Codes
use256-bit random secrets, domain-separated keyed verifiers, one-time display and
no-store responses; regular users have no accounts. PostgreSQL row locks enforce
concurrent redemption/session limits. Every private operation rechecks project/
target/evidence scope and optional live/AI flags. Session/code revocation, policy
version and expiry deny queued work, with a lock fencing exact child creation.
Running native work may finish owned bounded cleanup/collection after revocation;
that does not preserve browser access or authorize a new operation. Code values are
not accepted in API headers/query strings or stored in session/audit data.

Administrator recovery/provisioning is local, requires root for production, and
accepts passwords only through getpass or an owned0600 regular file. Changing an
environment label alone cannot grant staging recovery access: the development
exception also checks the owned workspace and exact private staging/test database.
Legacy account tables/author IDs remain archived, with unprovisioned accounts
disabled rather than automatically promoted. See ACCESS_MODEL and test evidence.

P8 staging checks now include protected no-follow secret files, production-only
hostname/origin/path/role validation, refusal of executor/provider configuration in
HTTP, and dispatcher role barriers. The logging formatter redacts complete raw
code/provider-key patterns even inside exception text or attacker-chosen paths.
Nginx templates exclude URI/query/body/cookie/IP from their access-log format.
The per-service role grant SQL was tested on real PostgreSQL:22 permission denials,
nonowner/nonprivileged roles and readable evidence; all test role/ACL changes rolled
back. Actual peer mappings/systemd containment remain NOT_RUN without root.

Snapshot/restore tests authenticate ciphertext before any extraction/SQL, reject
links/traversal/unknown members, preserve the live database, verify245 artifact hashes
and14 collected histories, and prove the restored audit trigger. A real retention/
snapshot lock-conflict test demonstrates bounded exclusion. Backups contain sensitive
DB authentication state and stay encrypted/private; off-host custody, production
backup role/service execution and rollback are still unqualified. No proprietary
QNX content or private runtime archive/key is in Git. An OSV query of all15 pinned
runtime packages returned no listed vulnerabilities on2026-11-07; that is point-in-
time database coverage, not proof of absence or an independent security audit.

W014 corrects a restore-verification gap: an UPDATE matching zero rows never
exercises a row-level audit trigger. The isolated verifier now checks the exact
restored trigger/function definition and enabled state, then inserts a synthetic
row in a forced-rollback transaction in its exact new temporary database. Both an
actual action change and DELETE must raise the expected append-only SQLSTATE and
message through separate savepoints. Metadata alone, permission errors and zero
affected rows cannot qualify the guard. Rollback must preserve counts, remove the
probe and preserve the snapshot database identity; only the database created by
that invocation is dropped, without FORCE. Inspection reports metadata/counts and
definition hashes only and always withholds a passing verdict. No live audit test
or schema repair is performed. The original ciphertext, keys, audit records and
unit isolation remain unchanged. Development PostgreSQL tests passed; the actual
preserved production snapshot restore remains an operator gate, not yet PASS.

W012 records the operator-confirmed systemd LoadCredential compatibility correction.
The original root:root0600 files are preserved. In the actual ExecStartPre context,
systemd supplied root:root0440 regular files whose ACL grants only owner read and
named UID982 read, with owning-group/other permissions zero. The group mode bits
encode the ACL mask here; mode0440 alone is never accepted as evidence of safety.

The shared credential reader opens every component with no-follow directory
descriptors, requires a single regular inode with trusted ownership and at most
4096 bytes, bounds the actual read again and rejects invalid UTF-8/NUL. Ordinary
private files require0400/0600 without an access ACL. The delegated exception
requires the fixed per-role `/run/credentials/resmgrcheck-*.service` path, matching
CREDENTIALS_DIRECTORY and exact credential ID, current nonzero effective UID equal
to the configured dedicated OS account, root:root0440 and the exact five ACL entries
(owner read, named current UID read, owning group none, mask read, other none).
The root-owned0550 parent must have the corresponding exact read/search ACL.
Extra/duplicate/unrelated user/group/other grants, write/execute bits, malformed
ACLs, missing ACL support, wrong owner/group/account/path/context and hardlinks
fail closed. The exception cannot be enabled by an environment path or0440 mode
alone. Production still requires credential files; environment-secret fallback,
root web execution, source-key permission changes and runtime_check bypass are absent.

The initial-install release correction checks the exact original marker/clone
identity, unchanged canonical unit and inactive dedicated worker/timer contexts.
It stages independent objects into new owned attempts, verifies a clean exact
commit/manifest and publishes a new immutable directory before pointer activation.
Atomic Linux no-replace publication also refuses an existing empty directory.
Unknown resources are refused/preserved. No original release/index, dependencies,
schema, data/audit, secrets, configs, grants, units or target state are overwritten;
Git inspection uses no optional locks to avoid index refresh writes. An exclusive
lock, exact immutable intent and idempotent validation support restart and pointer
rollback. Failed attempts remain for inspection; no automatic cleanup or healthy
rollback claim is made for the original credential-failing release.

Seventy-one focused checks include positive/negative credential ACLs and actual Gunicorn
application-loader/runtime_check paths in subprocesses with simulated UID982 and
DB/sandbox facts. Real unit startup, peer-role/namespace containment and readiness
remain operator qualification gates. No successful corrected production runtime or
P8 pass is claimed from these tests; see PRIVATE_INSTALL and W012 for exact scope.

W013 confirms the credential correction's real runtime_check success through the
operator's d6513ba observations. The subsequent Gunicorn failure was duplicate fd3
consumption:26.2.0 concatenates explicit fd binds with systemd-discovered descriptors.
The web unit removes only `--bind fd://3`. No launcher, root web execution, TCP
listener, socket permission change, credential bypass or sandbox relaxation is added.

Gunicorn defaults to no configured bind. In production its startup hook requires
no explicit address, matching LISTEN_PID and exactly one LISTEN_FDS entry. It
duplicates3 only for inspection, checks the native socket family/type/listening
state and exact `/run/resmgrcheck-web/application.sock` name, then closes only the
duplicate and leaves original3/LISTEN_* for Gunicorn discovery. Missing/invalid,
foreign-path/non-socket descriptors or duplicate binds fail before listening.
RestrictAddressFamilies=AF_UNIX, IPAddressDeny=any, LoadCredential, runtime_check,
resmgr-web identity, DB-role restrictions and all remaining unit directives persist.

The second immutable upgrade pins the verified credential release/manifests and
unchanged shared virtualenv, refuses changes to credential/settings/dependency/
DB/native code, and allows only the reviewed web ExecStart suffix deletion. It
also verifies the unchanged canonical socket unit/overrides. An exact-target
protected intent, existing release lock, verified new immutable directory and
atomic web-unit/current replacements support resume and rollback while web is
stopped. Neither original release/index, keys/config/database/audit nor other units
are rewritten. Operator daemon-reload is explicit. Unknown resources are preserved;
rollback returns to a known socket-failing release, not a qualified healthy service.

Real inherited-descriptor/Gunicorn tests model LISTEN_*; four additional real user
systemd cases cover both activation modes with a synthetic WSGI response and actual
IP-socket denial. Their own units stop and sockets disappear after testing. These
do not qualify production UID982, real DB/keys or full namespace/BPF containment.
Actual corrected root-managed activation, runtime_check and private HTTP200 in both
modes remain mandatory before advancing the current production gate. No public
deployment or P8 pass follows from user-manager tests alone.

## W016 — staged runner job and evidence route (2026-11-09)

Launch grants are durable single-use transitions, fenced by current user/code authority,15-minute queue/MFA freshness, exact runner capability/route/build and quotas. A local fsynced journal precedes grant delivery, so crashes/loss never select a replacement run or silently restart an external service. Customer-local mode/build allowlists may refuse central approval. Fixed read-only storage inventory reserves native file/block budget. Chunk uploads are signed/idempotent/bounded; DB guards reject changed archives/chunks and deleted/reset launch provenance. HTTP may insert chunks but cannot update/delete them or seal artifacts; private sealing precedes chunk cleanup. Tar modes, links, traversal and unknown members are refused. Native contracts/identity/seals are verified before no-replace publication. Failed stages remain for bounded recovery. Real PostgreSQL SET ROLE and loopback TLS upload/ingestion passed; independent review and separate-host/public/native-runner qualification remain pending.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 security qualification boundary

Actual staging browser tests exercise password/TOTP, scoped live-code issuance,
recorded evidence access, revocation and cross-project/admin denials. The live code
form requires an explicitly approved enabled customer runner. Enrollment's first
response publishes bounded discovered capabilities; retries require the same key
and inventory and an unrevoked, nonquarantined identity. External attachment rejects
fixture-control modes and lifecycle suites. Recovery retains the one launch grant
and exact native ID after an observed upload503. No pending/cleanup claim is inferred
from reconnection alone. Unit/PG tests remain required for negative authorization,
replay, quota and immutable-evidence cases beyond those browser journeys.

The new representative mailbox service has real QNX timeout/input qualification,
not universal driver support. No private customer host, public HTTPS, root-systemd
new-release qualification or independent security review is available yet. Existing
secure production runtime/restore is operator-provided evidence for3821952. P8 is
IN PROGRESS, AI disabled and off-server disaster recovery deferred.

## W019 initial immutable private upgrade gate (2026-11-09)

upgrade_private.py stages a new no-replace release, binds a fresh encrypted snapshot
and actual isolated audit-proven restore before additive migrations0018–0020, applies
only new least-privilege grants, and publishes separately inventoried static files.
Activation checks live schema/role/static gates before switching current; canonical
units/configs, original source keys, preserved engine and old releases stay unchanged.
Customer endpoints/AI remain disabled. Rollback never reverses schema or deletes data
and refuses incompatible retained customer/mailbox records. PRIVATE_UPGRADE.md gives
reviewed exact operator commands; no privileged apply was run by the agent.

Fifteen focused tests passed in7.836s. Git/filesystem recovery uses real disposable
clones with modeled root/unit contexts; PostgreSQL schema/grants/static publication
checks are actual unprivileged execution. These are not root production deployment
or rollback qualifications. Early fixture field/mode errors were corrected; static
attempt creation now accounts for restrictive operator umask, without touching old
trees. A full-module regression follows.

The latest ordinary verified curl HEAD to the intended public HTTPS origin fails
with exit60: certificate hostname mismatch. Verification was not bypassed, no HTTP
status was obtained and no Nginx/certificate was modified. This observation is from
the Ubuntu shell, not independent off-server verification. See
evidence/private-upgrade/public-tls.json. Public TLS/HTTPS is a confirmed remaining
blocker; P8/P9/P10 and independent/separate-host acceptance are not complete.

W019 closing regression: all315 explicitly selected web tests passed in83.703s.
The disposable test/restore DBs and generated rmctest roles were absent afterward.
The initial ambiguous `test tests` selection ran zero tests and is not counted.
See evidence/private-upgrade/web-tests.txt. No production deployment is claimed.

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
