# Production web test evidence

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

## W015 — current inventory and outbound runner enrollment (2026-11-09)

The operator confirms actual private HTTP200, nonroot systemd runtime_check and
the encrypted isolated restore (audit UPDATE/DELETE rejection) on immutable3821952.
Read-only current-pointer and unit metadata corroborate that release and active
web/socket/database; executor and backup timer were inactive. These facts supersede
W014's pending production restore, without rerunning successful work or relabeling
operator evidence. Public HTTPS could not be fetched externally; no HTTP/TLS,
browser/public-native or independent acceptance is claimed. No root action ran.

Enrollment implements600s256-bit one-use HMAC-verifier credentials, exact tenant/
target/device binding, separate administrator inventory approval, permanent
revocation, signed Ed25519 HTTPS exchange,60s freshness, nonce replay protection,
bounded rates, local route pinning, and disconnected/incompatible/quarantine states.
Machine endpoints reject cookies and arbitrary fields; administrator endpoints
retain MFA/CSRF/tenant checks. PostgreSQL guards reject identity/tenant changes.
The old lab worker excludes customer targets. Native execution remains explicitly
unavailable in this enrollment checkpoint; no SSH/SDK configuration reaches HTTP.

68 focused tests passed in8.989s:18 runner enrollment/auth/tenant/PG tests, three
actual loopback TLS client/Django journeys and47 retained scheduling/credential/
production-config tests. TLS tests enrolled, approved, heartbeated and revoked a
runner over a real encrypted connection, refused an untrusted certificate/wrong
server signing key, and tested private-file protections. Discovery was a fixture;
this is neither separate-customer-host onboarding nor a new QNX observation.
The earlier65-test run passed before TLS journeys were added. Disposable test DB
migrations applied through0018 and the test DB was destroyed. A makemigrations
invocation initially warned that its default DB history could not be checked in
the sandbox; subsequent tests applied real migrations in the dedicated development
cluster, without production access or guard relaxation.

Enrollment is disabled by default. The new signing seed is separate from existing
application/MFA/backup keys and uses the strict existing credential validator.
No production key, schema, unit, service, Nginx site, QNX process or original native
evidence changed. The owner confirms no separate customer runner is currently
available; staging may continue, separate-host native/public/independent review
remain gates. Job delivery/ingestion, an additional meaningful native integration,
immutable migration/rollback and full A–F acceptance remain outstanding. AI remains
disabled. Off-server DR automation is deferred, never counted as passed.

Current access decision: [DWEB-001](ACCESS_MODEL.md) replaces the former public
registration/email/SMTP requirements. W002 and prior email references below are
historical, preserved observations; W007 qualifies the revised model. AI is optional;
provider-disabled qualification does not establish real provider functionality.

## W000 — P0 baseline and read-only inventory

2026-11-07. Specification commit3d9048a, published baselineca4f74e. Working tree
was clean when checked out. Remote fetch was explicitly scoped to the requested
branch; the original single-branch refspec did not initially contain it.
Original engine fingerprint remains02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b.

[Sanitized inventory](evidence/p0/inventory.json) records the actual host findings.
47 running service units and12 enabled Nginx sites were inventoried without dumping
protected configuration. Existing PostgreSQL clusters were preserved. The account
is nonroot; noninteractive sudo requires a password. Existing PostgreSQL role is
not superuser and cannot create databases. Requested DNS did not resolve. No
matching Nginx vhost exists. No production changes were made.

The installed SDP was sourced normally; actual qcc discovery reported GCC12.2.0
gcc_ntox86_64. Read-only SSH to the existing guest returned QNX8.0.0/x86pc and UID0.
Guest data space:415 free entries,2992 free4096-byte blocks. This is capability/
storage inventory, not a new lifecycle execution claim. [All107 baseline host tests](evidence/p0/engine-host-tests.txt) passed in13.872
seconds; no unchanged native matrix was repeated.

Supported dependency candidates were checked against official Django/allauth docs
and PyPI, with [version metadata](evidence/p0/dependency-selection.json). Actual
installation/lock, audit and compatibility tests are P1 work. Django5.2 LTS is
listed supported through April2028 by https://www.djangoproject.com/download/.
MFA integration follows https://docs.allauth.org/en/latest/mfa/introduction.html.

P0 passes inventory/threat-model readiness with explicit downstream production
blockers. P1–P10 are not passed by this record. No AI provider or public HTTPS result
is claimed. See SECURITY, DEPLOYMENT and OPERATIONS for constraints and rollback.

## W001 — P1 foundation

Django5.2.19, allauth65.21.1 and psycopg3.3.8 installed in the private web virtualenv;
all15 installed/transitive Linux x86_64/Python3.12 wheels are exact-version/hash
pinned in web/requirements.lock. Native CLI dependencies/source remain unchanged.
Real PostgreSQL16 staging was initialized in ignored .local/web/pgdata with
listen_addresses empty, peer auth over a private0700 socket directory, port5438
within that directory. No existing database/cluster/service was altered.

Actual commands used web/ops/staging.py to run manage.py makemigrations control,
migrate --noinput, createcachetable, check, and test tests.test_foundation --noinput.
[All four tests](evidence/p1/tests.txt) passed against a separately created/destroyed
PostgreSQL test database. Identity case-fold uniqueness, Argon2 hashing, real scoped
records, empty initial data, liveness/readiness and HTTP method restrictions passed.
[Migrations/checks](evidence/p1/migrations.txt) succeeded with zero system issues.

An actual one-worker/two-thread Gunicorn was started at127.0.0.1:8431;
[readiness](evidence/p1/staging-health.json) returnedHTTP200 and the actual database
SELECT passed. It is isolated private staging under the development user, not a
public or production OS-isolation result. No seed activity or mock target exists.
Root provisioning, DNS, production mail and operator UAT remain downstream blockers.
P1 passed; secure account/tenant policies are P2 work, not asserted from foundation.

## W002 — P2 identity and authorization

[All34 PostgreSQL-backed foundation/identity tests](evidence/p2/tests.txt) passed
in6.572s. Actual allauth request flows verified signup, POST-only email confirmation,
invalid confirmation rejection, password reset, explicit password reauthentication,
TOTP enrollment with encrypted secret/recovery codes, actual second-factor login
and step-up before first organization creation. Test mail uses Django's isolated
outbox; this proves the protocol, not external SMTP delivery. Staging mail files
remain private; production mail is an explicit external configuration requirement.

Negative cases deny anonymous/unverified access, MFA enrollment without authenticated
session assurance, expired assurance, cross-tenant project/API/team/audit access,
viewer mutation, missing CSRF, cross-tenant assignment and overprivileged project
roles. Last-owner removal and admin-to-owner promotion are denied. Revocation
affects only that organization and is checked immediately; unrelated tenant access
remains valid. Password-confirmed logout-all invalidates session hashes globally.
Account export excludes passwords/MFA/session material and other users; sole-owner
deletion is blocked, eligible deletion disables access and schedules retention.

PostgreSQL trigger rejects audit UPDATE/DELETE. Logs use safe actions/object IDs,
not credentials. Shared database rate buckets and security headers are tested.
TOTP/recovery secrets use the separate0600 private Fernet key through the installed
allauth adapter; privileged owners/admins cannot remove required MFA.

Initial tests found one real session-revocation bug (request.user is lazy, not a
model class); the concrete User manager fix passed. Follow-up flow assertions were
corrected to allauth's actual stronger behavior: explicit enrollment reauthentication
and404 for invalid email confirmation. No security control was relaxed. Original
failed logs remain private under .local/web/evidence.

P2 passed the protocol/negative gate. Actual production SMTP, OS isolation and public
HTTPS remain NOT_RUN/downstream blockers. No live QNX job has been launched through
this foundation yet; P3 must prove it. No AI provider functionality is asserted.

## W003 — P3 real engine integration

[All55 PG/host tests](evidence/p3/host-tests.txt) passed in9.004s. Cases cover
intent-bound deduplication, queue quotas, serialized leases, expired-lease same-ID
recovery, worker permission/password/session reauthorization, tenant-bound targets,
immutable PostgreSQL run intents, signed preview confirmation, unsupported external
lifecycle, unknown capabilities, target-request mass-assignment rejection, exact
owned local process bounds/output/reaping, including callback failure containment.
No target result is fabricated by those host tests.

The actual CLI is a frozen ca4f74e worktree under .local/web/engine. Existing actual
QNX binaries, original deploymentd9d2a1a and source-corrected39b99d7 were reused.
No native C/build/evaluator change or reinstallation. The executor uses fixed argv,
a private0600 target/build registry, bounded subprocess resources and exact run IDs.
Public request handlers enqueue only; target commands occur in separate private
management workers. Production account/OS isolation is still a downstream gate.

[Actual HTTP qualification](evidence/p3/native-http.json): real loopback HTTP forms,
CSRF, real password/TOTP login, DB queue, private dispatcher and actual QNX produced
sensor fixed PASS, explicit ignore-unblock FAIL, unchanged-setting candidate replay
PASS/fixed, and job fixed PASS. Reposting the same signed request returned the same
job. Native bundle/build/fixture/runner/worker hashes are retained. Every case has
observed native cleanup and a reaped local CLI child. This used a local operator-
provisioned private acceptance identity, not an externally mail-verified customer.

Actual doctor target/architecture/SSH/SFTP/compiled-capability checks passed. Its
overall exit remained2: SDK ERROR/compiler UNKNOWN in the deliberately restricted
executor environment. Runtime target reachability is recorded separately; no doctor
PASS or private service-instance capability is inferred. No qcc process runs from
a public web request. Builds are operator-approved offline inputs.

[Actual connection-loss recovery](evidence/p3/recovery.json): confirmed the timed
worker's native pending event, then SIGSTOP only the exact owned local collection
SSH child (pidfd plus verified ancestry). The existing transport deadline killed/
reaped it. Initial job remained launch_uncertain with ERROR/partial evidence; no
cleanup PASS. After actual30-second lease expiry, the private worker collected the
same run ID and same supervisor, never relaunched. Original partial bytes and the
transport incident remained. Final canonical service FAIL retains both independent
cancellation reasons; native cleanup was separately observed. This adds one actual
QNX case, bringing the staging exercise to five native cases.

[Actual SFTP failure](evidence/p3/transfer-failure.json): killed only a verified owned
SSH child of the active readback SCP process. Parent SCP/CLI exit was observed.
Canonical exit2 and all required cases NOT_RUN were preserved. Normal CLI exit plus
bound finalized state before any native launch intent established no native launch;
no native cleanup was claimed. Slot was released, target marked unavailable, and
there was no automatic retry. This is real failed transport, not another native
service execution or simulated test result.

Gunicorn26's default per-user control socket was discovered during staging and
disabled in the dedicated configuration. Only this task's verified Gunicorn master
was stopped/restarted; unrelated services were untouched. The default socket was
observed gone. Production must use the dedicated configuration and service accounts.

Source [observation](evidence/p3/source-observation.json) records gate-close WIP
web files over49e9690. Initial four-case batch preceded recovery/failure-path fixes;
it is not relabelled clean final-web execution. All actual native source identities
are unchanged in sealed bundles. P9 final clean release qualification is NOT_RUN.
Raw private web acceptance/transport evidence is preserved under .local/web, not
made public as customer activity. These sanitized indexes contain no credentials.
P3 passes private staging integration; SMTP, public HTTPS, dedicated production OS
isolation and optional real AI provider remain unverified/downstream gates.

## W004 — P4 dashboard

Private staging source over7a3d030. [All64 PG-backed host tests](evidence/p4/host-tests.txt)
passed in16.494s, including genuine archived six-case lifecycle/20-cycle rendering,
unaltered native FAIL obligations/event references, source-fixed comparison,
cross-tenant denial, public playback without enqueue, invalid identifiers and
tampered required evidence withholding PASS and the derived HTML report.

[Actual Chromium qualification](evidence/p4/browser.json) passed104 HTTP browser
views:1440/390px with JavaScript and1280/390px without JavaScript. All26 desktop
pages were scanned by axe-core; no serious/critical WCAG2A/AA/2.1AA findings.
Native disclosure keyboard activation and exact event anchors passed. No page
overflow, browser errors or external network requests were observed. Fourteen
private screenshots were retained; desktop overview/mobile failed-run views were
visually inspected. This is Chromium qualification, not assistive-technology or
all-browser certification. No screenshot includes credentials or MFA inputs.

[Actual UI state qualification](evidence/p4/states.json) added four queued views
across desktop/mobile/JS-disabled modes, actual field errors and a dedicated-runner
request shown UNSUPPORTED. Browser POST recorded cancellation intent; the separate
dispatcher then observed that exact queued identity as cancelled_before_launch.
No CLI/native process started and no cleanup was claimed. This is not another
native case. The unsupported customer request did not connect to any host.

Checks found and corrected narrow-grid overflow, insufficient accent contrast,
text-link underlining and the installed-allauth template override precedence.
Two earlier host runs exposed only a test client stream-close/database-transaction
interaction; consuming its wrapped stream fixed the test without weakening the
production integrity checks. A queued-inventory browser assertion was corrected
to its distinct factual inventory label. Earlier private logs are retained.

Dashboard counts are actual authorized requests, not seeded traffic. Partial demo
uses the preserved initial P3 transport-loss summary and states no final native
bundle existed. Fixed/broken/job playback uses original Phase10 evidence. Native
engine/build/evaluator files are unchanged; no expensive QNX matrix was repeated.
P4 passes private staging; P5–P10, SMTP delivery and production deployment remain
separate outstanding work. The code will receive a clean-release qualification
at P9; this WIP evidence does not pretend to be that final revision.

## W005 — P5 evidence and authorized sharing

Source over3a33c78. [All82 PostgreSQL-backed host tests](evidence/p5/host-tests.txt)
passed in20.734s. A final focused27-test run after tightening retention against the
original cleanup observations passed in12.409s. Tests cover actual sealed native
bytes, inventory graph closure/immutability enforced by PostgreSQL, traversal,
symlink/hardlink rejection, hash corruption, status API withholding stale PASS,
tenant denial for exports/policy/holds, offline references, exact owned dry-run/apply
retention, unknown-file refusal, replay dependencies, policy bounds, hold audit,
due-only account personal-data erasure and pseudonymous audit preservation.

[Actual HTTP/export qualification](evidence/p5/browser.json) downloaded five real
private staging collections: sensor fixed, broken/recovered, source replay, job and
failed-transfer NOT_RUN. All package hashes/identities verified. Ten offline
Chromium views passed (1440px/JS and390px/no-JS);209 local references resolved,
no external requests or page overflow. These are genuine previously executed
QNX collections, not five new native executions. The recovered package retains
its exact earlier partial bytes and summary alongside the final FAIL result.

[Six exact existing collection inventories](evidence/p5/inventories.jsonl) were
extended with a v2 web inventory. Five contain real QNX cases; one is the actual
failed-transfer/no-native-launch collection. Original v1 marker/native bundle
bytes were verified and preserved. No target command, build or service change.
Downloads are project-member authorized and audited, with a literal UUID filename;
there is no anonymous/private-link sharing bypass. ZIPs contain original evidence,
manifests, report, SHA256SUMS and offline/verdict explanations, never SDK/executables,
SSH configuration or diagnostic command logs.

Earlier tests correctly stopped retention on the collector's redundant
cases/CASE/events.jsonl file. Only after verifying its exact creation in
resmgrcheck.workflow.collect_case was that exact known auxiliary name admitted.
Unknown directories/files still stop removal before mutation. A real PostgreSQL
nullable-join row-lock error in the local inventory command was corrected with
select_for_update(of=('self',)); six actual collections then verified. Public
test logs retain truthful results; private failed attempts are not erased.

`check --deploy` on intentional loopback HTTP staging reported four expected
HSTS/HTTPS/secure-cookie warnings. They are not suppressed or represented as a
production pass. Secure production settings/HTTPS/OS separation, backup restore,
SMTP delivery and real AI provider remain downstream unverified requirements.
P5 passes local evidence/sharing/retention qualification, not hardware WORM storage
or third-party security certification. Raw packages/screenshots remain private.

## W006 — P6 implementation; real provider gate pending

Source over6169f7e. [All117 PG-backed web host tests](evidence/p6/host-tests.txt)
passed in32.821s. A final focused74-test run after queued-cancel/source-erasure
and replay/retention locking changes passed in19.938s. AI tests use explicitly
labelled mock responses: they prove consent/authorization/schema/cost/protocol
behavior, not a real model response. They cover exact signed-preview consent,
deduplication without respend, model-policy changes, zero/stale/insufficient budgets,
cross-tenant/source/viewer denial, source/private-key/SDK/binary/upload bounds,
best-effort redaction, prompt text remaining untrusted, unknown citations and
verdict-field refusal, required uncertainty/source/comparison references, escaped
output, provider401/403/429/500/incomplete/refusal/oversize/malformed handling,
revocation before dispatch, conservative failure reservations, uncertain lease
expiry without reissue, queued-only cancellation, immutable consent/completed
provenance, derivative erasure and no native verdict mutation. A real private child
rejected oversized input before any network request; timeout mapping is host-mocked.

[Actual disabled-provider browser qualification](evidence/p6/disabled-browser.json)
passed16 loopback HTTP views at1440/390px with JavaScript and1280/390px without it.
Four new/affected pages passed axe scans with no serious/critical findings.
An actual original-source upload used only docs/jury/source-fix.patch, already
published original MIT correction; its digest is recorded. Exact redacted preview
and no-provider state were observed, with no external network requests/provider
calls. The deterministic report stayed available. This does not prove AI output.

[Two actual current-web native cases](evidence/p6/no-ai-native.json) passed on the
existing QNX guest with AI unavailable: sensor fixed timeout and job fixed timeout.
Real HTTP/CSRF/password/TOTP forms queued exact IDs; duplicate POST deduped, the
separate dispatcher invoked the existing engine, both canonical outcomes were PASS,
native cleanup and host CLI exit/reaping were observed, and new v2 inventories
verified. This specifically requalifies the changed web sealing/integration path,
not the unchanged36-expectation native release matrix. Total actual web staging
native cases so far:seven (P3 five plus these two); failed-transfer/inventory/
queued cancellation and archived playback do not inflate that count.

The packet-bound test initially withheld a full before/after packet. Repeated
assertion observed objects were replaced by explicit excerpts plus exact cited
observations and a disclosure; the24000-byte bound remains enforced. Original
canonical evidence is unchanged and linked. A job test expectation was corrected
to its actual versioned adapter ID job-v1. Browser checks corrected the shared
manifest upload wording for source review. Record#0 references now disclose the
actual target run manifest rather than pointing to a nonexistent producer event;
a dedicated host check verifies every native reference has a disclosure target.

The implemented real OpenAI adapter follows the official Responses/structured-output
and data-control documents linked in AI.md. No endpoint/model/key is borrowed or
fabricated. The operator has agreed to configure dedicated AI and SMTP locally;
the files/values were not yet present at this observation. `qualify_ai_provider.py`
is prepared for four actual consented requests after secure local configuration.
Real provider/account/cost/interpretation verification remains **NOT_RUN**. P6 is
**IN PROGRESS**, and P7–P10 have not advanced. Same-user private staging is not
production OS isolation, public HTTPS or independent operator UAT. No original
native C/evaluator/profile/Makefile or sealed historical evidence was changed.

A later read-only [hostname observation](evidence/p6/hostname.json) found DNS now
resolves (P0's earlier NXDOMAIN observation remains historical). No matching
enabled Nginx vhost was found; an HTTPS health request did not verify. This task
made no DNS/vhost changes and does not infer an application deployment from DNS.

[Checkpoint publication](evidence/p6/publication.json) verifies a6db2f5 on the
authorized feature branch and unchanged ca4f74e on main/implementation/phase-1.
The GitHub connector retrieved the matching commit. The public change review
covered144 changed text files, with no literal credential/private-key/executable
pattern finding. This is a scoped source review, not an independent penetration
test or production security acceptance. Host-only GitHub workflow status was not
established by the connector's PR-only query; no CI/native claim is inferred.

P6 staging preservation also performed a real encrypted checkpoint/isolated restore.
[Sanitized receipt](evidence/p6/checkpoint-restore.json): database counts/inventory
identity matched, the restored audit trigger denied updates,140 artifact hashes and
eight collected executions verified. The exact temporary restore DB was dropped;
the original stage DB/evidence were preserved. This made no QNX/provider call.
Seven of those records contain QNX cases; the failed-transfer record contains none.
This does not pass the later production backup/account/off-host/key-custody gate.

A P6 API review found that the provider defaults its processing tier to the account's
project setting. The adapter now explicitly requests standard/default pricing and
withholds a missing/different returned tier. [All36 focused AI host tests](evidence/p6/standard-tier-tests.txt)
passed in12.281s after this change; actual provider behavior is still pending
secure local setup.

## W007 — Administrator/access-code replacement gate

Owner-approved DWEB-001,2026-11-07. Observed base58ce0e1 with uncommitted web
changes; [gate-close hashes](evidence/access-v1/source-observation.json) identify
reviewed files, not a clean final-release execution snapshot. Original native/CLI
runtime remains02b34132…; main and the published release remain unchanged.

Before schema changes, an actual encrypted private checkpoint restored into an
exact new temporary database. [Receipt](evidence/access-v1/pre-migration-restore.json):
140 artifact hashes/eight collected execution records and append-only audit trigger
verified, original database/evidence preserved. Seven records are actual native
cases, one a failed-transfer record with no native launch. This is staging
preservation, not production backup-role/off-host/key-custody qualification.

Actual PostgreSQL migrations0013–0017 passed. Legacy authors and audit references
remain; unprovisioned old accounts are disabled, never silently elevated. Explicit
local adoption preserved the existing staging administrator's hash, MFA and author
identity, cleared unused email and revoked sessions. No account/code credential is
published. Old invitations/deletion records are archival; their workflows/tasks
and public email/signup/reset routes are removed. No SMTP dependency remains.

[All135 PostgreSQL tests](evidence/access-v1/host-tests.txt) passed in37.650s through
`web/ops/staging.py manage.py test tests --noinput`. Coverage includes local
Argon2 provisioning, protected recovery, username/password/real TOTP, enrollment,
password/session changes, CSRF/rate limits, anonymous denial, valid/malformed/
expired/revoked codes, opaque session binding, idle/absolute expiry, one-time
secret display/verifier-only storage, no bearer/query authentication, scope edits,
individual/global code revocation, concurrent lifetime and active-session limits,
project/target/evidence/download/compare isolation, prohibited administration,
code AI signed consent/budgets/revocation and exact child-start authorization.
Provider protocol fixtures are host mocks and make no paid API calls. Redaction
includes code secrets even when their URL-safe last character is '-' or '_'.
`makemigrations --check --dry-run`, Python compilation and diff whitespace checks
passed. Two deliberate missing-CSRF requests log403, as expected.

An earlier135-test attempt had134 successes and a test-fixture AttributeError from
using the wrong reverse relation for Membership. Correcting that assertion produced
the final135/135 result; no control or required coverage was relaxed. The private
native support helper also initially fetched a POST-only revoke route to obtain
CSRF (405); it now obtains CSRF from authenticated session settings for such routes.

[Actual Chromium156 browser checks](evidence/access-v1/browser.json) passed36 views
at1440px and390px, including JavaScript disabled. Ten axe scans had zero serious/
critical findings. Real administrator password/TOTP and UI code creation/redemption
ran; third-session denial, individual/session-wide revocation, selected-evidence
and cross-project denial, readonly native/AI denial, obsolete routes404, no external
requests and no horizontal overflow passed. Codes/cookies were held only in memory;
no authenticated browser state or creation-secret screenshot was saved. These are
loopback staging HTTP results, not public HTTPS/cookie deployment qualification.

[Two actual code-authorized QNX cases](evidence/access-v1/native-revocation.json)
passed for sensor/job. The job's actual native pending event was observed before
administrator revocation. Browser access ended while bounded service-owned native
supervision, cleanup and collection completed canonical PASS. Exact local CLI exit
was reaped. A separately queued revoked request was rejected with
`actor_authorization_revoked`, no started_at/output directory, native launch,
native verdict or cleanup claim. Unknown state was not promoted to success.

[Four additional actual QNX cases](evidence/access-v1/native-replay.json) exercised
real administrator/code/CSRF HTTP requests, duplicate-intent dedupe, private queue,
sealed v2 inventory and original engine: fixed sensor PASS, ignore-unblock sensor
FAIL(exit1), source-candidate replay PASS(exit0), fixed job PASS. The replay retained
ignore-unblock and original inputs, selected real source39b99d7/08b20033… against
original d9d2a1a/02b34132…, and canonically compared as `fixed` without fixture-mode
change. The fixture hash changed020e5004…→99a511d8…; shared runner/worker hashes
remained unchanged. All six new native cases have verified cleanup/reaping. Earlier
native matrix results remain intact; this is affected web-authorization qualification,
not a rebuild or repetition of the unchanged complete native matrix.

P2 revised authentication/authorization and affected P3/P5 access gates pass private
staging. P6 qualifies optional-disabled operation: real provider/account/usage remains
NOT_RUN until dedicated local configuration and actual exercise. SMTP is superseded,
not a blocker. P7 customer scope and P8–P10 production isolation/backup/HTTPS/rollback/
independent operator UAT still require their own gates; no public deployment occurred.

## W008 — P7 truthful customer target boundary

Base05078d8; [operator onboarding guide](CUSTOMER_TARGETS.md) documents the actual
request/approval/immutable-build/inventory/code boundary and external limitations.
Local target/build approval now uses the same production-root/private-staging
operator guard as administrator provisioning. No approval HTTP endpoint exists.
[All48 focused PostgreSQL scheduling/access tests](evidence/p7/scope-tests.txt) passed
in10.196s, including injected target fields, unknown required capability, external
lifecycle denial before dispatch, target/code administration denial, cross-project
bindings, queued revocation, code session concurrency and bounded host children.

W007 supplies actual supported managed-fixture native/replay proof; W003 transport
recovery/failure observations and original CLI external-health qualifications are
preserved, not falsely relabelled as new external customer execution. No native code
or supported adapter changed, so no redundant native matrix was repeated. Arbitrary
customer lifecycle/agent onboarding is explicitly UNSUPPORTED and unavailable for
launch. P7 passes this truthful limited scope. P8 hardening is next; no public
service or unrelated VPS configuration changed.

## W009 — P8 staging hardening; actual root gate still pending

Base6447fb0 with uncommitted hardening changes. [Source observation](evidence/p8/source-observation.json)
records gate-close web hashes, not a clean P9 release reproduction. The original
engine runtime still matches02b34132…; no native source, original evidence or release
branch changed. No unchanged QNX matrix/build was repeated; W007's six actual
access-authorized cases and earlier evidence retain their actual source identities.

[All152 PostgreSQL-backed tests](evidence/p8/host-tests.txt) passed in41.031s.
[Eleven focused configuration checks](evidence/p8/focused-config.txt) subsequently
passed in1.068s, including refusal of WSGI exposure by the private executor role. These cover
production protected/no-follow secret files and hostname/origin/path checks,
separate service roles, no HTTP dispatcher/provider credentials, no HTTP-role
private dispatcher/WSGI, safe logging, code/credential redaction inside exceptions,
read-only evidence sharing with unchanged bytes, hardlink refusal, private symlink
boundaries in installation permissions, unexpected deployment-warning refusal,
authenticated encryption tamper/key-mode/link/traversal rejection, actual isolated
PostgreSQL restore, bounded retention/snapshot exclusion and missing-archive receipt
denial. `pip check`, Python compilation, migration drift and diff checks passed.

[Actual PostgreSQL grant checks](evidence/p8/database-grants.json) used four temporary
nonprivileged/nonowner roles and real SET ROLE:22 operations returned42501, including
schema creation, audit rewrite/trigger disable, inappropriate code/administrator,
lease/provider/native-job writes. Evidence SELECT was allowed. The complete test
role/ACL transaction rolled back; no permanent roles/ACL/data changed. This validates
the proposed SQL permissions, not actual production peer mappings/OS identities.

The new streaming AES-256-GCM [snapshot](evidence/p8/backup.json) and
[restore drill](evidence/p8/restore.json) passed against the actual private staging
application:245 artifact hashes,14 collected histories and database identity/audit
trigger verified. Thirteen histories contain actual native cases; one is the real
failed-transfer/no-native-launch record. Only the exact new temporary restore DB
was removed. Original data/evidence remained intact. The encrypted backup hash is
7f5bfc7896a3552cb0f1985c1bc0be1928598461ce16fba75f2e09e5bb38751d.
Archive/key remain ignored/private. This does not qualify production service/
backup-role execution, independent off-host copy/key custody or disaster recovery.
[Local operations status](evidence/p8/operations.json) reported no queued work,
expired lease or quarantine and explicit native health `not_measured`; a fresh
receipt is not represented as restore proof.

[36 developer/public browser views](evidence/p8/access-browser.json) and
[14 additional administrator views](evidence/p8/administrator-browser.json) passed
in actual Chromium156 at1440px/390px, with JavaScript disabled on mobile. Seventeen
axe scans had zero serious/critical findings. Actual administrator password/TOTP,
code creation/redemption/limits/revocation and scope denials were exercised without
persisting raw codes/cookies or secret screenshots. The extra administrator checks
initially found one real keyboard-scroll issue and a500 from the legacy session
page's missing humanize template dependency. The audit table is now keyboard
focusable and the session page uses a dedicated MFA-protected administrator view,
without the obsolete allauth email/manage template. It exposes no session keys and
offers password-confirmed global revocation, which also invalidates queued actor
fingerprints. Both browser failures were corrected and the complete14-view rerun
passed. No accessibility threshold or authorization check was weakened.

The live [OSV audit](evidence/p8/dependency-audit.json) returned no listed
vulnerabilities for all15 exact installed runtime packages on2026-11-07. This is
point-in-time OSV coverage, not absence-of-vulnerability certification. Installed
Nginx accepted the proposed [isolated template check](evidence/p8/nginx-template.json)
using high loopback ports and a disposable syntax-only certificate. The original
privileged-port test reached syntax OK but bind permission was denied. No production
listener/server/reload occurred; temporary test ports were verified closed. No
trusted certificate/public HTTPS verification is claimed.

[Production boundary](evidence/p8/production-boundary.json): actual root preparation,
unit activation/namespace/BPF/peer roles, production backup/restore/off-host custody,
TLS/cookies/CSRF, quotas/retention/rollback and independent P9 UAT remain NOT_RUN.
Read-only systemd verification cannot qualify absent application executable paths.
The process is UID1000 and `sudo -n true` still requires a password. No credentials
were requested or printed. [PRIVATE_INSTALL.md](PRIVATE_INSTALL.md) gives the concrete
next root action and dedicated private resource plan. That preparation starts no
public app/SSH/database listener, touches no Nginx/DNS/TLS/firewall, and starts no
executor/AI/timer. Prepared code is not a claim that those production controls have
actually run. P8 remains IN PROGRESS; P9/P10 do not advance on this evidence. SMTP
is superseded; optional AI is unconfigured, so real provider qualification is NOT_RUN.

## W010 — Private installer clone correction and early recovery

2026-11-08, branch `feature/production-web-ai`, base `4ed4855` plus this correction.
The operator reports running root preparation for full SHA
`4ed4855f7633176baea06f2be53154630a9d4d1f`, failing in clone with Git dubious
ownership, with no release directory/Git metadata left behind. This is operator
evidence, not a root command executed by the agent. The protected log's exact content
and marker content could not be read independently: a narrowly filtered read-only
`sudo -n /usr/bin/python3 -c ...` attempt returned exit1, `sudo: a password is required`.
No passwords/configuration were requested or printed; no privileged installer ran.

[Read-only inventory](evidence/p8/installer-recovery/inventory.json) confirms all
four dedicated users and six groups, root-owned top-level directories, a root-owned
0600 log/marker, role/private/evidence/state directories and empty release parent.
The exact release and `.git`, engine, current pointer, database and static tree are
absent. Protected directory contents remain NOT_READ. [Direct systemctl observation](evidence/p8/installer-recovery/services.txt)
found all nine dedicated units not-found/inactive; Nginx remained active/running and
the host PostgreSQL umbrella active/exited. An initial Python-child systemctl probe
returned1 with no stdout in the sandbox; the direct read-only command succeeded.
No service/account/configuration mutation was performed against the host.

Real disposable Git2.43.0 subprocesses, using `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`,
reproduced the original failure naming the source `.git`. Merely adding another
top-level `-c safe.directory` did not cure it. The corrected clone uses `--no-local`
and explicit shell-quoted upload-pack with command-scoped trust of that exact source
metadata path; the outer clone trusts the exact worktree. Both reset inherited trust
entries and disable hooks. No global/system Git configuration was changed, no
wildcard exception was added and no Git security check was disabled.

[Twenty-six focused checks](evidence/p8/installer-recovery/focused-tests.txt) passed
in1.655s:15 new installer tests plus11 existing production-configuration checks.
Command: existing private web venv `web/manage.py test tests.test_production_config
tests.test_private_preparation --verbosity 2`, `RMC_WEB_ENV=test`, existing protected
key paths. Django skipped database setup; no database or service was started.
The new tests execute real cloning/checkout, including a quoted source path and an
older requested commit than source HEAD, independent object inodes, repeat completed
clone validation, unchanged isolated global config and continued denial for untrusted
Git commands. They reproduce failure then recover the same marker/revision and
exercise prepare through both real clones with OS identities mapped to disposable
fixtures, stopping before venv/database/services. Negative cases preserve unknown
files/interrupted destinations, reject mode/link/hardlink/receipt/revision/dirty-tree
mismatches and require local root for apply. These are host regression tests with
simulated ownership checks, not successful root-run production qualification.

The original application SHA must remain the retry's `--revision`; run the corrected
committed driver from the source checkout. The marker is never rewritten for a new
SHA. Existing known directories are validated without automatic permission repair.
Root must inspect/validate the protected state on retry. Unknown or interrupted clone
trees have no automatic deletion/adoption path; later database/migration interruption
recovery is not universally qualified. PRIVATE_INSTALL.md gives the concrete retry.
Read-only plan, Python syntax compilation and `git diff --check` passed. No native
code/engine/QNX evidence changed and no native build/run was repeated. Successful
root preparation, namespace/peer roles, HTTPS, production backup/restore/rollback,
off-host custody and independent UAT remain pending; P8 stays IN PROGRESS.

## W011 — Temporary in-unit credential diagnostic; correction awaits metadata

2026-11-08, branch `feature/production-web-ai`, base `d758972` plus this diagnostic.
The operator retried preparation and reports that the private socket is active,
the web service repeatedly fails during ExecStartPre with `RMC_WEB_SECRET_KEY
credential file permissions/type invalid`, the original application/MFA source
files remain root:root0600 and LoadCredential is configured. These source-key facts
and the exception are operator-provided; no protected key content was accessed.

[Read-only production observation](evidence/p8/credential-diagnostic/production-observation.txt)
confirms `User=Group=resmgr-web`, socket listening, web service auto-restart,
ExecStartPre `manage.py runtime_check` exited1, no drop-ins and the current release
pointer still targeting4ed4855. A static tree now exists. Runtime credential paths
were absent between attempts; the canonical installed unit file was unreadable to
UID1000. Installed systemd is255.4-1ubuntu8.18. No privileged command, production
unit installation, secret access, database change, Nginx change or QNX command
was performed by the agent. W010's earlier absent-release/unit inventory is historical.

The [upstream v255 credential implementation](https://github.com/systemd/systemd/blob/v255/src/core/exec-credential.c)
prefers a root-owned credential with a named target-UID read ACL, falling back to
target ownership when needed. Its ACL mask can appear as group-read in stat while
the owning group's ACL grants no access. The current Django validator rejects any
group mode bit; this is a plausible explanation, **not confirmed production file
metadata**. The [credential interface documentation](https://systemd.io/CREDENTIALS/)
and installed systemd.exec manual describe per-unit credential access/lifetime and
namespace visibility. Owner clarification explicitly requires the actual unit's
metadata before implementing the smallest production validator correction.

`web/ops/production/credential_diagnostic.py` therefore supplies a temporary
operator-run diagnostic only. Its root install/remove mode refuses active web
socket/service, noncanonical installed unit contents, unknown overrides, files,
links, wrong protection and mismatched prior diagnostic contents. It installs only
its own root-owned public Python script and runtime web drop-in, without touching
canonical units, release/current pointer, marker, source secrets or database. The
drop-in inserts a stat/fgetxattr-only observer then the unchanged runtime_check,
retains User/LoadCredential/sandbox/ExecStart and sets Restart=no for one attempt.
Removal verifies exact bytes/ownership and deletes only those known files. It is
repeatable after its own partial install. The observer always returns0 so a failed
metadata capture never prevents the original runtime_check from running; only that
original check controls application startup. It prints credential IDs and file
UID/GID/mode/type/ACL metadata, or fixed metadata errors, never secret bytes or hashes.

[Thirty-nine focused checks](evidence/p8/credential-diagnostic/focused-tests.txt)
passed in1.704s:13 diagnostic tests,11 existing production-configuration checks and
15 prior installer checks. No database setup was used. New coverage verifies that
os.read is never called by the observer, values/modes remain unchanged, actual
POSIX ACL metadata is decoded, leaf symlinks are reported without following them,
malformed ACL bytes are not dumped, missing metadata leaves runtime_check intact,
the override retains isolation, and install/remove preserves known/unknown resources.
Root install/remove behavior used disposable UID1000 fixtures with the root guard
mocked; this is not an actual privileged diagnostic installation.

[Actual unprivileged systemd user-manager test](evidence/p8/credential-diagnostic/user-systemd.txt)
used only synthetic LoadCredential sources. The final standalone probe succeeded
with both runtime files UID/GID1000,0400,regular,no access ACL. After the unit exited,
its runtime credential directory was verified absent. This tests the observer and
real credential lifecycle, **not the production resmgr-web context or root-managed
ACL branch**. D-Bus access from the sandbox initially failed; the approved external
test still used the unprivileged user manager, without sudo. Earlier exploratory
transient Environment properties left `%d` literal; explicit runtime paths fixed
the test invocation. No production Environment settings were changed.

Read-only default plan, syntax compilation and diff checks passed; settings.py,
canonical web unit, original engine/native/evidence files remain unchanged. Source
hashes and boundaries are in [checks.json](evidence/p8/credential-diagnostic/checks.json).
The production validator correction is intentionally not committed/applied until
the operator captures the real unit's JSON using PRIVATE_INSTALL.md and removes
the temporary override. Existing installation/keys/database remain preserved;
do not reset the original marker or run prepare with a new application revision.
Actual runtime_check, readiness, namespace/peer-role security and later production
gates remain unqualified. P8 remains IN PROGRESS; P9/P10 do not advance.

## W012 — Confirmed credential ACL correction; immutable private release recovery

2026-11-08, branch `feature/production-web-ai`, base `b278b30` plus this correction.
The operator confirms the temporary diagnostic ran inside the actual systemd
ExecStartPre context and was removed successfully. Both application/MFA runtime
credentials were root:root0440 regular files with owner-read, named UID982-read,
owning-group-none, mask-read and other-none ACL entries. Source keys remain
root:root0600; canonical unit/source files are unchanged. The structured
[operator confirmation](evidence/p8/credential-fix/operator-confirmation.json)
records this provenance; no secret bytes or hashes were requested or captured.
This supersedes W011's unconfirmed diagnosis. The old secret() rule treated the
ACL mask's group mode bit as an unsafe group grant and rejected these credentials.

`settings.secret()` now calls a standard-library credential reader. Ordinary
trusted-owner0400/0600 files without access ACL remain private. Every component is
opened without following links, using O_PATH for ancestors so directory-listing
permission is not unnecessarily required. File descriptors establish regular
single-inode type, owner and4096-byte bound before secret reads; the actual read
is bounded again and UTF-8/NUL errors remain content-free. The delegated path
requires a fixed role directory and exact credential ID, matching
CREDENTIALS_DIRECTORY, effective nonroot UID matching the dedicated account,
root:root0440 and exactly the observed five ACL entries. The pinned root:root0550
directory must have the exact named-UID read/search ACL. Directory metadata was not
part of the operator's supplied file report; it is an additional fail-closed
context invariant derived from systemd255 and covered by fixtures, with actual
acceptance still subject to the real unit gate. Arbitrary0440 files, extra/writable
ACLs, unexpected ownership/path/principals/entries, hardlinks, malformed inputs and
oversized files fail. Production file requirements and minimum secret length remain.

[Seventy-one focused tests](evidence/p8/credential-fix/focused-tests.txt) passed in5.474s:
15 credential checks,17 release-recovery checks,11 existing production configuration
checks,13 diagnostic checks and15 earlier installer checks. Django skipped database
setup. Positive ACL tests use real POSIX xattrs; root ownership is modeled over
unprivileged files. Hostile unrelated-principal ACL bytes are injected where sandbox
UID/GID mappings prohibit creating those principals. A fresh-process fixture models
the exact UID982/root0440/read-only ACL and loads production settings through both
the actual runtime_check management command and Gunicorn's application loader
(`--check-config`). Both accept that credential model and reject an owning-group
read grant without printing values. DB/sandbox/identity facts in that compatibility
fixture are explicit mocks; it starts no server and is **not actual resmgr-web
OS execution or production isolation qualification**.

`recover_credentials.py` provides a narrowly scoped, reviewed operator procedure
for the immutable4ed4855 installation. It rejects runtime changes outside credential
validation/related operations and requires unchanged dependencies, templates/assets,
models/migrations, unit files, engine and database-grant code. Before activation it
checks the exact original marker/clone receipt, clean original source/index without
optional Git index writes, original virtualenv, canonical unit, source-key metadata
without opening key contents, removed diagnostics/overrides and inactive dedicated
web/worker/timer units. It makes no database connection or migration, does not install
packages, rewrite configuration/units or start/reload services, and never contacts QNX.

An exclusive root-owned lock serializes the operation. An immutable exact-target
intent identifies the recovery. A fresh independent Git clone is checked/sealed
with its protected manifest, then published to a new commit directory and activated
by atomic current-pointer replacement. The unchanged old virtualenv and static
configuration are reused; the old release remains present/unmodified. Publication
cannot overwrite even an empty preexisting destination: a real
Linux/glibc renameat2(RENAME_NOREPLACE) check passes in disposable tests.
Interrupted staging attempts are retained, and retries use new attempts or validate/reuse an
already completed release. Unknown occupied directories, modified tracked/untracked
content, alternate intent/manifests/current pointers and canonical-unit changes are
refused. Pointer-only rollback preserves both releases and all data, returning to
the known credential-failing original with web stopped, not a healthy rollback claim.
Real disposable Git tests interrupt cloning and both sides of pointer switching,
repeat activation, roll back/reapply, and reject unknown resources/dependency changes,
active units, bad key modes and concurrent operators. Original key/database/audit,
unit/marker/source/index bytes and original source/index modes/mtimes are verified
unchanged. Root guards are mocked over disposable UID1000 fixtures; no privileged
release deployment was performed by the agent.

[Source/check boundaries](evidence/p8/credential-fix/checks.json) record actual hashes
and syntax compilation. `runtime_check.py`, the canonical web unit and Gunicorn
configuration are unchanged, as are dependency lock, migrations, templates/assets,
native/engine and original QNX evidence. A nonprivileged service query found web
failed, socket inactive and no drop-ins after the operator's diagnostic cleanup.
No privileged commands, service mutations, Nginx/other PostgreSQL changes, SDK/QNX
operations or credential copies occurred in this agent turn.

PRIVATE_INSTALL.md gives the exact next operator plan/apply/qualification procedure.
The new immutable commit must be activated, the actual systemd ExecStartPre
runtime_check must pass under resmgr-web, and Gunicorn must return private readyz
HTTP200 for the exact invocation before this startup gate is qualified. Those
actual corrected-production observations remain **PENDING**, along with remaining
P8 HTTPS/backup/restore/off-host/operational gates and independent P9/P10 acceptance.
Do not advance P8–P10 from these host/compatibility tests or edit the original
preparation marker to force an upgrade. Source secret values and protection remain.

## W013 — Gunicorn/systemd duplicate FD consumption and immutable socket correction

2026-11-08, `feature/production-web-ai`, base `d6513ba` plus this correction. The
[operator report](evidence/p8/socket-activation/operator-observation.json) confirms
the actual d6513ba credential correction/runtime_check succeeds under the dedicated
nonroot identity, nonprivileged DB role, unrelated-credential/IP-socket denials and
evidence-write boundary. Gunicorn then exits EBADF in explicit and triggered modes;
the latest private readiness request timed out10s with HTTP000. These are operator
observations, not a production service execution by the agent. [Read-only live unit
metadata](evidence/p8/socket-activation/production-units.txt) independently confirms
direct Python `-m gunicorn ... --bind fd://3`, matching socket/service association,
AF_UNIX stream path, Accept=no,0660/resmgr-web:www-data and no drop-ins. Both units
were inactive after operator cleanup and current points at d6513ba.

The actual installed and test Gunicorn versions are26.2.0. Source hashes for
arbiter.py/sock.py/systemd.py match byte-for-byte in the two virtualenv paths (the
installed release shares the original virtualenv). The arbiter calls listen_fds()
to discover descriptors3..N when LISTEN_PID matches. In the [pinned26.2.0 socket
implementation](https://github.com/benoitc/gunicorn/blob/26.2.0/gunicorn/sock.py),
create_sockets concatenates configured integer binds and discovered descriptors;
here that is[3,3]. The first BaseSocket wrapper duplicates then closes original3;
the second socket.fromfd(3) raises EBADF. [Official deployment guidance](https://gunicorn.org/deploy/#systemd)
uses automatic systemd discovery without an explicit fd bind. No systemd/launcher/
Python workaround or third-party package patch is needed.

An isolated real Unix listener, inheritable fd3 and matching modeled LISTEN_PID/FDS
reproduced the exact exception after direct exec into Python/Gunicorn. Thus a valid
FD existed before Python startup; the failing path consumes it twice. This is not
a claim that the stopped production process's live descriptors were inspected.
The root service's live LISTEN_* environment was not captured by the agent.

The production web unit removes only `--bind fd://3`. The original User/Group,
LoadCredential, runtime_check, RestrictAddressFamilies, IPAddressDeny, resource
limits and every other directive remain byte-identical. Socket configuration is
unchanged. Gunicorn's config sets an empty bind default (no implicit TCP) and a
production on_starting guard rejects explicit binds, missing/wrong PID/count,
non-socket/non-stream/non-listening/foreign-path descriptors. It inspects only a
duplicate of3, preserving original3 and LISTEN_* for the real automatic path.
The guard emits only a safe validated-listener marker, not credential data.

[Ninety focused regressions](evidence/p8/socket-activation/focused-tests.txt) passed
in10.591s:6 real FD/HTTP tests with modeled activation,13 real disposable Git/UID
upgrade tests and all71 earlier credential/release/config/diagnostic/installer
checks. Django skipped database setup. FD cases reproduce old EBADF with a proven
live descriptor, verify corrected Unix HTTP200 without rebinding the socket inode,
reject wrong/missing PID/count/closed/non-socket/foreign path and explicit duplicate
binds, and ensure HTTP503 or timeout cannot pass readiness. Compatibility fixtures
from W012 still model root ACL/UID982/DB/sandbox facts; they remain distinct from
real service qualification. No unchanged native matrix was repeated.

Four [actual unprivileged user-manager systemd cases](evidence/p8/socket-activation/user-systemd.json)
also passed. Both old modes supplied a live socket3 with LISTEN_PID matching and
LISTEN_FDS=1, then produced EBADF/readiness timeout. Both corrected modes supplied
the same valid handoff and returned AF_UNIX HTTP200. Actual IP-socket creation was
denied with NoNewPrivileges/RestrictAddressFamilies=AF_UNIX. Each randomly named
fixture unit was stopped and its socket removed. These tests use UID1000, synthetic
WSGI readiness and no secrets/DB/runtime_check, not the root-managed production unit
or full production namespace/BPF containment. Explicit-start user tests keep the
transient socket active; a discarded fixture variant stopped it and allowed its
never-started transient service definition to GC, causing a test setup error. That
variant was corrected without changing production configuration. Transient tests
made no Nginx/database/QNX/root service changes and did not bind a TCP listener.

`recover_socket_activation.py` performs the specific second immutable upgrade from
d6513ba. It verifies the original preparation/credential deployment records,
unchanged clean credential release/index/shared virtualenv, canonical web/socket
units and no filesystem/loaded overrides, source-key metadata without opening
contents, and inactive dedicated web/worker/timer contexts. Changes to credential
code, settings, dependencies, DB/grants/migrations, assets, engine or unrelated units
are outside its scope. It stages/publishes a new manifest-verified independent Git
release with atomic no-replace semantics, then atomically replaces only the known
web ExecStart suffix and current pointer. A separate exact-target SOCKET_RELEASE
intent and existing release lock support retries across cloning, unit replacement
and pointer replacement; unknown/modified resources are preserved/refused. Earlier
releases/manifests/configs/keys/database/audit remain untouched. Rollback restores
the known socket-failing d6513ba unit/pointer, not a healthy service claim.
The helper starts/reloads no service and requires explicit operator daemon-reload.

The [source/check boundaries](evidence/p8/socket-activation/checks.json) record exact
code/library hashes, syntax and unchanged credentials/settings/runtime_check/socket
unit/dependencies/migrations/assets/native/evidence paths. Production values were
never printed, copied or modified; no privileged installation command ran. The
PRIVATE_INSTALL procedure must now qualify the actual corrected root-managed unit
in both activation modes, current-invocation runtime_check/identity/role/credential/
network boundaries, validated listener and private readyz HTTP200. All those new
production observations remain **PENDING**. P8 stays IN PROGRESS; P9/P10/public
deployment do not advance from host or user-manager results.

## W014 — isolated restored audit proof, including empty tables (2026-11-08)

The operator reports active immutable release
`59158ade7da66475f3f1255e34aebd12fca29fce`, successful
`resmgrcheck-backup.service` and preserved encrypted archive
`/var/backups/resmgrcheck/snapshot_20261108T224711Z.rmc`. Its isolated drill failed
`backup_restored_audit_trigger_unproven`. Read-only systemd metadata corroborates
backup success and an active web service/socket at that release. The agent did not
open the protected archive/key, query production database rows or run a privileged
deployment. The production archive's actual audit count and restored trigger state
are **PENDING** operator `inspect-restore`; an empty production table is a
hypothesis, not an observed fact. See the [provenance record](evidence/p8/restore-audit/operator-observation.json).

A real encrypted development pg_dump/pg_restore reproduced the defect with zero
audit rows and the correct enabled trigger/function: the old UPDATE returned
rowcount 0 and raised no exception. PostgreSQL [row triggers execute per affected
row](https://www.postgresql.org/docs/16/sql-createtrigger.html); a zero-row UPDATE
cannot prove either presence or failure of append-only protection. A populated
archive also passes the corrected proof without selecting original audit rows as
mutation targets. The schema and append-only migration remain unchanged.

`restored_audit_metadata` reports count, presence, definition-match flags, enabled
state, replication role and definition hashes. It internally verifies the exact
known zero-argument PL/pgSQL function body/properties, trigger/function linkage and
BEFORE ROW UPDATE/DELETE shape with no WHEN/column/argument filters. Enabled `O`
or `A` is required with replication role origin; disabled and replica-only triggers
fail. The [PostgreSQL catalog](https://www.postgresql.org/docs/16/catalog-pg-trigger.html)
documents these states. Raw function source, row values and backup contents are
never included in diagnostic JSON. `inspect-restore` still performs authenticated
restore, hashes, database identity, immutable evidence checks and exact cleanup,
but intentionally returns `passed:false`/`audit_behavior_tested:false`.

`prove_restored_audit` rejects the source/default DB and any connection not matching
the exact generated `resmgrcheck_restore_<12hex>` name before DML. It requires an
autocommit independent connection and locks the isolated table against concurrent
schema/writes during proof. Within a full forced-rollback transaction it inserts
one new UUID synthetic event, changes its action and attempts its deletion in
separate savepoints. Both must produce SQLSTATE P0001 and exactly the expected
append-only exception; permission denial or no exception fails. Psycopg's
[transaction/savepoint and forced rollback semantics](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
are exercised against real PostgreSQL. The verifier checks count/probe absence
after rollback and full snapshot database identity again before returning. No
application live-DB connection is repointed. The existing authenticated encryption,
member hashes, owned private key, canonical collected-evidence checks and exact
created-DB cleanup remain intact. Failed cleanup prevents a successful verdict;
no broad termination or FORCE deletion was introduced.

[86 focused regressions passed in 22.137s](evidence/p8/restore-audit/focused-tests.txt)
on PostgreSQL 16.15, as the unprivileged development user in the existing private
development cluster. This includes 14 new audit/restore tests, six existing archive/
backup/status tests, ten new immutable-upgrade tests and 56 earlier credential/
release/production-config tests. Cases cover empty/populated audit tables,
metadata-only inspection, missing/disabled/replica/wrong/filtered guards, actual
behavior required even with mocked valid metadata, wrong SQLSTATE, source-DB refusal,
tampered ciphertext, createdb/pg_restore/cleanup failure and exact cleanup. The
existing real snapshot test also validates sealed artifacts and collected execution
inventories. After the suite, the test DB and all generated restore DBs were absent.
An earlier exploratory run with a random test DB name correctly hit the existing
local-operator guard in the operational-status test. Reusing its already approved
test DB name, after confirming absence, passed; the guard was not weakened.

`recover_restore_drill.py` is a specific third immutable upgrade from 59158ad. It
verifies protected preparation/credential/socket records, clean old Git/index and
shared virtualenv, unchanged canonical web/socket/backup units without overrides,
source-key metadata without content reads, inactive dedicated jobs/web/socket and
the exclusive existing release lock. It allows only restore verifier/CLI/helper
and tests/docs changes, rejecting schema/migration/credential/dependency/unit/engine
changes. An exact-target RESTORE_RELEASE intent and protected manifest govern a
fresh independently cloned release, published atomically without replacing any
occupied directory; only current switches. Retry/rollback preserve earlier releases,
partial attempts, archives/receipts, keys, DB/audit, units and preparation records.
Unknown resources or changed releases are refused. Ten tests exercise real
disposable Git trees and modeled UID/unit contexts, including interrupted clone,
pre/post pointer interruption, retries, rollback, active jobs/concurrent lock,
schema changes and unknown/modified resources. These are not root deployment tests.

[Source hashes and checks](evidence/p8/restore-audit/checks.json) distinguish real
development PostgreSQL execution, modeled deployment and pending production
qualification. No production service was restarted, no privileged deployment ran,
and no live audit mutation, key/snapshot replacement, Nginx/public exposure, native
build or QNX interaction occurred. PRIVATE_INSTALL.md provides the exact protected
inspection/full-drill commands using the existing snapshot and operator CREATEDB
profile, plus immutable activation/retry/rollback. The operator must record the
actual inspection and successful isolated restore and reverify the private runtime/
readiness/isolation before advancing this gate. **P8 remains IN PROGRESS; P9–P10
and public deployment remain withheld.**

## W016 — staged runner job and evidence route (2026-11-09)

108 focused tests passed in26.236s, followed by one additive migration/legacy encrypted restore test in1.557s. This adds real loopback TLS signed-job/upload/private-ingestion, durable lost-grant/lost-upload-ack tests, immutable job/chunk provenance, tenant/ticket denial, quotas,15-minute authority expiry, read-only storage-budget checks, unsafe archive/occupied destination refusal, missing/incomplete native evidence quarantine and exact original evaluator sealing. Genuine recorded native fixtures retain their original IDs and are never labeled new execution. Real SET ROLE checks confirm HTTP may insert chunks but cannot rewrite/delete them or seal artifacts, while the nonowner executor may seal and clean completed upload chunks. All random test roles and test/restore DBs were absent after the suite. Initial job tests caught PostgreSQL rejecting FOR UPDATE on nullable joined principals; locks now explicitly target only intended rows. An earlier test helper shadowed its module name and prevented discovery; it was corrected before execution. No production data/roles/keys/units were touched.

The separate migration test uses only the dedicated disposable test DB with no runner rows. It preserves existing user/project/audit IDs while reversing0018/0019, creates and actually restores an encrypted pre-runner-schema fixture with the audit proof, then reapplies the additive migrations and checks row preservation. It does not reverse production migrations or delete customer records. New snapshots include counts for all runner tables; the original pre-runner archive format remains accepted and partial additive schemas fail closed. TLS and job tests use fixture discovery, and command-execution fixtures copy labeled genuine saved evidence; no new QNX behavior is claimed by them. All temporary keys remain local/outside Git. Actual new-runner QNX, added adapter, separate-host, browser and production immutable upgrade/rollback qualification are still pending. Off-server DR stays deferred, not passed.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 — real local runner route, additional native service and browser continuation

[evidence/runner-native/index.json](evidence/runner-native/index.json) binds the
actual source candidates, qcc binary hashes, deployment IDs, original native IDs,
case bundle hashes and scope. New native observations are mailbox FAIL
w8d66e00e0e544645b9, actual corrected-source replay PASS w064e821521a9460499,
sensor PASS wcfbbd9bf3a984ae586 and job PASS w1422b4ce6fb04060a4. Each runs the
timeout profile through browser authorization → signed HTTPS job → customer runner
process → actual QNX → private immutable ingestion. Only the mailbox fixture binary
changes between candidates; this is a source correction, not a fixture-mode label.
All four contain actual cleanup observations. A real fixture-gateway503 interrupted
the replay's chunk upload; the second process resumed the same archive/native ID
without regranting or rerunning. Mailbox input/protocol/ACK tests passed23/23 on QNX,
with exact direct-child wait status. PID/instance facts do not attest a binary.

The original native/browser report deliberately remains passed:false: a later
APIRequestContext ZIP request did not share Chrome's private CA trust. Earlier
pre-native attempts found an unavailable default Chrome cache, a sync Playwright/
Django async-boundary issue and a missing breadcrumb underline; these were fixed
without bypassing TLS, Django's async safety or accessibility checks. No native run
was repeated to repair presentation-only tests. The continuation passed in15.486s
on a fresh disposable DB using the same verified native bytes labeled RECORDED.
It exercises real password/TOTP, scoped codes and revocation, source comparison,
Chrome-authenticated ZIP download, tenant/admin denials and390px no-JavaScript
layout. Original report:16 views/8 Axe scans; continuation:15 views/5 scans, zero
reported violations. These are automated UID1000 staging tests, not actual root
systemd, public HTTPS, a separate customer host or independent human acceptance.

The opt-in qualification modules do not match test_* discovery. Native execution
requires the explicit approved-local-lab environment and existing private route;
no credentials, images or binaries are committed. Original QNX histories/engine
selection, production DB/keys/snapshot/units and other VPS applications are preserved.

W018 closing regression:120 focused PostgreSQL/TLS/runner/work/dashboard/restore/
credential/config tests passed in34.947s; see evidence/runner-native/regression-tests.txt.

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

Operator-provided safe JSON confirms e1ef88c failed private_response_cacheable
and rolled back its own changes. No protected logs or state were requested/read.
The actual Django anonymous /app/ redirect emits no-cache. The earlier synthetic
backend emitted no-store and did not reproduce this behavior.

The correction sets no-store on all dynamic responses at the dedicated HTTPS
boundary while preserving static public300. Actual isolated Django/PostgreSQL/
Nginx/private-TLS ran the same deployment checks:13 probes PASS in one test1.346s;
upstream no-cache became boundary no-store. Four actual isolated Nginx tests PASS
in3.439s (including no-cache synthetic redirects, custom evidence CSP, static,
rate limits, TLS, Unix proxy and errors). Twenty focused recovery/permission tests
PASS in0.779s. Root/systemd/deployment side effects in those20 tests are modeled;
filesystem rollback and owned subprocess handling are real. Candidate migration
covers a changed reviewed payload, old-hash mismatch rejection, immutable backups,
exact original restoration and refusal of verified/concurrently edited resources.

See evidence/https-cache-recovery for logs and explicit provenance. Existing44-view/
12-scan isolated browser evidence remains valid for its recorded scope and was not
repeated. No production browser/native execution or successful external TLS is
claimed for this correction. Root retry, actual renewal/rollback, production
acceptance and independent client verification remain pending.

## W024 graceful reload and strict rollback verification

See evidence/https-reload-recovery for protected-inspection provenance, safe
metadata and fresh test logs. Agent sudo could not use terminal-scoped credentials;
the operator ran the read-only repository probe. It emitted no configuration,
secret or log contents. No failed-command diagnostic file was present. Protected
state says rolled_back_after_failure, rollback_original_http_not_restored,
renewal_completed_and_recorded:true and rollback_verified:false. Code records that
renewal marker only after Certbot return0: the dry run completed, and failure was
in the subsequent rollback drill. Original HTTP configuration restoration is
confirmed by exact backup/bootstrap hashes/bytes, root0644 modes, correct symlink,
absent own hook, successful nginx -T and actual404. Private readiness200, active
nonroot web/socket/nginx and active immutable544f22c are preserved. Certificate
links remain root-owned in the dedicated archive, fullchain0644/private key0600.

The actual nginx ExecReload sends a signal and returned0. The old first HTTP probe
status was not recorded; its exact historical value cannot be asserted. A real
isolated master/worker test pauses only its owned master, installs original HTTP
configuration, validates it and queues HUP. Its existing worker still returns308.
The corrected bounded verifier observes308 then404 after that master resumes and
proves unique ACME handling. This establishes the timing defect without modifying
production Nginx or any unrelated service.

27 recovery tests PASS in1.166s: real disposable files/process groups; root/systemd/
Certbot/HTTP modeled. Coverage includes stale workers, persistent wrong HTTP refusal,
exact modes, refusal of404 without an ACME round trip, interrupted original restoration, preserved backups, new-driver
recovery retaining the completed Certbot proof, and TLS reactivation delay. Five
actual isolated Nginx/TLS/Unix-proxy tests PASS in4.762s, including the owned master
reload reproduction. Existing W023 real-Django13-probe and W021 browser evidence
retain their earlier scope; no production browser/native testing was repeated.

Current local verified curl fails hostname validation; independent external
Firecrawl readiness fetch fails TLS too (its connector500 is not a target HTTP
response). TLS was never bypassed. Production corrected retry, real public auth/MFA/
codes/browser/native acceptance and independent existing-admin UAT remain NOT_RUN.
Customer separate-host qualification remains BLOCKED, endpoints/AI disabled and
off-server DR deferred. P8 remains IN_PROGRESS.

## W025 Unix proxy identity and immutable authentication recovery

See evidence/https-auth-identity for exact logs and provenance. The real cf15209
operator run passed HTTPS/renewal/rollback, then browser acceptance failed. Its
report records seven views, five zero-violation scans, no native runs and timeout
at administrator login; root status metadata confirms the browser POST returned403.
The protected cleanup receipt confirms only the temporary account/codes were
disabled/revoked, original users unchanged, audits/evidence preserved and no active
native work. Original HTTP-only configuration is restored; private readiness200
and dedicated units active. The agent did not execute privileged deployment.

Installed allauth65.21.1's DefaultAccountAdapter.get_client_ip raises PermissionDenied
when its default peer/XFF lookup cannot find an address. The new exact-context test
uses empty REMOTE_ADDR, overwritten X-Real-IP, real CSRF and the old default setting:
login returns403 before authentication. Enabling the supported production-only
header setting returns200 on a wrong password, password302 to MFA, keeps dashboard
unauthorized before TOTP, then authenticates only after actual valid TOTP. Missing/
invalid/comma-list headers fail closed; forged XFF cannot substitute, valid IPv6
works, missing CSRF and hostile origin still return403. The existing fixture's
forced127.0.0.1 concealed this production-only condition and is corrected.

61 actual PostgreSQL identity/access/route/cleanup tests PASS in12.968s. Seven actual
Gunicorn26.2.0 inherited Unix-FD tests PASS in2.678s; the new route observes exactly
empty REMOTE_ADDR with the explicit proxy header retained. LISTEN_* is modeled,
not an actual systemd qualification. The corrected real Django/PostgreSQL/Nginx/
verified private-TLS browser rehearsal PASS in163.049s:44 desktop/mobile/no-JS views,
12 zero-violation scans, actual password/TOTP and code issuance/scope/revocation/
usage/expiry; Gunicorn's empty address is modeled in this WSGI fixture. No production,
root, external client or QNX qualification is inferred from that rehearsal.

15 recovery regressions PASS in0.181s, one privacy-reporting test PASS. Recovery tests
use real disposable pointer/history files and model root/services/backups/HTTP.
They cover original-private restoration on runtime/browser failure, same-release
resume/interrupted pointer, changed unit/native/settings rejection, unknown release
preservation, snapshot-hash mismatch and verified-proof reuse. Runtime helper is
operator-only, checks no pending migrations and creates new static assets without
schema/grant writes. Successful original-private restoration after corrected
production failure remains pending real qualification; nothing patches current.
Production acceptance, exact corrected systemd isolation, external HTTPS and native
registry approval remain pending. Customer/AI disabled; off-server DR deferred.

Final combined driver/cleanup suite:52 tests PASS in6.245s. A pre-existing test
checking an owned killed child raced /proc reaping; it now accepts disappearance
between lookup/read as a reaped process, while any still-present process must be
a zombie. The final pass includes all strict rollback/TLS/security regressions.
No application supervision behavior changed for that test correction.

## W026 password-only administrators and preserved recovery state

Evidence: evidence/password-only. Operator-run read-only probe confirmed e6890b0's
RuntimeError at original release unknown_untracked_content, phase prepared, no
backup bound and no completed staged manifest. The exact original544 remains active,
private readiness200, own HTTP404/root0644 files/link restored and units active.
The preparation diagnostic's Git-ownership markers predate this attempt and are not
the new failure. No secrets/protected contents were displayed. Unprivileged walk
finds root-owned750 __pycache__ directories under resmgrcheck, web/control and
web/resmgr_web, no unexpected visible files; contents are inaccessible to agent.

The Python regression proves -I ignores PYTHONDONTWRITEBYTECODE while -I -B prevents
writes. Root launchers also set sys.dont_write_bytecode before repository imports.
Cache validation compares bounded protected regular single-link files, interpreter/
header/source binding and exact marshal bytes of fresh compilation of Git-trusted
source; it never imports or unmarshals the candidate and never deletes/chmods it.
Tests reject tampered payload/header, unrelated files, symlinks and world-write.
Actual protected cache equality remains required by the operator command. Prepared
325f367/e6890b0 can transition only with original544 still current and no backup
bound/verified; its exact journal is retained. Unknown states/resources are refused.

Full web suite392 tests PASS in93.974s using disposable PostgreSQL/files/processes.
It covers current password-only login both with/without stored MFA, unchanged
Authenticator records, local recovery preserving records/refusing reset, actual
invalid-login/rate/CSRF tests, secure cookies/origin, idle/absolute expiry and recent
password checks, code issuance/revocation/limits/concurrency, scoped protected routes,
queued native/AI authority and start revocation, immutable/audit/backup/restore and
existing runner guards. Legacy MFA compatibility tests use explicit test-only
ADMIN_MFA_REQUIRED=True; they do not claim current MFA enforcement. Native scheduling
tests now create administrators without authenticators. Schema/models/migrations,
engine/CLI/native evidence/units/dependency locks were not changed.

The final browser rehearsal uses actual Gunicorn26.2 over an actual Unix socket,
Django/PostgreSQL and Nginx TLS, rather than a fake loopback REMOTE_ADDR. It PASSes
in150.878s:46 views/12 zero-violation accessibility scans on desktop and mobile/no-JS,
real wrong/correct password, no MFA redirect, deferred MFA route404, access codes,
expiry/usage/revocation, tenant/admin denial, CSRF and cookie/header checks. Its
fixture CA is explicitly trusted/pinned for this isolated host only; production
has no TLS bypass. Native status remains blocked and no QNX runs execute. It is
not actual systemd, production DB role, public deployment or independent UAT.

Final focused immutable-recovery and cache regressions also pass; see exact logs.
Privileged side effects are modeled there, filesystem/pointer/history checks real.
New protected receipt output explicitly names password-only/deferred policy and
safe failure stages. Real production activation/isolation, retained cache proof,
fresh backup/restore, independent public TLS and password/code/native acceptance
are pending the new operator command. AI/customer endpoints disabled; off-server
DR deferred. P8 remains IN_PROGRESS.

## W027 exact derived-cache proof and recovery correction

Protected read-only probe provenance and exact cache/source/hash metadata are in
evidence/bytecode-recovery/observed-caches.json. Operator55daf08 failed at
original_release_validation, still prepared_after_reviewed_password_policy with no
bound backup. It did not stage3f4bafb or change a service. The probe confirms original
544 source/origin clean, manifest SHA25612ae2c9115b31ac323c8a9ad4db9f075b11703fab5490e320a04ecf23e3f5134
matching recorded identity and the original protected venv binding. Fourteen cache
files are regular root:root0640 cpython-312 data, distinct from tracked source,
dependencies, configs and executables. The service cannot create root-owned cache
files; its nonroot identity/read-only code tree/no-bytecode environment is unchanged.

Cache mtimes11:21:27.790533–11:21:28.149536 UTC coincide with cf15209 root acceptance
imports immediately before its browser output directory birth11:21:28. That old
root -I invocation lacked -B; setting PYTHONDONTWRITEBYTECODE inside its environment
could not change interpreter startup behavior. The ownership, timestamps and launch
path strongly indicate earlier root acceptance imports as the cache origin; this
is an inference, without a process-level file-creation audit. The new -I -B preflight
cannot explain these earlier timestamps. Source and dependency identities are intact.

The only mismatch against cold optimize=0 compilation is contracts.pyc:46918 bytes,
SHA256116ccaf3a6158dafae68f192f249286ce000275553c4eee0c67d2adc9c3084a1. Its source is
29669 bytes, SHA2566537b93f6662a0cf386b48dc02b6d62d0026d2d8d0eb6a4df16b3406c8de13b5,
mtime1794212697. Cold payload46887 bytes differs from warm payload46902 bytes.
Two identical optimize=0 compilations on CPython3.12.3 reproduce the complete
observed cache hash when the first code object remains alive. No marshal.loads,
unknown-code import/execution, filename normalization or optimization waiver is
needed. The earlier diagnostic's optimize=1 match was not proof of an optimized
origin; the same complete bytes are obtained at optimize=0.

The committed unprivileged reproduce_release_bytecode.py verifies visible source
against Git and reconstructs all14 full cache hashes from captured metadata. All14
PASS; cache files are never opened or modified by that reproducer. The exact-case
regression runs in a fresh -I -B subprocess and asserts the actual production hash.
84 recovery-related tests PASS in10.214s with disposable PostgreSQL/files/processes;
root/systemd effects modeled. Nine cache regressions and18 journal/recovery cases
include tampered payload/header, corrupted or executable source, executable cache,
unknown directory, symlink, empty source and interrupted history publication. Failed
preflight is proven to leave services/releases untouched and safely resume. The
full authentication/browser qualification from W026 is retained for unchanged3f4bafb
and was not needlessly repeated. No actual production recovery has run by the agent.

Protected health reports original544 active, private readiness200, database reachable,
nginx/db/web/socket active, own HTTP404/original files/link restored. Unprivileged
checks confirm executor/AI/backup inactive, no dedicated unit overrides, roughly43GB
free, and no3f4bafb release directory. Actual corrected recovery, fresh backup/restore,
new private systemd isolation, public HTTPS/password/code/native and independent
acceptance remain pending. AI/customer endpoints stay disabled; off-server DR deferred.
P8 is IN_PROGRESS.

## W028 actual production password/code/browser acceptance

The operator completed recover_https_auth.py using application
`3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58` and driver
`1ee18b6be6084e7e8dd7036a52947374a288b27f`, with -I -B. Protected original-release
validation reported PASS for all 14 retained bytecode files and no original-file
changes. The workflow advanced through mandatory dedicated backup, isolated restore,
private runtime/readiness and HTTPS checks, then finished browser acceptance without
rollback. These gate outcomes are operator evidence plus code-path verification;
protected snapshot/runtime/configuration receipts were not independently opened this
turn. Agent read-only checks confirm current points to3f4bafb and nginx/db/web/socket
are active. Original544 remains preserved.

The actual nonsecret browser-report.json and operator-cleanup.json were read directly
from .local/web/evidence/production-https-8702f911d6744bc5af36f2b2d607e1b2 and copied
unchanged into evidence/production-password-acceptance. browser_passed is true;
administrator_password/access_codes passed, MFA deferred. There are46 views across
desktop/mobile/no-JS,12 accessibility scans with zero reported violations. Checks
include invalid/valid password login, administrator overview/security/code issuance,
code redemption, single-use limit, actual-clock expiry, active-session revocation,
cross-tenant404, code-to-administrator404, GET logout405 and CSRF/origin. These are
real HTTPS requests through production Nginx/Gunicorn/Unix-socket/systemd, not the
previous loopback rehearsal. Full idle/absolute session durations were not waited;
the report correctly retains their unit-only qualification. No credentials, cookies
or traces were saved. Temporary account disabled, temporary codes revoked, existing
users unchanged, audits/evidence preserved, no active native work left behind.

VPS-origin standard-library HTTPS client verified the certificate and HTTP200,
HSTS max-age31536000, CSP, nosniff and same-origin referrer policy. The generic external
web tool could not retrieve the site; a fresh independent Firecrawl fetch then
returned HTTP200, expected title/public recorded-evidence page, maxAge0 and
skipTlsVerification=false. Receipt metadata is external-public-fetch.json. This
qualifies off-server public reachability only, not external authenticated sessions
or native testing. Independent authenticated/operator UAT remains pending.

The browser report's overall passed=false denotes native BLOCKED, not browser or
recovery failure. Native reason is approved_executor_registry_missing; runs=[] and
no production QNX case executed. acceptance_operator.native_plan fails closed before
selecting targets/builds or starting the executor. The registry requires exact
approved tenant/project/target bindings, private existing route and a verified
sensor before/after + job build pair. No route, key, target grant or execution
permission was created/changed. Production customer endpoints and AI remain disabled;
separate customer-host qualification absent, off-server DR deferred. Existing native
and CLI evidence remains unchanged. Full application rollback and independent
acceptance remain outstanding; P8 is IN_PROGRESS. This checkpoint changes only
documentation/evidence, with JSON/count/integrity checks and no repeated test matrix.

## W029 production executor workflow staged (not executed)

The active application remains3f4bafb; HTTPS/password/code/browser acceptance from
W028 is retained. Fresh VPS-origin HTTPS /readyz/ returned200 with trusted TLS.
Read-only development-UID preflight independently verified both pinned original/
corrected remote manifests and all ten native file hashes on the existing QNX8 lab.
No test or service was started. The lab has148 free file entries; no old evidence
was removed. Native acceptance is bounded to three cases, combining defect recovery
and job revocation with the required source-corrected replay.

[PRODUCTION_EXECUTOR.md](PRODUCTION_EXECUTOR.md) supplies one reviewed operator
workflow: exact private registry/route/key copies with restrictive executor ownership,
additive scoped approvals, actual canonical-unit credential/sandbox probe, restored
normal dispatcher, production dashboard tests, evidence/download checks and safe
temporary-account/code cleanup. No Nginx/auth configuration or immutable source patch.

The committed database grant matrix lacks permission for start_authority's row locks.
Real disposable nonprivileged PostgreSQL tests reproduce that failure and verify a
lock-only correction: UPDATE(id) plus invoker-role triggers that reject every actual
executor authorization UPDATE. No authorization rows, ownership or table-wide UPDATE
permission are changed. Actual production grant metadata is checked in the operator
workflow; no root DB operation ran by the agent. Unknown guards/grants are refused.

74 tests PASS in11.333s, including22 focused provisioning/PG tests. Filesystem/PG
effects are real and disposable; systemd/signals are modeled. Actual production
registry, executor role/sandbox, native IDs/verdicts, same-ID recovery, revocation,
evidence integrity and cleanup remain PENDING ROOT EXECUTION. The idle executor
stop/start rehearsal is staged; full compatible application rollback remains open.
[INDEPENDENT_UAT.md](INDEPENDENT_UAT.md) is NOT_RUN. See
[evidence/production-executor-plan/checks.json](evidence/production-executor-plan/checks.json).
Customer endpoints/AI remain disabled, off-server DR deferred and P8 IN_PROGRESS.

## W030 root-coordinator ownership mismatch and resumable correction

The operator's ce97 run passed private binding installation, the actual canonical
executor credential/sandbox/DB/native capability probe and approval publication.
The failure was acceptance/ exact_approved_native_plan_required. Source proves it
occurred before any native intent, temporary account or browser batch was created.
The protected state is not readable by the agent; no direct protected-log inspection
is claimed. The revised root command will verify that exact state privately.

acceptance.native_plan accepts registry metadata owned by resmgr-exec, then calls
control.engine.registry under root. The latter correctly accepts only UID0 or its
calling UID; a registry owned by UID981 fails executor_registry_permissions there.
The selector suppresses PolicyError and returns zero pairs. A disposable PG/files
regression reproduces the original result, then proves the fixed-ID root coordinator
accepts exact executor custody. The generic worker validator remains unchanged and
still rejects the same file under an unrelated UID. Labels are not authority.
Negative checks reject insecure mode/UID, cross-tenant rows and altered manifests.

78 combined tests pass in11.412s;26 focused tests refreshed in0.665s. PostgreSQL and
files are real/disposable; root identity and systemd/signals are modeled. SQL capture
proves the resume lock-guard checker emits no GRANT/DDL/mutations. Recovery tests
prove original state/failure/runtime proof preserved across an archive/publication
interruption, while wrong phase/failure, changed custody and native intents refuse
adoption. Tests/evidence are in evidence/executor-selector-recovery.

The agent independently observed3f4bafb current, trusted HTTPS /readyz/200 and active
nginx/database/web/executor services. No privileged production change or QNX lifecycle
test ran by the agent. Actual production probe success is operator evidence; native
IDs/verdicts/recovery/revocation/cleanup and rollback/UAT remain unverified. AI/customer
endpoints remain disabled, off-server DR deferred and P8 IN_PROGRESS.
