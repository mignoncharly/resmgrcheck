# Web architecture

W015 stages an outbound customer runner alongside the private lab dispatcher,
disabled by default. Customer SSH/QNX configuration stays local. HTTPS validates
the central origin; pinned Ed25519 keys authenticate both directions.600s one-use
enrollment binds a device key to a preselected organization/project/target, followed
by separate MFA administrator approval of its exact inventory. Unique nonces and
60s freshness prevent request replay. Local route fingerprints and PG guards fence
silent route/key/tenant substitution. Connection is distinct from lifecycle proof.
Job delivery/ingestion are the next checkpoint; enrollment grants no native command.
The original engine/CLI/evaluator remain unchanged.

The [contract](PRODUCTION_IMPLEMENTATION_CONTRACT.md) supersedes the original
CLI-only scope for this branch. The native engine, CLI and evaluator remain intact.

The public control plane is Django 5.2 LTS on Python 3.12, server-rendered HTML,
PostgreSQL and a dedicated Gunicorn service behind Nginx. Optional browser behavior
enhances server-rendered states. No frontend framework or duplicate evaluator.

The P4 dashboard renders original engine obligations, event references and observed
monotonic offsets through the canonical bundle verifier. All20 recorded reconnect
cycles remain visible. Required-evidence corruption withholds a passing conclusion
and the derived report. Inline offline HTML uses a script-disabled sandbox/CSP;
raw downloads are authenticated and tenant scoped. Public playback is a fixed
allowlist of genuine saved QNX evidence, isolated from the execution queue.

Administrator organization/project membership and access-code project/target/evidence
grants scope every object lookup, download, comparison and AI retrieval. Developer
sessions create no user accounts; only locally provisioned administrators have
username/password/MFA credentials. There is no email/SMTP workflow. UUIDs are identifiers, never authorization. Delayed jobs recheck
current user membership, project, target and immutable build approval before use.
The database is the durable queue: explicit transitions, locks, leases, idempotency
and target quarantine. A stale lease permits status/collection, never blind relaunch.

The private execution plane invokes only fixed CLI argument vectors in the pinned
engine checkout. Server-managed allowlists map target/build UUIDs to approved local
configuration; browsers cannot choose hostnames, SSH commands or executable paths.
Original target run IDs, evidence seals, verdicts and candidate identities survive
collection. Cancellation intent is separate from observed native termination.

Production uses separate nonroot web/executor accounts. Only the executor can read
the fixed QNX route credential; no public web process can read SDK authentication or
SSH keys. Builds are operator-approved offline inputs; the internet cannot trigger
qcc or arbitrary source execution. Deployment must establish OS isolation before
production acceptance. Current staging under the development user is not that proof.

AI is optional, explicitly consented, quota-bound and limited to selected tenant
evidence/source. It cannot execute tools, deploy patches or mutate canonical results.
Provider absence/failure leaves deterministic testing/reporting available.

The P6 implementation separates the AI worker from the HTTP process and native
executor. HTTP records signed exact-preview consent and a transactional cost
reservation; only the private AI worker reads its dedicated provider credential.
The fixed stateless Responses adapter runs in a bounded owned child, with no QNX
credential in argv/environment, tools or inherited proxy configuration. Dedicated
OS/filesystem isolation remains a P8 production requirement. Immutable input/output hashes,
native reference IDs, provider/model/usage provenance and uncertain-call records
remain distinct from Run verdicts. See AI.md for egress, bounds and retention.
Actual provider qualification is pending dedicated local configuration; host mocks
and disabled-browser checks do not establish provider access or successful output.

Customer targets require an approved dedicated runner/route for that tenant.
This release will not accept arbitrary shared-host SSH or claim external lifecycle
observers that do not exist. Public demo uses isolated recorded evidence only.
The implemented approval/request boundary and precise limitations are documented
in [CUSTOMER_TARGETS.md](CUSTOMER_TARGETS.md); approval is a protected local action.

ACCESS_MODEL.md records the approved replacement decision. PostgreSQL serializes
code redemption and fences revocation against local child creation. Run/source/AI
rows bind exactly one administrator or code-session identity; legacy authors/audit
remain preserved. Browser sessions use opaque cookies with revocation/idle/absolute
limits, not repeatedly transmitted raw codes or API bearer credentials.

P8 preparation separates production configuration into web/executor/AI/operator/
backup roles. HTTP receives neither registry nor provider settings and refuses
private dispatcher commands; only its role can expose WSGI. Nonroot services receive
only required systemd credentials. The fixed root-owned engine checkout has an
explicit Git safe-directory binding and private state location, preserving real
evaluator source identity. A verified owned-file read-sharing step preserves sealed
bytes and owner-write state while giving only the evidence group read access.

Encrypted backups use a synchronized PostgreSQL snapshot and a shared advisory
lock that excludes local retention until artifact copying completes. Authenticated
stream encryption and an exact isolated restore drill preserve native hashes/audit.
The backup DB role is SELECT-only; protected local wrappers retain root only for
key custody/peer authentication and are contained with no capabilities/home/IP
network. These service/OS claims are intended configuration and require the pending
actual root qualification; staging tests are not that proof. See PRIVATE_INSTALL.md.
