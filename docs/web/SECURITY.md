# Security boundaries and review

Baseline: [OWASP ASVS 5.0](https://asvs.owasp.org/) Level 2 requirements where
applicable and the [multi-tenant cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html).
These are review checklists, not certification.

Threats include account takeover, cross-tenant object access, CSRF, uploaded source
injection, path traversal/symlinks, forged candidate identity, queue duplication,
stale job authorization, target contamination, resource exhaustion, AI data egress
and public execution of privileged lab operations. Fail closed on missing approval,
required capability, evidence, ownership or transport certainty.

Controls to qualify: verified accounts, Argon2 passwords, MFA for owners/admins and
live execution, secure sessions and invalidation, CSRF, shared rate limits, explicit
membership scoping, fixed profile/route/build allowlists, bounded subprocesses,
original run-ID recovery, target leases/quarantine, immutable artifact verification,
safe downloads and report sandboxing, audited roles/exports, retention and backups.
AI needs project opt-in and per-request consent, redacted bounded inputs, validated
event citations and reserved cost budgets. Treat source/logs as data, not instructions.

P0 findings: no passwordless administration; requested DNS absent; no dedicated
ResMgrCheck OS/database/SMTP/provider provisioning yet. These are production blockers,
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
