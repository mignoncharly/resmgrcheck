# Web architecture

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. W028: immutable application `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`
is active. Production password/code/browser acceptance passed; an independent
external public fetch returned HTTPS 200. Native execution is BLOCKED by the missing
approved executor registry; independent authenticated acceptance remains pending.
P8 is IN PROGRESS. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

W015 stages an outbound customer runner alongside the private lab dispatcher,
disabled by default. Customer SSH/QNX configuration stays local. HTTPS validates
the central origin; pinned Ed25519 keys authenticate both directions.600s one-use
enrollment binds a device key to a preselected organization/project/target, followed
by separate password-authenticated administrator approval of its exact inventory. Unique nonces and
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
username/password credentials (MFA deferred). There is no email/SMTP workflow. UUIDs are identifiers, never authorization. Delayed jobs recheck
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

## W016 — staged runner job and evidence route (2026-11-09)

W016 supersedes W015's pending job route: signed polls bind one runner/target, immutable job/ticket/intent, build, organization/project and original native ID. One launch grant follows current authority checks and cannot be reissued/reset. A local fsynced intent precedes the grant; uncertainty selects same-ID collect. Interrupted uploads reuse an immutable local archive and per-chunk acknowledgement journal. Authenticated128KiB chunks are bounded to64MiB/job and256MiB outstanding. HTTP stores them in PostgreSQL only. The existing private executor validates canonical contracts/build/target/replay/native seals, publishes without replacement and creates the immutable evidence graph. Invalid/incomplete evidence or unobserved cleanup quarantines. Connection and upload alone never establish PASS or cleanup.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 observed execution route

The staged outbound design now has actual QNX observations: browser-approved jobs
traverse authenticated loopback HTTPS to a separate runner process and the approved
QNX VM, then return through bounded upload/private ingestion. A real interrupted
upload resumed the same immutable native ID. The central HTTP identity never used
customer SSH material. This topology remains on one VPS; it cannot qualify network
separation, a customer's licensed environment or the intended public origin. The
mailbox adapter follows the same registry/supervisor/evaluator path as sensor/job.

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

## W021 single-command jury HTTPS rollout (2026-11-09)

The active private application is now544f22c, operator-confirmed runtime/readiness/
backup/isolated restore/audit proof. No source update to that immutable release is
needed by this correction. A route-wide review and72 administrator/code/machine
regressions passed; no genuine application authorization gap was confirmed. The
HTTPS candidate is finalized with error-response headers, preserved evidence CSP,
POST-only auth/MFA limits, raw peer-IP identity, no proxy cache/buffering, private
logging and persistent HTTP ACME. Only exact dedicated site/http settings and its
lineage-guarded renewal hook may change, after protected backup, strict file/key/
unit/release validation and nginx -t. Unknown resources/edits are refused.

The operator-run workflow includes an actual own-config rollback/reapply drill,
bounded trusted-TLS checks, one-certificate Certbot dry-run, temporary audited
administrator/code browser journeys as a nonroot process, cleanup and existing-
approved-lab native acceptance when possible. It never invents target approval,
copies SSH keys, changes existing user passwords/MFA, patches current, rewrites
historical evidence or modifies another site/service. Interrupted test identities
are reconciled using protected intents plus append-only creation audit. Public/
native/independent gates remain pending until their real observations exist.

All342 web regression tests passed in89.677s. The focused command/rollback suite
passed13 cases, including actual owned process-group timeout cleanup; four actual
isolated Nginx/TLS/Unix-proxy cases passed, including spoofed forwarding,502/413/429
headers and strict TLS rejection. The full browser-driver rehearsal passed44 views/
12 zero-violation Axe scans in162.971s with actual Django/PG and private fixture TLS.
Its native status remains BLOCKED/no execution and overall production acceptance
false. These results are not root production or independent public qualification.

Both an ordinary verified curl and independent Firecrawl fetch still fail public
TLS before deployment (hostname mismatch / remote SSL error), with no target HTTP
status or verification bypass. A valid dedicated certificate existing on disk is
operator-provided; it is not yet served by the HTTP-only vhost. The one privileged
command awaits the operator; the agent ran no deployment/reload. See
[HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md) and evidence/https-rollout. Customer
endpoints remain disabled until a separate customer host is qualified. AI stays
disabled; off-server DR is deferred. Independent existing-admin UAT is NOT_RUN.

## W024 graceful reload and strict rollback verification

The HTTPS deployment driver treats nginx reload as signal delivery, not proof
that replacement workers are serving. Configuration identity/modes/link and actual
HTTP404/ACME behavior independently qualify restoration. Bounded verified-TLS probes
qualify reactivation. Status-only observations distinguish the drill from final
failure cleanup; failed or uncertain verification never becomes a readiness claim.
Application544f22c, database, executor and evidence architecture are unchanged.

## W025 Unix proxy identity and immutable authentication recovery

Nginx supplies the original client address through an overwritten X-Real-IP header
over the private Unix listener. Gunicorn's Unix REMOTE_ADDR is empty. Allauth must
explicitly consume the supported trusted-header setting in production for rate
limits and session metadata; forwarded chains remain stripped. Missing/invalid
addresses fail closed. Fixtures must model empty Unix peer identity, alongside
real Gunicorn transport tests, rather than inventing a loopback peer. A one-setting
correction is deployed as a new immutable application with a separate static tree;
existing root-owned runtime configuration remains unchanged. The application does
not serve static files; the reviewed Nginx alias selects the new tree.

## W026 password-only administrators and preserved recovery state

Administrator assurance is a release policy independent of project/target/code
permissions. ADMIN_MFA_REQUIRED=False selects password freshness and suppresses
allauth MFA challenges without uninstalling its app/schema or deleting authenticators.
The explicit future true path is retained/tested but requires reviewed reactivation.
Session clocks/revocation and durable worker checks stay independent. Existing
immutable mfa_at fields retain their schema and now carry current-policy assurance
time; no historical record is relabelled as an MFA result.

Qualification now uses actual Gunicorn/Unix transport with Nginx TLS and Django/PG.
Actual systemd runtime/isolation still requires operator execution. Root operation
launchers prevent bytecode writes even with -I; original source identity validation
separately verifies retained derived caches before immutable pointer activation.

## W028 deployed control-plane qualification

Application3f4bafb is active behind dedicated HTTPS Nginx, Unix-socket Gunicorn and
the preserved nonroot systemd/private database boundary. Production password/code/
browser acceptance passed; independent public landing retrieval returned HTTPS200.
The executor remains a separate privileged-custody boundary: absent approved registry
means no native execution, regardless of successful web login or recorded playback.
This checkpoint does not add routes/grants/credentials or change architecture.
Customer machine endpoints and AI remain disabled. Actual production native,
independent authenticated UAT and separate-host customer qualification remain open.

## W029 fixed production executor custody

The [executor qualification workflow](PRODUCTION_EXECUTOR.md) registers exactly one
operator-owned lab organization/project/target and two immutable before/after builds.
The public application remains3f4bafb; no host/SSH/executable selector enters browser
authority. Private route/key copies remain within resmgr-exec custody and its existing
systemd loopback/filesystem/credential boundaries. No SDK/license access is granted.

Authorization-row locking gains narrowly scoped UPDATE(id) permission plus invoker
triggers denying all actual executor updates; shared code is unchanged. A service-
context probe gates approval, followed by three real dashboard cases. These production
steps are prepared, not executed.74 tests passed; native outcomes and independent UAT
remain unverified. AI/customer endpoints stay disabled; P8 is IN_PROGRESS.
