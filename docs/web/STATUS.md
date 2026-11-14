# Production web implementation status

W041 (2026-11-14): approved hackathon improvements in progress. Shared report/demo
assertion explanations pass117 host/10 dashboard tests; raw evidence and canonical
verdicts remain unchanged. Host-origin current pointer namesdfe1060 and web/executor
are active. This observation supersedes W040's pending-pointer statement, but no
protected activation receipt or independent UAT was reread. New presentation changes
are not deployed. Full compatible rollback and independent UAT remain open; local
sudo requires authentication. Owner has no independent tester yet. See E018 in
the engine test record and submission/improvement-gates.json.

W040: owner authorized deployment of navigation candidatedfe1060 from current21a6f57.
The separately pinned deploy_navigation.py driver is prepared/tested; activation
remains pending because noninteractive sudo requires a password. It reuses the
existing immutable procedure with a separate navigation-release journal.33 helper
tests pass; HTTPS readiness200/TLS verification0 and web/executor active were
observed before activation. See NAVIGATION_DEPLOYMENT.md for the local root command.

W039: application-wide navigation implemented on feature/production-web-ai; not
deployed. One permission-aware component supplies desktop/mobile section links,
active state, breadcrumbs and contextual returns for project/target/run/compare,
organization/admin/code/security, runner and AI/source screens. Run history can be
scoped to an authorized project and preserves useful filter context on return.
See NAVIGATION.md and TEST_EVIDENCE W039. W038's fixed21a6f57 candidate does not
contain this navigation change; any subsequent deployment needs a separately
reviewed immutable candidate/driver. Do not patch /opt/resmgrcheck/current.
Read-only current-pointer observation at W039 is21a6f57 (the earlier security-page
release). No protected deployment receipt was reread and no new production
qualification is inferred from that pointer. Navigation is not deployed.

W038: owner requested deployment of W037. A reviewed exact-candidate release driver
is ready; activation remains pending local root execution because sudo requires a
password. See [SECURITY_PAGE_DEPLOYMENT.md](SECURITY_PAGE_DEPLOYMENT.md). It reuses
immutable staging/backup/restore/runtime/browser helpers, updates only the own
static alias, preserves W036 native evidence and performs no native execution.
Production pointer remains3f4bafb; no privileged procedure has run in this turn.

W037 (2026-11-10): administrator security redesign implemented and locally tested;
not deployed. Settings alone bypass the login-width wrapper and use a1080px layout,
real current-session matching, UTC session dates, recovery guidance and a separate
password-confirmed danger zone with inline errors.53 focused tests passed; desktop,
tablet and mobile/no-JS captures have no overflow or axe violations. Production
remains3f4bafb. See evidence/administrator-security-redesign and TEST_EVIDENCE W037.

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. W028: immutable application `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`
is active. Production password/code/browser acceptance passed; an independent
external public fetch returned HTTPS 200. W036: operator recovery driver
`1fde3dfc1f4a3fbd74faa05bdc6212a1efc187c6` completed same-ID recollection and
production native acceptance. Original collection ERROR remains preserved;
recollected defect FAIL and cleanup allowed the new acceptance batch. Sensor
source-corrected timeout replay PASS, intentional defect FAIL, job timeout PASS,
interrupted-connection same-ID recovery, live/queued revocation, verified evidence
downloads and cleanup all passed. The guarded idle executor stop/start passed.
Independent UAT and full application rollback remain pending. W030–W035 below
preserve the original failures and preparation history.
P8 is IN PROGRESS. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

Branch: `feature/production-web-ai`. Specification: `3d9048a`, superseded for access by the owner-approved administrator/code decision (2026-11-07).
The published CLI/jury release `ca4f74e` remains independently recoverable.

Native recovery/acceptance is complete; do not repeat provisioning or qualification.
Next remaining acceptance work: [independent UAT](INDEPENDENT_UAT.md) and a separately
reviewed compatible application rollback drill. No HTTPS redeployment is required.

## W028 HTTPS checkpoint (executor status superseded by W030)

Active immutable application: `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`.
Completed operator recovery driver: `1ee18b6be6084e7e8dd7036a52947374a288b27f`.
The pointer and nginx/database/web/socket active states were independently inspected
read-only. Original `544f22c` remains preserved. The corrected preflight validated
all 14 retained caches without changing original files. The operator workflow
completed mandatory fresh encrypted backup, isolated restore, private runtime and
readiness gates before HTTPS activation. Protected receipts were not read this turn.

Actual production HTTPS browser acceptance passed password-only administrator
login, scoped code issuance/redemption/revocation/usage/clock expiration, CSRF/origin,
cross-tenant and administrator denial checks, 46 desktop/mobile/no-JS views and
12 scans with no reported accessibility violations. Temporary accounts were disabled
and codes revoked; existing users, audit and evidence remained intact. Full 30-minute
idle/12-hour absolute expiration durations were unit-qualified, not waited in production.

The intended public URL is https://qnx-resmgrcheck.gestionatech.de. VPS-origin TLS
verification and HTTP 200 passed, with HSTS/CSP/nosniff/referrer headers. A fresh
independent Firecrawl fetch also returned HTTPS 200 and the expected public landing
page with TLS verification not disabled. This qualifies public reachability only;
independent authenticated/native acceptance remains pending.

| Gate | State | Evidence |
| --- | --- | --- |
| P0–P5 | Prior staging qualification retained | Original engine/evidence/tenant authorization unchanged; historical qualification retained |
| P6 AI | PASS for disabled release mode | AI stays disabled; no provider qualification |
| P7 customer targets | IN PROGRESS | Separate customer host unavailable; machine endpoints remain disabled |
| P8 hardening | IN PROGRESS | Production native recovery/acceptance and executor rehearsal passed W036; full application rollback and independent UAT pending |
| P9–P10 | INCOMPLETE | Public reachability and production native passed; full independent acceptance incomplete |

Production registry provisioning and the actual executor probe passed in ce97.
W036 completes the native recovery and dashboard qualification after the selector,
dispatch mutex, controller selection and Git index corrections. Preserve completed
provisioning, all prior ERROR/FAIL records and separate recovery evidence.

The HTTPS workflow completed its own configuration rollback drill before acceptance;
full rollback of the newly active application was not exercised this turn. Existing
historical rollback records remain. Off-server disaster recovery is deferred.
See [the W028 evidence](evidence/production-password-acceptance/checks.json) and
[HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md). No privileged action ran by the agent.
No unrelated VPS application, QNX process, credential or database record was changed
by this documentation/evidence checkpoint.

## Historical installation checkpoints (superseded where noted)

2026-11-08 earlier recovery update (W010, historical): the operator ran preparation for exact application
revision `4ed4855f7633176baea06f2be53154630a9d4d1f`; it failed during clone with
reported Git dubious ownership. Dedicated accounts/groups/directories and protected
log/marker exist; release/engine/database/static/current and all dedicated units do
not. The corrected installer supplies exact source `.git` trust to `upload-pack`,
uses independent transport objects and validates early recovery/clone receipts.
No global Git trust changes. Twenty-six focused checks pass with real disposable
Git subprocesses and simulated differing-owner checks; no privileged installation
was run by the agent. Protected log/marker contents remain unread because local
sudo authentication is required. Retry with the corrected committed driver and
the original application SHA in PRIVATE_INSTALL.md, not the correction's HEAD.
No native engine/evidence or unrelated service changes; P8/P9/P10 do not advance.

W011 historically superseded W010's empty-install observation: the operator retry reached web
startup. The current pointer targets application4ed4855; a static tree exists,
the socket is listening and the service is in auto-restart after ExecStartPre
credential validation failure. The operator confirms root:root0600 source keys
and LoadCredential; actual in-unit file/ACL metadata has not been captured.
The possible systemd POSIX ACL-mask incompatibility remains a working diagnosis.
At the owner's request, the next step is a temporary operator-installed metadata
probe before the unchanged runtime_check, with one-attempt restart behavior and
explicit cleanup. PRIVATE_INSTALL.md gives exact commands. No production credential
validator/security change is committed before that evidence. No privileged command
was run by the agent; only disposable unprivileged synthetic systemd tests ran.
The existing keys, database, release marker, canonical units and QNX remain intact.

W012 supersedes the pending diagnosis: the operator captured root:root0440 regular
runtime credentials with owner-read/named-UID982-read/group-none/mask-read/other-none
ACLs, and successfully removed the diagnostic. The ACL mask caused the old generic
group-bit rejection. The new validator accepts only exact protected systemd path,
ID, account, ownership and ACL context; ordinary private-file rules remain strict.
The immutable replacement procedure preserves the original4ed4855 release/virtualenv,
keys/configs/database/audit/static tree/units and preparation marker, publishes a new
commit directory and atomically switches current. It is resumable with retained
staging attempts and exact-target rollback; no privileged installation was run by
the agent. Seventy-one focused checks pass, including UID982 entrypoint compatibility
fixtures and real disposable Git recovery. Those fixtures simulate OS/DB/sandbox
facts; real runtime_check and Gunicorn readiness under resmgr-web remain pending.
Use PRIVATE_INSTALL.md's operator command; no P8/P9/P10 advancement yet.

W013 updates W012's runtime boundary: the operator activated d6513ba and confirms
real runtime_check success (nonroot/dedicated identity, nonprivileged DB role,
unrelated-credential denial, IP-socket denial and evidence-write boundary). Gunicorn
then failed with EBADF in both activation modes; readiness timed out with HTTP000.
Gunicorn26.2.0 merges explicit fd://3 with systemd's discovered3, consumes/closes3
once and fails on the duplicate. Actual unprivileged systemd tests reproduced both
old failures with live fd3 and correct LISTEN_PID/FDS; both corrected modes return
Unix HTTP200 with actual IP-socket creation denied. Synthetic WSGI/UID1000 test
scope is distinct from production keys/DB/UID982/full isolation.
The unit now omits the explicit bind; a no-TCP-default config validates one exact
inherited Unix listener without consuming it. The second immutable recovery
procedure preserves credential code/data/records and all other isolation directives,
publishes a new release and updates only the known web ExecStart and current pointer.
No privileged production deployment ran by the agent. Real root-managed corrected
activation, current-invocation runtime_check and readiness remain pending; P8 is
IN PROGRESS, with P9/P10/public deployment withheld.

W014: the operator activated 59158ad and the protected backup service completed
successfully. The isolated drill of snapshot_20261108T224711Z.rmc failed
backup_restored_audit_trigger_unproven. A real restored empty-table test shows
the old UPDATE affects 0 rows even with the correct enabled trigger/function.
The production archive's actual count/metadata remain unread by the agent because
the archive/key are protected; inspect-restore now reports only those facts after
authenticated isolated restoration, with no mutation probe and no passing verdict.
Full verification requires exact metadata plus actual UPDATE/DELETE rejection on
a new synthetic row in the isolated DB, savepoint recovery and full rollback/count/
identity preservation. Missing/disabled/changed guards or permission errors fail.
The immutable upgrade preserves all earlier releases, DB/audit, archive/keys,
unit/socket/credential protections and records. No privileged deployment or live
audit mutation was performed. Real corrected production restore remains pending;
P8 stays IN PROGRESS and no public deployment/phase advancement is claimed.

SMTP is no longer a product dependency or release blocker. Public signup, verification, email reset and invitations are removed. Administrators are locally provisioned; regular developers/testers use scoped access-code sessions. Earlier W002/W006 email requirements are historical and superseded. Original native/CLI identities and sealed bundles remain unchanged.

## W016 — staged runner job and evidence route (2026-11-09)

W016 implements signed job delivery, customer-local launch/upload journals and private evidence ingestion. Launch is granted once per immutable runner/job identity; retries collect the exact native ID or resume the same archive. HTTP cannot read SSH credentials or write evidence. Target quotas, stale authorization, capabilities/mode/build checks and cleanup quarantine are enforced.108 focused tests passed, plus a separate actual migration/legacy encrypted restore roundtrip. The loopback TLS job/upload/ingestion journey uses labeled recorded QNX bytes, not a new native execution. Additional-adapter, actual new-runner QNX/browser, separate-host and immutable production upgrade qualifications remain pending. Production stays3821952; public deployment remains withheld.

## W017 — adapter contract and mailbox source checkpoint (2026-11-09)

The additional mailbox adapter/owned retained-message service and versioned static ABI1 catalog are staged. Explicit matching-generation ACK/message custody is separate from waiter cancellation; public PID/instance metadata does not prove a running build. Missing signal/departure/repeat/ordering qualification is not advertised. Historical deployment parsing now binds an exact known adapter subset, preserving original two-adapter evidence and rejecting missing/unknown files.112 host tests passed in13.833s;119 PG/TLS/dashboard/restore/security tests passed in34.670s. No new native result is claimed at this source checkpoint. The approved lab route was initially stopped; the preserved existing QEMU overlay was started as the unprivileged existing KVM account, with unchanged SSH trust, loopback22220 only and new private console/PID files. Actual read-only df reports267 free file entries/2441 blocks. Native qcc/build/input/runner qualification follows in isolated worktrees, with a bounded file budget and no original-history deletion. Public/production/separate-host/independent gates remain pending.

See [ADAPTER_INTEGRATION.md](ADAPTER_INTEGRATION.md) for build/registration, exact supported scope and evidence requirements.

## W018 — actual local outbound-runner/QNX and browser qualification (2026-11-09)

Production remains3821952; all work below is unprivileged private staging. The owner
confirms no separate customer runner host is available, so that qualification is
blocked on an actual customer environment. A separate runner process on this VPS
used authenticated loopback TLS and the preserved approved QNX guest. Real qcc
builds and independent target readback bind two source candidates: only the owned
mailbox fixture binary differs. Browser-enrolled and explicitly approved work ran
mailbox timeout FAIL, corrected-source replay PASS (comparison fixed), and sensor/job
timeout PASS/PASS. Each has observed native cleanup. An injected HTTP503 interrupted
the replay upload; the retained exact run ID resumed without a second native launch.
Twenty-three real QNX mailbox input/ACK/identity checks passed. Broader mailbox
lifecycle families and arbitrary external-service compatibility remain unsupported.

The initial browser/native driver stopped after all four runs at a test-client CA
trust error during ZIP download; its report remains failed. A presentation-only
continuation imported those exact immutable native IDs as RECORDED and passed
administrator password/TOTP, scoped-code issuance/redemption/revocation, comparison,
authenticated Chrome ZIP download, tenant denial and no-JavaScript mobile checks.
Together the reports contain31 views/13 Axe scans with zero reported violations;
this is automated staging evidence, not independent accessibility or public UAT.
See evidence/runner-native/index.json for precise scope and original reports.

Enrollment now publishes discovered capabilities immediately, changed-inventory
retry is refused, approved customer targets can receive live codes, and external
attachment cannot select fixture controls. Dedicated production runtime/isolation,
separate-host enrollment, actual public HTTPS/auth/native journeys, compatible
rollback and independent acceptance remain pending. P8 stays IN PROGRESS; P9–P10
and public deployment are withheld. AI remains disabled; off-server DR is deferred.

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

The operator-run e1ef88c deployment failed at private_response_cacheable and
reported own_changes_rolled_back:true. The real anonymous /app/ redirect carries
Django no-cache, which permits storage and fails the intended no-store requirement.
The previous synthetic backend incorrectly supplied no-store and missed this case.
The corrected dedicated HTTPS boundary hides upstream cache headers and supplies
no-store for every dynamic response; static public300 remains separate.

Twenty deployment/recovery regressions pass, four actual isolated Nginx/TLS tests
pass, and all13 exact deployment probes pass against real isolated Django and
PostgreSQL (upstream no-cache, boundary no-store). Recovery accepts only the two
known failed drivers after proving their old committed payload hashes and exact
restored originals, preserving backups and driver history. No immutable application
release, secrets or unrelated services changed. The revised single operator
command is still required; real public/browser/native acceptance has not advanced.
P8 remains IN_PROGRESS; P9/P10 are not claimed.

## W024 graceful reload and strict rollback verification

Protected metadata from the operator-run read-only probe confirms8000144 completed
and recorded the dedicated Certbot dry run, then failed its immediate rollback
HTTP check. The original site/http files match both backups and committed bootstrap
bytes, are root:root0644, and have the correct enabled symlink. The own hook is
absent, nginx -T passes/includes the own files, and HTTP returns404. Private
readiness is200; nginx/web/socket are active and web remains resmgr-web on544f22c.
The restoration succeeded. Public TLS currently fails verification, independently
confirmed externally; HTTPS deployment is not passed.

The unit reload only signals Nginx. Actual isolated Nginx reproduces old-worker308
while restored original files already pass nginx -t. W024 replaces the one-shot
assumption with bounded strict verification of exact originals/modes/link, HTTP404
and ACME, and waits for verified TLS after reactivation. Persistent wrong behavior
still fails; failure cleanup now proves HTTP restoration too.27 recovery tests
PASS, five actual isolated Nginx tests PASS. No production modification was made by
the agent. Known failed8000144 recovery retains backups/history and its completed
same-certificate renewal proof; the rollback drill is still required. A new reviewed
operator command is pending. P8 IN_PROGRESS; P9/P10 not claimed.

## W025 Unix proxy identity and immutable authentication recovery

The cf15209 deployment passed local HTTPS/security, dedicated renewal and actual
HTTP rollback/reactivation. Authenticated browser acceptance then failed: its first
administrator POST returned403. Safe evidence shows seven real public views/five
zero-violation accessibility scans; administrator/MFA and codes are NOT_RUN, not
passed. The operator's read-only probe confirms original HTTP404 restored, exact
root0644 files/link, private readiness200, active web/socket/nginx, and successful
temporary-account/code cleanup preserving existing users/audit/evidence. No native
work ran; approved_executor_registry_missing is a distinct production blocker.

Installed allauth65.21.1 requires a valid client IP. Actual Gunicorn26.2.0 Unix-FD
testing confirms REMOTE_ADDR is empty. Nginx overwrites X-Real-IP and strips XFF,
but allauth's default ignores X-Real-IP and denies login before password checking.
The former WSGI fixture incorrectly supplied127.0.0.1, masking this incompatibility.
Production now explicitly trusts only Nginx's overwritten X-Real-IP; missing or
malformed identities still fail closed. MFA, CSRF, DB-cache rate limits and Unix
service isolation remain intact.

61 actual disposable-PostgreSQL authorization/identity/code tests PASS; seven real
Gunicorn FD tests PASS, including empty peer identity. The corrected fixture uses
empty REMOTE_ADDR and passes44 desktop/mobile/no-JS views and12 accessibility scans.
15 recovery tests and one privacy-reporting test PASS; privileged services/backup/
HTTP are modeled, filesystem pointer/history operations are real. No corrected
production release has been activated by the agent. A new immutable application
and reviewed one-command recover_https_auth.py workflow are prepared; see the
updated HTTPS_DEPLOYMENT.md. P8 remains IN_PROGRESS; P9/P10 not claimed.

The committed authentication application is325f367c803b44e2f5ac5f4bb3264a7abfb7f08f.
Its immutable recovery plan passed unprivileged review. Actual current remains544f22c;
use the reviewed driver SHA from the handoff with this application revision.

## W026 password-only administrators and preserved recovery state

W026 implements the approved password-only administrator policy. No enrollment,
MFA login or MFA privileged gate is active; existing authenticators, their encrypted
records, MFA source key and LoadCredential remain intact.15-minute privileged
reauthentication uses the password; sessions have30-minute idle and12-hour absolute
limits. Local provisioning/recovery, hashing, CSRF/origin, rate limits, audit,
revocation and all tenant/project/target/evidence scopes remain enforced. Developer/
jury sessions still use administrator-issued codes without personal accounts.

The previous e6890b0 RuntimeError was original-release validation rejecting untracked/
ignored content, before staging/backup, not an MFA failure. Protected metadata shows
prepared325f367, no backup bound, original544 active/ready200, HTTP404 restored and
old diagnostic data predating this attempt. Unprivileged metadata identifies three
root-owned750 Python cache directories, with no unexpected visible source files.
Root -I ignored environment-only bytecode suppression. New launchers set -B and
sys.dont_write_bytecode. Only caches matching fresh committed-source compilation
may be retained; unknown files, links, unsafe modes or altered payloads still stop
recovery, and nothing is deleted/chmodded. Exact protected cache payload validation
remains an operator-workflow gate, not an observation from unprivileged metadata.

392 web tests PASS in93.974s. Actual isolated Django/PostgreSQL/Gunicorn26.2/Unix/
Nginx/private-TLS browser acceptance PASS in150.878s:46 desktop/mobile/no-JS views,
12 zero-violation scans, password-only login and scoped code management/expiry/
revocation. Actual systemd/new private release/public HTTPS qualification is pending.
The reviewed recovery adopts only the known unstarted prepared attempt with retained
history, creates a new immutable release, preserves old data/keys/receipts and
checks backup/restore/private readiness/isolation before HTTPS. P8 IN_PROGRESS;
no new QNX execution or production-native/customer-host qualification is claimed.

The committed password-only application is3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58.
Its unprivileged immutable recovery plan passed. Actual production is still544f22c;
use the reviewed driver SHA from the handoff. No privileged deployment ran by the agent.

## W027 exact derived-cache proof and recovery correction

W027 confirms55daf08 stopped before staging/backup/service actions at an overly
strict derived-cache comparison. The exact offender was
resmgrcheck/__pycache__/contracts.cpython-312.pyc under immutable544f22c. Original
source/origin and deployment manifest match their recorded identities, and the
original venv binding is verified. The source remains intact. All14 captured
root0640 caches have full SHA256 matches reconstructed from Git-verified source,
header metadata and CPython3.12.3 without reading/importing candidate contents.

The contracts cache matches the second of two identical optimize=0 compilations
with the first code object kept alive. CPython marshal serialization depends on
object reference/sharing context, so one raw representation was not a canonical
integrity check. Two exact trusted compiler outputs are accepted; no candidate
normalization/decoding or optimized-mode bypass is used. The latent zero-length
tracked __init__.py rejection is corrected too. All other source/header/metadata/
path checks remain, with explicit tracked-mode validation and rejection of executable
replacements. Original caches/source, keys, backup/data and history are preserved.

84 relevant tests PASS in10.214s, including actual production hash reproduction,
modified payload/source/header, unexpected directories, symlinks, executable bits,
empty source and interrupted recovery/history. All14 captured cache hashes also
PASS the unprivileged source/header reproducer. Current544 remains active: private
HTTP200/DB SELECT1, own HTTP404 restored, nginx/db/web/socket active, workers inactive.
The3f4bafb application is unchanged and remains unactivated; only the recovery driver
changes. Actual corrected recovery, public HTTPS/password/code acceptance and native
registry/independent qualification remain pending. P8 IN_PROGRESS.

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

## W030 completed provisioning; selector recovery prepared

Operatorce97df9 completed fixed private registry custody, actual executor systemd
probe and exact approval publication. It stopped at exact_approved_native_plan_required
before temporary-principal creation or native queueing. The root coordinator called
a worker-only ownership validator as UID0 on the legitimate executor-owned registry;
that rejection was suppressed into zero candidate pairs. The fixed coordinator now
validates exact IDs/tenant/route/build/proof and executor UID/GID0600 explicitly.
The generic worker ownership policy and immutable application are unchanged.

78 combined tests pass;26 refreshed focused checks reproduce root-context rejection,
strict corrected selection, negative custody/bindings and interrupted journal resume.
Recovery archives the exact ce97 state/failure/proof and reuses completed provisioning
after read-only checks. It refuses native intents, changed private bytes or unknown
state. No reinstall, repeat systemd probe, HTTPS deployment or authentication change.
Current3f4bafb HTTPS readiness200; nginx/db/web/executor active. New production native
IDs remain absent and P8 IN_PROGRESS. See [PRODUCTION_EXECUTOR.md](PRODUCTION_EXECUTOR.md)
and [W030 evidence](evidence/executor-selector-recovery/checks.json).

## W031 web queue mutex correction prepared

Operator885 verified/reused completed provisioning, passed fixed root selection and
reached the native form. The production journal confirms permission denied for table
control_executorslot twice,30.086/30.083s before the browser's TimeoutError. The browser
recorded no run IDs and cleanup closed its account/codes. Confirmation uses a dispatch
mutex that the web role could neither create nor lock under the deployed grant matrix.

The correction precreates its empty row and grants lock-only UPDATE(name), with a
database trigger rejecting every actual web slot update. INSERT/DELETE/table-wide
UPDATE remain unavailable; executor lease writes continue.86 tests passed, including
real Chromium/HTTP/Django/PG reproduction (preview200/confirm500), then guarded positive
confirmation302 without any native launch. No immutable application or Nginx/auth/unit/
key change. New resume archives885 history and requires authoritative zero associated
Run rows plus audited account/code closure; it never trusts an empty browser report
alone. Actual production native/recovery/revocation/cleanup remain pending. Current
3f4bafb readiness200; P8 IN_PROGRESS. See [PRODUCTION_EXECUTOR.md](PRODUCTION_EXECUTOR.md).

## W032 sensor collection blocked

45bde2e passed queue-lock validation and created web run
274989f6-c306-4581-8f69-3db1ca21997d / nativew274989f6c30645818f. Actual browser
POST200/302 and observer-ready metadata are retained. Collection then failed with
unclassified observer ValueError; the native verdict and cleanup are unconfirmed.
No retry/redeployment ran. One read-only protected inspection is pending; the first
operator invocation split the filename and did not run.40 focused tests pass, with
real disposable PostgreSQL/Chromium and modeled service control. Diagnostic code
now retains allowlisted check names and correct step labels. Current3f4bafb HTTPS
readiness200 and own services active. P8 remains IN_PROGRESS; native recovery,
replay/job evidence, rollback and independent UAT remain pending. See W032 in
TEST_EVIDENCE.md and evidence/native-collection-inspection.

## W033 verified partial state; same-ID recovery staged

The operator read-only probe confirms intact inventories/execution but no final
bundle for274989f6-c306-4581-8f69-3db1ca21997d / w274989f6c30645818f. Canonical
ERROR, blocked state, quarantine and held private-qnx lease remain authoritative.
Account/code/session authorization cleanup passed; native cleanup did not. The
recovery branch can seal an old partial ERROR when CLI collect fails. Missing
selected-controller state reproduces the SDK/bootstrap failure before collection
history; its actual absence/child exit2 are checked before operator recovery.

The reviewed root command installs only the already verified controller selector,
collects the same ID into separate private evidence under the actual sandboxed
executor, and requires exact request/build/supervisor/partial-prefix/FAIL and native
cleanup before audited release. Original ERROR and its immutable artifact graph
remain unchanged. Then it resumes one explicitly reviewed dashboard batch; it never
relaunches the original ID. No web/Nginx/authentication/engine source deployment.
89 tests PASS in13.917s, including real archived QNX bytes, disposable PostgreSQL,
Chromium and modeled systemd restoration. Actual root recollection/new batch remain
pending. Current3f4bafb HTTPS200 and own services active. Full app rollback and
independent UAT remain open. P8 IN_PROGRESS; AI/customer endpoints disabled.

## W034 recovery evaluator Git index access

Operator75b3c54 confirmed missing recovery-controller selection, then failed in the
actual executor worker. The read-only follow-up shows the exact approved selector
installed and fresh native collection bytes retained in its separate private directory,
but no usable sealed summary. Original run274989f6-c306-4581-8f69-3db1ca21997d remains
blocked ERROR, quarantined, with its lease held and no recovery audit. Account/codes
remain revoked; original inventory hashes match.

Agent inspection confirms engine .git/index root:root0600; unprivileged evaluator
identity fails at git status with index permission denied. A real temporary Git
reproduction confirms git diff HEAD refreshes the index under umask0077 despite
--no-optional-locks. Explicit diff.autoRefreshIndex=false prevents that write.
The reviewed recovery now guards that setting, verifies the exact failed collection
signature/index tree, journals original metadata, and grants only root:resmgr-exec0640
on the same index inode/bytes. Actual executor Git reads precede native collection.
No source/keys/old evidence overwrite; a fresh recovery output preserves75b3c54's
partial output. Unknown failure signatures or index changes refuse repair.

95 tests PASS in13.548s. Root permission changes/systemd are modeled; real Git,
PostgreSQL, Chromium and archived QNX evidence checks pass. The exact protected
CalledProcessError signature remains a mandatory apply-time check, not an observed
value in the supplied probe. Current3f4bafb HTTPS200, nginx/db/web/executor active,
recovery override absent. Actual corrected recollection/new native acceptance and
rollback/UAT remain pending. P8 IN_PROGRESS; AI/customer endpoints remain disabled.

Independent index-free verification read all4782 tracked engine files against the
pinnedca4f74e Git tree: zero content/type/executable-mode mismatches. It read no
private configuration and did not refresh the index. Tracked source integrity is
intact; the confirmed fault concerns generated Git metadata permissions.

## W035 interrupted-session verification (2026-11-10)

The five correction checkpoints after ce97df9 were already committed; the working
tree was clean on return. Operator confirmation: the latest1fde3df recovery was
not executed. Its unprivileged exact-commit plan passes. The original selector
failure remains a coordinator/worker ownership-context mismatch, not a missing
approval, unsupported operation or schema mismatch. Subsequent operator attempts
encountered the guarded queue mutex, missing controller selection and Git index
access failures documented in W031–W034.

Fresh host observations: current application3f4bafb, HTTPS readiness200 with valid
TLS and expected JSON, nginx/database/web/executor active/running with successful
main-process status. Host index metadata remains root:root0600. The dedicated
recovery override directory is absent. Protected diagnostics/journals and production
SQL were not freshly readable: UID1000 has no noninteractive sudo authorization.
The exact last protected state remains the W034 operator observation: one blocked
ERROR run274989f6-c306-4581-8f69-3db1ca21997d, nativew274989f6c30645818f, held lease,
quarantined target, intact original evidence, approved selector installed, separate
unsealed collection and no recovery audit. Current QNX process liveness/cleanup
cannot be inferred from the healthy executor service.

All95 focused regressions passed in14.709s after fixing streaming static-file
responses in the local Chromium test helper and asserting no failed browser
requests. Real temporary Git/PostgreSQL/Chromium and archived QNX evidence were
used; root custody/systemd remain modeled. No production code changed this turn.
Use the pinned1fde3df recovery command in PRODUCTION_EXECUTOR.md, preserving its
driver identity on retry. Native acceptance, full application rollback and
independent UAT remain pending. Evidence: evidence/native-resume-verification.

## W036 production same-ID recovery and native acceptance passed (2026-11-10)

The operator ran the pinned1fde3df command successfully. Its supplied output records
the exact index repair without source/index byte changes, same-ID recollection of
w274989f6c30645818f with canonical FAIL, original ERROR retained, and a successful
new native acceptance batch. The private final report is
/var/lib/resmgrcheck/private/operator/native-acceptance/report.json. The agent did
not read that protected report or run the privileged command.

| Native ID | Actual result | Evidence |
| --- | --- | --- |
| wbfcf8cf53f354a45b5 | Sensor intentional cancellation defect FAIL | Same supervisor/ID recovered after connection interruption; partial evidence retained |
| w85d0f7bb970a4ca8bc | Sensor timeout corrected-source replay PASS | Canonical comparison fixed; fixture mode stayed ignore-unblock |
| weead18b9841f4ff386 | Job timeout PASS | Session/code revoked during live collection; cleanup verified |

All three runs have verified cleanup, immutable bundle IDs and verified downloads.
Queued web runed8cacad-0717-4cee-a341-ae26cf8e0a8e was rejected before native launch;
it has no native verdict/evidence (NOT_RUN). Temporary account/codes were closed,
no own native work remained active, and prior users/audit/runs/evidence were preserved.
The operator report also records guarded idle executor stop/start PASS and unchanged
HTTPS. Successful harness qualification does not change the intentional FAIL.

The agent read the matching local browser/cleanup reports and checked HTTPS200 with
valid TLS, unchanged3f4bafb pointer, nginx/db/web/executor active/running, repaired
index root:resmgr-exec0640 and no loaded executor drop-in. These host checks are
separate from the operator-run native observations. No production database reread,
new QNX call or repeat acceptance occurred in this documentation turn. W035's95
focused tests remain the applicable regression evidence; no source changed.
See evidence/production-native-acceptance. Full application rollback and independent
UAT remain open; P8 remains IN_PROGRESS and customer endpoints/AI stay disabled.
