# Production web implementation status

Branch: `feature/production-web-ai`. Specification: `3d9048a`.
The published CLI/jury release `ca4f74e` remains independently recoverable.

| Gate | State | Evidence |
| --- | --- | --- |
| P0 baseline/threat model | PASS | Inventory, preserved baseline, dependency/security review, explicit deployment blockers |
| P1 foundation | PASS | 15 pinned/hashed wheel dependencies; real PG migrations, four tests, isolated Gunicorn readiness200 |
| P2 identity/authorization | PASS (staging protocol) | 34 PG-backed tests incl. real verification/TOTP/reset flows, tenant denial, CSRF, session revocation; SMTP delivery not production-verified |
| P3 engine integration | PASS (private staging) | 55 host tests, five actual QNX cases, bounded transport loss/same-ID recovery and real failed-SFTP preflight |
| P4 dashboard | PASS (private staging) | 64 PG-backed tests;104 browser views/26 accessibility scans; four queued views and cancel/unsupported/error forms |
| P5 evidence/sharing | PASS (private staging) | 82 host tests; five HTTP downloads/ten offline views/209 references; immutable inventory and bounded retention |
| P6 AI analysis | IN PROGRESS | Opt-in provider, consent/redaction/citations/budget controls; real provider not configured |
| P7–P10 | NOT_RUN | Must satisfy each gate in order |

Actually running production web features: none. No production hostname/TLS or
ResMgrCheck vhost currently exists. Original engine runtime digest remains
`02b34132312d710a3700cc3347cdc89fa4329c43389732a43a6f41c3f6d05d2b`.
Existing QNX features/evidence remain qualified; this is separate from web execution.
AI provider: not configured or verified. Playback material: genuine saved QNX cases.

External actions observed necessary: root-owned service/account/Nginx provisioning
(noninteractive sudo is unavailable), DNS for the requested hostname, dedicated
transactional email configuration, optional project-consented AI provider setup,
and independent operator UAT. No secrets should be sent in chat. Concrete commands
will be supplied after the relevant install/configuration artifacts are prepared.
Continue implementation/staging without changing unrelated VPS services.
