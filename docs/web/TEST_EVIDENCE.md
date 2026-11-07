# Production web test evidence

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
