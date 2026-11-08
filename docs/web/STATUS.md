# Production web implementation status

Branch: `feature/production-web-ai`. Specification: `3d9048a`, superseded for access by the owner-approved administrator/code decision (2026-11-07).
The published CLI/jury release `ca4f74e` remains independently recoverable.

| Gate | State | Evidence |
| --- | --- | --- |
| P0 baseline/threat model | PASS | Inventory, preserved baseline, dependency/security review, explicit deployment blockers |
| P1 foundation | PASS | 15 pinned/hashed wheel dependencies; real PG migrations, four tests, isolated Gunicorn readiness200 |
| P2 revised administrator/code authorization | PASS (private staging) | W007/W009:135 then152 PG tests, concurrent redemption,50 current browser views/17 scans, native revocation/queued denial, MFA-scoped administrator sessions |
| P3 engine integration | PASS (private staging, revised access) | W003 historical recovery/failed-transfer retained; W007 six new actual QNX cases through code sessions, source-corrected replay |
| P4 dashboard | PASS (private staging) | 64 PG-backed tests;104 browser views/26 accessibility scans; four queued views and cancel/unsupported/error forms |
| P5 evidence/sharing | PASS (private staging, revised access) | Immutable inventories retained; W007 selected-evidence/download/comparison/cross-project boundaries and browser denials |
| P6 AI analysis | PASS for disabled-AI release mode; enabled provider NOT_RUN | W006 no-AI native/browser proof, W007 code consent/budgets/revocation tests; dedicated provider unconfigured, no provider functionality claimed |
| P7 customer target story | PASS for documented limited scope | W008:48 PG negative checks; managed fixtures/operator approval only, arbitrary external lifecycle UNSUPPORTED |
| P8 hardening | IN PROGRESS; web startup failing | W009 staging and W010 clone checks retained; W011 temporary in-unit metadata diagnostic prepared; real systemd credential ACL capture/runtime_check/readiness and later production gates pending |
| P9–P10 | NOT_RUN | Independent operator UAT and release/public deployment gates remain |

Actually running production web features: none. A later read-only check found DNS
now resolves, but no matching enabled ResMgrCheck vhost and no verified HTTPS health
response. This task made no DNS/Nginx change. Original engine runtime digest remains
`02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b`.
Existing QNX features/evidence remain qualified; this is separate from web execution.
AI provider: not configured or verified. Playback material: genuine saved QNX cases.

External actions observed necessary: root-owned service/account/Nginx provisioning
(noninteractive sudo is unavailable), public vhost/TLS verification, optional project-consented AI provider setup,
and independent operator UAT. No secrets should be sent in chat. Concrete private preparation commands are now in PRIVATE_INSTALL.md; their actual
successful root execution and the later security/release gates remain pending.
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

W011 supersedes W010's empty-install observation: the operator retry reached web
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

SMTP is no longer a product dependency or release blocker. Public signup, verification, email reset and invitations are removed. Administrators are locally provisioned; regular developers/testers use scoped access-code sessions. Earlier W002/W006 email requirements are historical and superseded. Original native/CLI identities and sealed bundles remain unchanged.
