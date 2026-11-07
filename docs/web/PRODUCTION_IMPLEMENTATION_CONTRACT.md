# ResMgrCheck Production Web + AI: implementation contract

Status: **implementation specification**, not a deployed or verified web application.
Baseline: public qualified commit `ca4f74e0fcff33b6f6ebf6c553b3f8379f6440e0`.
Implementation branch: `feature/production-web-ai`.
Preferred production domain: `qnx-resmgrcheck.gestionatech.de` (DNS names are case-insensitive; use lower-case canonical URLs).
Product goal: useful, secure, maintainable, real-user ResMgrCheck web application with CLI parity and optional evidence-grounded AI. The source QNX engine and the published hackathon release must remain independently usable.

## Approved access decision (2026-11-07)

The owner-approved administrator/access-code model replaces all prior public-user registration, email-verification, email-reset and SMTP requirements. It reopens affected authorization gates; previous email tests remain historical evidence only. Codes establish secure revocable browser sessions, never arbitrary host/command access. AI remains optional: a disabled provider must not block deterministic testing or deployment of the qualified no-AI mode. Public deployment waits for revised authentication and production security gates. See ACCESS_MODEL.md.

## Nonnegotiable truths

- The verified engine has sensor and job fixtures, 36 release expectations, 107 host tests and native evidence, but does not automatically support arbitrary QNX resource managers.
- Existing external attachment provides read-only health diagnostics with unverified running-build/instance identity; full external lifecycle testing requires new QNX adapter/observer work and native qualification. UI/API must expose this as UNSUPPORTED, not PASS.
- Web presentation never recomputes PASS/FAIL/ERROR/UNSUPPORTED/NOT_RUN. The existing canonical evaluator is authoritative.
- AI can explain, summarize, suggest source or tests, and review differences with cited evidence references. It cannot change verdicts, run arbitrary tools, apply patches, or restart services without an explicit independently authorized workflow.
- Never put QNX runtime, private SSH keys, myQNX license material, passwords, generated images or protected configs into Git, browser output, AI prompts, public evidence packages or logs.

## Recommended architecture

Keep the existing native C11/qcc runner/worker, Python evaluator, immutable evidence, CLI, and QNX guest intact.

Use a new production `web/` Django application (compatible, actively maintained supported Django/Python versions as confirmed by agent), PostgreSQL, and Nginx/TLS. Prefer server-rendered HTML with lightweight progressive enhancement / HTMX over a new full SPA unless interaction proves it necessary. An explicit application/service boundary invokes the existing CLI through fixed argument vectors (never arbitrary shell expressions). Do not duplicate the test engine in Django.

Split the public **control plane** from the **execution plane**:
- Public HTTPS: authentication, organizations/projects, role management, target registration, suites, run requests, run history, immutable evidence downloads, offline report views, AI explanations, admin and audit.
- Durable dispatcher: database-backed jobs, explicit state transitions, leases, retries with idempotency keys and bounded queues; workers must reauthorize organization/target ownership before dispatch. A queued web request is not itself a successful QNX run.
- Private executor: nonroot isolated OS account/service with narrowly-scoped access to an explicitly approved lab target and verified SSH host keys. Restrict run profiles and fixture modes by registered capabilities. Execute QNX tests only for authorized attached targets; never accept arbitrary user-supplied hostnames, commands, binary paths or remote service paths as executable instructions.
- The current IONOS VPS has other live apps. Inventory memory/disk/ports, systemd units, Nginx sites and database capabilities before changing anything. Use dedicated user, database, virtualenv, directories, socket and systemd units. Preserve unrelated sites and services.
- Production default should not give anonymous users shared execution on the owner's privileged lab. Isolate demo mode from live execution. Multi-tenant customer-owned target connections require an explicit safe architecture (e.g., outbound agent/proxy with per-tenant identity or restricted dedicated runner); do not turn on arbitrary shared-host SSH.
- AI is an optional server-side provider adapter. API keys live only in secret runtime configuration with least privilege; never ask the user to paste secrets into chat. Support explicit consent, per-project AI enablement, prompt/response redaction, model/provider provenance, request timeout, token/cost budgets, rate limits and no-AI fallback. Treat uploaded source and logs as untrusted data; defend against prompt injection.

## Real-user workflows to ship

1. Anonymous landing, scope, documentation and recorded demo. Distinct administrator username/password/MFA login and developer access-code redemption. No public registration.
2. Only locally provisioned administrators have password accounts, securely hashed with mandatory MFA, protected password changes and global session revocation. Lost-password/MFA recovery is an audited protected server-side procedure. No email authentication or SMTP dependency. Developers/testers have revocable browser sessions after code redemption, without user accounts.
3. Administrator-issued cryptographically random access codes carry explicit project/target/evidence grants, optional expiry, redemption and active-session limits, download/live/AI permissions, usage/audit and immediate revocation. Display raw codes once; store only a secure keyed verifier. Never accept them as unrestricted API credentials. Repeat scoped authorization in every view/API, queue, execution boundary, download and AI retrieval. Administrators retain scoped organization roles; no public administrator signup.
4. Target management: explicit local/owned lab or verified remote agent; capability discovery and provenance. Accurate connect, unknown, unavailable, unsupported, and last-seen statuses.
5. Profile/scenario selection with server-side validation; target compatibility checks, required capability checks, preview and confirmation.
6. Job submission: idempotent scheduling, concurrency quotas, bounded worker/process leases, progress and cancel-request state, crash/SSH-loss recovery using exact stored run IDs. "Cancel web job" must not falsely claim to have stopped a QNX process.
7. Runs: list/filter, real status, completion and coverage, test verdicts, before/after comparison, original-instance health, immutable evidence references, raw bundles and HTML report. Never silently rewrite evidence or display AI opinion as test result.
8. Source correction/replay: import real before/after candidate manifests, show immutable source/build hashes and unchanged profile/settings. Optional patch suggestions must require developer review and separate actual deployment permissions. Fixture-mode contrast stays "incomparable", not "fixed".
9. AI Explain: case-by-case explanation grounded in exact event IDs, contract, manifest and evidence. Clearly label interpretation and uncertainty. AI output is supplementary and not authoritative. No provider or model should be invented.
10. Public demo sandbox based strictly on **recorded verified evidence**, visibly labeled playback-only and never represented as a live target test. Demo visitors can explore reports, job and sensor comparisons without access to QNX.

## Screen map

- Public: Home, How it works, Demo, Docs, Security/Limitations, Contact, Privacy/Terms.
- Authenticated: Overview, Projects, Targets, New Run, Live Run Detail, Results, Compare, Evidence, AI Analysis, Team, Settings.
- Admin: locally provisioned administrators, access codes/sessions, organization and target approvals, queue health, quotas, audit and retention, AI budgets, error health and backups.
- Responsive desktop and mobile; keyboard navigation, form errors, visible empty/loading/error states; distinguish recorded demo data from live user runs.

## Implementation gates (no phase advances on a failing gate)

**P0. Baseline and threat model**: inventory server, repo, existing native tests, product capabilities, dependencies, DNS/TLS status and deployment impact; create worktree/branch and rollback; document risks. No unreviewed modifications to existing services.

**P1. App foundation**: pinned supported backend dependencies; Django app, PostgreSQL migrations, health/readiness, config separation, env-based settings, static assets, accessibility shell, typed data models. Unit tests and isolated staging deployment.

**P2. Identity and authorization (reopened by approved access decision)**: protected local administrator provisioning/recovery, username/password plus MFA, password changes/session revocation; no signup/email/SMTP. Scoped one-time-display access codes with secure verifier storage, serialized redemption/session limits, immediate revocation, secure browser sessions and organization/project/target/evidence/AI/live permissions. Test PostgreSQL concurrency, expired/revoked/bad codes, authorization and CSRF, background launch revocation, anonymous denial and JavaScript-disabled browser behavior. Preserve historical authors/audit/evidence through safe migrations. Use OWASP ASVS 5.0 Level 2 as a checklist where applicable, not a claimed certification.

**P3. Real engine integration**: fixed command adapters, target capability inventory, policy/allowlists, run-id mapping, durable job states, bounded subprocess execution, exact recovery; real QNX staging tests prove existing engine still works. No arbitrary external-service lifecycle support.

**P4. Dashboard**: projects, targets, run creation, history/detail, canonical verdict rendering, timeline, compare and offline report. Test browser accessibility, narrow widths, JS-disabled fallback, run loss, empty and partial states.

**P5. Evidence and team sharing**: immutable bundles and manifests, retention/export, access-restricted downloads with safe Content-Disposition, no traversal/symlink escapes, integrity checks, audit. Secure sharing only with explicit organization authorization.

**P6. AI analysis**: opt-in real provider integration, strict evidence retrieval, server-side citation of native event references, prompt-injection handling, redaction, cost caps, graceful disabled/failing provider behavior, no mutation. Test real provider only after local key has been configured by operator securely; mock tests are not provider proof.

**P7. Real-user external target story**: clearly define and implement secure customer target onboarding/agent architecture if offered. If full external lifecycle testing is a launch requirement, implement per-service adapter and live QNX pending/unblock/identity observers; prove it on an external real service, including cancellation, reaping, health and source-fixed replay. Until then publish only the truthful supported scope, with UNSUPPORTED for unavailable cases.

**P8. Production hardening**: HTTPS and HSTS, host/domain/CSRF settings, secrets permissions, audit and error reporting, bounded uploads, malware-safe handling, PostgreSQL backup and restore drill, retention, migrations, queue saturation, process containment, rate limits, deployment rollback, strict dependency scanning. Validate staging with real browser + QNX use cases and avoid disrupting other VPS apps.

**P9. Release acceptance**: clean checkout and install; complete end-to-end tests for two real QNX fixtures, demo playback, multi-tenant isolation, timeouts, SSH loss, retries/dedupe, deterministic verdicts, evidence integrity, AI disabled and, when explicitly configured, real-provider-enabled operation (never infer provider proof), verified source-fix replay, responsive browser, rollback; independent operator UAT. Record exact commands, PASS/FAIL/NOT_RUN and blockers. No universal compatibility claim.

**P10. Production deployment**: after all relevant gates, configure DNS `qnx-resmgrcheck.gestionatech.de`, Nginx vhost, valid TLS, systemd services, isolated database and users, backups and monitoring; verify public HTTPS externally, account lifecycle, real run authorized through restricted executor, error logs, isolation and safe recovery. Production deployment is not "complete" until the externally reachable site and actual end-to-end operations are observed. Keep Devpost submission separate and never submit without explicit approval.

## Production release blocker checklist

- No insecure direct object references / cross-tenant leakage, including AI, tasks, exports and download URLs.
- No arbitrary shell command execution, target host switching or unapproved QNX fixture actions from web input.
- No public SSH to QNX guest; no SDK license state or root execution exposed to web workers.
- No fake results or seeded example counts presented as live traffic. Playback-only demo is clearly marked.
- If AI is disabled/unreachable, every existing test and deterministic report still works.
- Existing CLI remains available and native regression passes; original hackathon commit stays recoverable.
- Original evidence unchanged, and full production release has commit+build manifest, backup, runbook and rollback proof.
- Test exposed hostname from outside the VPS, not just localhost.
- Do not assert "100% ready" from host tests alone. Provide a verified acceptance matrix and identify any remaining unsupported customer workflows.

## Agent operating contract

Work from `feature/production-web-ai`, preserve commits and evidence; commit checkpoints after each verified gate. Continue autonomously through implementation and staging. Do not ask owner for routine design approvals. Ask only for material external/account actions impossible without user participation, and never request passwords, tokens, `.env` or protected configs in chat. Do not change existing domain DNS, expose services, or deploy production until preflight and readiness gates pass; the owner has requested production at the stated hostname, so complete the release once verified safe within this authorization. Do not submit Devpost or change the published hackathon video as an incidental task.

Maintain `docs/web/STATUS.md`, `docs/web/ARCHITECTURE.md`, `docs/web/SECURITY.md`, `docs/web/TEST_EVIDENCE.md`, `docs/web/DEPLOYMENT.md` and `docs/web/OPERATIONS.md` with observed results, current revision, remaining limitations, next action and rollback.

Always distinguish:
(a) actually running production web features,
(b) QNX native features actually verified,
(c) AI provider functionality actually verified,
(d) demos/replays from recorded evidence, and
(e) features not yet supported.

Security review baseline: https://asvs.owasp.org/ and https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html
