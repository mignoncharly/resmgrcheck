# Production web test evidence

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
