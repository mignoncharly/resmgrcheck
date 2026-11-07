# Web architecture

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

ACCESS_MODEL.md records the approved replacement decision. PostgreSQL serializes
code redemption and fences revocation against local child creation. Run/source/AI
rows bind exactly one administrator or code-session identity; legacy authors/audit
remain preserved. Browser sessions use opaque cookies with revocation/idle/absolute
limits, not repeatedly transmitted raw codes or API bearer credentials.
