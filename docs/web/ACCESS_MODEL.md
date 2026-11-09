# DWEB-001 — Administrator accounts and scoped access-code sessions

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. Actual private release remains544f22c; corrected immutable
activation/public acceptance is pending. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

Owner-approved2026-11-07. Replaces the former public registration/email account
decision for the web application. Historical native evidence and earlier web test
records are preserved; they do not qualify the revised authentication gate.

Only administrators have username/password accounts. A protected local command
provisions them; there is no public signup, email verification, invitation or email
reset route, and no SMTP dependency. Argon2 password hashes, password changes and administrator session revocation are
mandatory. MFA is deferred for this hackathon release: existing authenticators and
encryption keys are retained but neither login nor privileged actions require a
second factor. Only a reviewed future release may reactivate it. Protected local
password recovery preserves these records; --reset-mfa is refused while deferred.
Production provisioning/recovery requires root. Administrator sessions expire after
30 idle minutes or12 absolute hours; privileged actions retain recent-password
confirmation without an MFA challenge.

Developers/testers receive an administrator-issued code and create no User row.
Generation uses256 random secret bits plus a random locator. The raw value is shown
once in the creation POST response, marked no-store, and is never saved in the
database, session, logs, audit, screenshots or test artifacts. The database stores
only a domain-separated HMAC-SHA256 verifier keyed by the private application key.
Rotating that key invalidates all code verifiers and requires replacement codes.
An administrator cannot retrieve the original value; revoke/reissue if it is lost.

## Grants and sessions

The administrator selects an organization and explicit project/target/evidence
scope, download permission, optional lifetime redemption maximum, active-browser
session maximum1–20, optional UTC expiration, and live-QNX/AI flags. All-evidence
access is an explicit opt-in covering selected projects/targets and their future
evidence. Without it, only individually selected existing evidence and the code's
own later runs are visible. The UI flags apply to each selected project; editing
replaces the listed grants and revokes current sessions. Revocation is irreversible.

Successful CSRF-protected POST redemption rotates the opaque Django browser
session and CSRF token. A server-side AccessSession binds it through a keyed
browser-session fingerprint. No raw code is stored in the browser session or sent
on subsequent page requests. Codes are not Authorization/Bearer/query-string API
credentials. The SQL-backed cookie is HttpOnly/SameSite=Lax and HTTPS-only in
production. A session expires after12 hours or the code's earlier expiry, with a
30-minute idle limit. Sign-out revokes its exact access session.

Redemption locks the code row in PostgreSQL; expiry, lifetime uses and active-session
capacity are checked within the same transaction. Concurrent redemptions cannot
oversubscribe these limits. Expired/revoked/malformed/unknown/over-capacity attempts
get a generic error and never echo the supplied value. Shared database limits
bound redemption per IP/global and administrator login per IP/normalized username.
Nginx must overwrite the real-client-IP header on the private production socket.

Every private view/list/API, evidence/report/ZIP download, source/AI retrieval and
queue uses the same scoped principal selectors. Administrator organization/project
roles remain scoped; a locally provisioned platform owner is explicitly privileged.
Code sessions cannot create accounts, codes, organizations, memberships, target
routes, build approvals or policies. They cannot choose arbitrary SSH hosts,
commands, files or SDK actions. Recorded public playback grants no live execution.

## Deferred work and recovery

Run, AI and source records store exactly one authority: an administrator FK or an
AccessSession FK. Native IDs, signed intents and evidence identities remain
immutable. Workers recheck session/code revocation, expiration, policy version,
scope and current target/build approval. Code edits/revocation invalidate all its
sessions; explicit session revocation invalidates only that browser. Queued work
with withdrawn authority is withheld before starting a child or sending AI data.

An additional transaction fences code revocation against the exact owned local
child creation. It holds the code row only while spawning, never across the QNX
service operation. Administrator password/session changes are also checked at
that boundary. A code cannot authorize a new run after revocation. Already-started
native supervision may finish bounded cleanup/collection under service authority;
this is not continued browser access, a duplicate launch or a termination claim.
Same-ID recovery may collect existing evidence after actor revocation and still
checks exact target/tenant/build bindings. Unknown ownership/cleanup remains ERROR.

AI remains optional. A code additionally needs its AI grant, project opt-in,
available provider, signed exact-payload consent and transactional project/global
budget. Sources/AI analyses created by a code are restricted to that code's scope;
other codes do not gain them through guessing IDs. Disabled AI does not block
native testing. Real provider qualification is conditional on dedicated local
configuration; mocks never establish provider functionality.

## Safe migration and records

An encrypted private staging checkpoint/restore preceded the migration. Schema
migrations0013–0017 add code/session authority and tenant/identity constraints.
Legacy identities and immutable author/audit references remain. Unprovisioned old
accounts are disabled with an audit event rather than silently elevated. Existing
staging administrator adoption is an explicit local provisioning action, preserving
its password hash/MFA/evidence identity and invalidating old sessions. No regular
developer identity is converted to a password account.

Archived legacy email/invitation/deletion rows remain for provenance; there are no
live routes, forms or background jobs that use those workflows. Original native
bundles, manifests, SDK/SSH authentication, CLI, QNX fixtures and published release
are unchanged. Retention still protects historical hashes, audit and supervised
cleanup facts. See OPERATIONS.md for commands and TEST_EVIDENCE.md for actual results.

Acceptance requires PostgreSQL provisioning/password login (MFA deferred), invalid/expired/revoked code,
limits/concurrency, session/code revocation, rate/CSRF, project/target/evidence/AI
boundaries, queued execution authorization, anonymous denial and real responsive/
JavaScript-disabled browser qualification. Public deployment remains gated on this
revised acceptance plus production hardening and independent operator UAT.
