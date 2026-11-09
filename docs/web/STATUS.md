# Production web implementation status

Branch: `feature/production-web-ai`. Specification: `3d9048a`, superseded for access by the owner-approved administrator/code decision (2026-11-07).
The published CLI/jury release `ca4f74e` remains independently recoverable.

W015 baseline inventory (2026-11-09): source and actual installed pointer were
3821952e6c99cf8c6d548e59301166dde590b8a0. The operator confirms private HTTP200,
nonroot systemd runtime checks and an actual encrypted isolated restore with audit
UPDATE/DELETE rejection. These successful gates are accepted as operator evidence,
not unnecessarily repeated or relabeled as agent execution. Read-only metadata
confirms private web/socket/DB active and executor/backup timer inactive. External
fetch could not access the requested HTTPS URL; public HTTP/TLS remain unverified.

The expanded A–F scope is implemented in private staging through W020: outbound
enrollment/jobs/private ingestion, actual mailbox source-corrected QNX replay,
sensor/job route regression, browser MFA/codes/comparison/download/mobile checks,
stronger customer-local SSH trust binding and reviewed immutable upgrade commands.
Production enrollment stays disabled. The owner confirms no separate customer
runner host is available yet; implement/stage now, qualify that host later. Public
TLS currently fails hostname verification. P8 is IN PROGRESS; public/independent
acceptance and actual new-release root activation/isolation/rollback remain pending.

| Gate | State | Evidence |
| --- | --- | --- |
| P0 baseline/threat model | PASS | Inventory, preserved baseline, dependency/security review, explicit deployment blockers |
| P1 foundation | PASS | 15 pinned/hashed wheel dependencies; real PG migrations, four tests, isolated Gunicorn readiness200 |
| P2 revised administrator/code authorization | PASS (private staging) | W007/W009:135 then152 PG tests, concurrent redemption,50 current browser views/17 scans, native revocation/queued denial, MFA-scoped administrator sessions |
| P3 engine integration | PASS (private staging, revised access) | W003 historical recovery/failed-transfer retained; W007 six new actual QNX cases through code sessions, source-corrected replay |
| P4 dashboard | PASS (private staging) | 64 PG-backed tests;104 browser views/26 accessibility scans; four queued views and cancel/unsupported/error forms |
| P5 evidence/sharing | PASS (private staging, revised access) | Immutable inventories retained; W007 selected-evidence/download/comparison/cross-project boundaries and browser denials |
| P6 AI analysis | PASS for disabled-AI release mode; enabled provider NOT_RUN | W006 no-AI native/browser proof, W007 code consent/budgets/revocation tests; dedicated provider unconfigured, no provider functionality claimed |
| P7 customer target story | IN PROGRESS for A–F scope | W018 actual same-host outbound/QNX mailbox replay + sensor/job; separate customer host pending |
| P8 hardening | IN PROGRESS; private runtime/restore passed (operator) | Active3821952; remaining HTTPS/auth/native/rollback and new runner security gates pending |
| P9–P10 | NOT_RUN | Independent operator UAT and release/public deployment gates remain |

The private web service/socket are active at3821952 (read-only unit observation).
Private HTTP/runtime/restore success is operator-provided; public HTTPS is unverified.
This task made no DNS/Nginx change. Original engine runtime digest remains
`02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b`.
Existing QNX features/evidence remain qualified; this is separate from web execution.
AI provider: not configured or verified. Playback material: genuine saved QNX cases.

Remaining work: separate
customer-runner acceptance, intended HTTPS auth/native/browser/isolation/rollback
and later vhost/TLS/operational verification,
optional project-consented AI provider setup and independent UAT. No secrets should
be sent in chat. PRIVATE_INSTALL.md gives the concrete operator-only procedure.
Continue implementation/staging without changing unrelated VPS services.

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
