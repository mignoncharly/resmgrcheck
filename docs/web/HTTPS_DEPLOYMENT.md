# One-command HTTPS deployment and production acceptance

W028 current state: application `3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58` is active
at https://qnx-resmgrcheck.gestionatech.de. The operator completed driver
`1ee18b6be6084e7e8dd7036a52947374a288b27f`. Production HTTPS password/code/browser
acceptance passed; independent public-page retrieval returned HTTPS 200. Native
acceptance passed root selection and then stopped at a web dispatch-mutex permission
error (W031). Its guarded database correction and executor-only resume are prepared.
Independent authenticated acceptance is still pending. P8 is IN PROGRESS. Customer-runner
endpoints/AI remain disabled; off-server disaster recovery is deferred.

**Do not repeat the completed deployment to address the native registry blocker.**
The application remains healthy; this blocker is a separate executor acceptance
gate. Follow the reviewed new driver in PRODUCTION_EXECUTOR.md, preserving the
completed registry/probe/approvals and all recovery history.
See [the W028 evidence](evidence/production-password-acceptance/checks.json).
The next separate operator workflow is [PRODUCTION_EXECUTOR.md](PRODUCTION_EXECUTOR.md);
it does not rerun this HTTPS deployment.
The following recovery procedure is retained for operator-reviewed recovery/rollback,
not a request to rerun the completed attempt. Original release `544f22c` and protected
receipts remain preserved; no cleanup/reset of their state is authorized.

## Retained procedure: immutable authentication recovery

Do not repeat the old application/driver command. W026 adopts the owner's approved
username/password-only administrator policy: MFA is deferred, with existing
records and encryption keys retained. Developer/jury access remains scoped codes.
No registration/email route is added. Password hashing, recent-password privileged
checks,30-minute idle/12-hour absolute session expiration, revocation, CSRF/origin,
shared rate limits and audit remain required.

The previous e6890b0 recovery failed at original-release validation before staging
or backup: strict Git inventory rejected untracked/ignored content. Metadata shows
root-owned750 __pycache__ directories left in the original release. The root Python
-I invocation ignored PYTHONDONTWRITEBYTECODE. This failure was independent of MFA.
New root launchers use -B and set sys.dont_write_bytecode before repository imports.
Retained caches are never imported/unmarshaled for validation or deleted/chmodded:
header/tag/owner/type/link/size/source binding and exact marshal payload must match
fresh compilation of the committed source. Any unrelated file or mismatch still
fails closed and is preserved. Actual protected cache equality is checked/receipted
by the operator workflow; source metadata alone does not prove cache integrity.

W027 now proves the protected cache contents, not just their metadata. The read-only
operator probe verified original source/origin, manifest identity/SHA and venv binding.
All14 root0640 cpython-312 caches match full-file hashes reconstructed from the exact
Git source, timestamp header and CPython3.12.3. The failing contracts.pyc is46918 bytes,
SHA256116ccaf3a6158dafae68f192f249286ce000275553c4eee0c67d2adc9c3084a1.
It matches a second identical optimize=0 compilation with the first code object still
alive. The first marshal payload is46887 bytes; the second is46902. The old validator
incorrectly required just the first representation. This is a serialization-context
false positive, not modified source, an optimized-mode waiver or permission to trust
arbitrary bytecode. The probe's optimize=1 match did not establish an optimized origin;
the actual complete hash is reproduced at optimize=0.

The fix compares raw candidate bytes only to these two freshly generated trusted
payloads. It never decodes, normalizes, unmarshals or executes candidate bytecode.
Tracked empty __init__.py files are valid; Git membership/mode, source bytes,
ownership/regular-file/link checks, exact interpreter tag/magic, header and all byte
comparisons remain required. Unexpected cache directories, symlinks, changed source,
executable replacements and every unrecognized payload are refused and retained.
Source files/caches are neither deleted, overwritten nor chmodded.

The known55daf08 attempt can transition only with the same3f4bafb application,
original544 current, phase prepared_after_reviewed_password_policy, step
original_release_validation and no bound/verified backup. Its exact journal is
retained under auth-upgrade-55daf0882e17c69ffcf0e5f43312c43856f571c2.json. Interrupted
history publication is resumable without losing the original receipt. All cache
checks run again before staging, backup or service actions. Other histories/states
are not adopted. Authentication, Nginx payloads, units, packages and native permissions
are unchanged by this correction. See evidence/bytecode-recovery for the metadata,
exact-hash reproducer and tests; W027 replaces W026's pending cache proof.

The prepared325f367/e6890b0 attempt can transition only while original544 is still
current, no backup was bound/verified and its phase is exactly prepared. Its exact
journal is retained under a protected historical name; unknown states cannot be
adopted. New source scope names only the reviewed authentication/policy/interface
files plus tests/docs/ops; migrations, units, dependencies, engine and target/build
registrations stay frozen. No policy change is applied to the old immutable tree.

The X-Real-IP correction remains: Gunicorn's Unix REMOTE_ADDR is empty, so allauth
uses only the header overwritten by dedicated Nginx from its original peer. XFF
and Forwarded stay stripped; missing/malformed identities fail closed. See pinned
65.21.1 implementation and [allauth proxy/rate-limit configuration](https://docs.allauth.org/en/dev/common/rate_limits.html).

The agent completed review, unprivileged tests and a read-only plan. The operator
already ran this procedure with application3f4bafb/driver1ee18b6 successfully in W028.
The parameterized command below is historical recovery reference only:

```sh
sudo /usr/bin/python3 -I -B \
  /home/mignon/projects/resmgrcheck/web/ops/production/recover_https_auth.py \
  --release 3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58 \
  --driver-revision REVIEWED_FULL_DRIVER_SHA \
  --apply
```

This stages a separate release and validated shared pinned venv, preserving the
original544 directory. A fresh dedicated encrypted snapshot and isolated restore
are bound to a protected auth-upgrade receipt; verified same-snapshot proofs are
checked and reused on retry. Only the dedicated web/socket are stopped for an
atomic pointer switch. Units, their isolation, key/config files, schema/grants and
native routes stay unchanged. A root-only runtime helper checks no pending migrations,
the configured peer identity and new immutable static assets; it does not migrate.
Actual nonroot runtime_check and private HTTP200 must pass before HTTPS is attempted.

The known rolled-back cf15209 record must match its committed candidate, original
backups/files/modes/link and actual HTTP404/ACME. Its history and completed same-cert
renewal proof are retained. The receipt is explicitly rebound to the new immutable
application/driver, requiring the HTTPS rollback drill again. No state is deleted
or reset to bypass a check. Existing acceptance accounts/codes stay disabled and
their audits/evidence remain. On a known failure, own HTTPS rollback is verified,
then the original private pointer/service is restored and checked. Unknown edits
cause review/refusal. Interrupted stages/new releases are retained; retry the same
command/SHAs without overwriting unknown resources.

The command then runs the existing strict TLS/security/renewal/rollback/browser
workflow. Password POST statuses and precise safe stages are recorded without
contents. Safe operator cleanup metadata is published even on browser failure.
Missing native registry remains BLOCKED, never automatically provisioned. No QNX
permissions/credentials are changed. Customer endpoints/AI remain disabled.

For an explicitly reviewed rollback of this correction, use the same command
with --rollback added. It first restores/verifies own HTTP-only configuration,
then restores the original private release and verifies readiness/runtime. Both
releases, backup/restore receipts, keys, all DB records and evidence remain intact.
Actual corrected production acceptance and this new release rollback are pending;
modeled recovery tests do not complete either qualification.

## Historical HTTPS-only command (superseded for544f22c)

The agent runs source review, unprivileged tests and the read-only plan. The operator
runs this one command locally with the exact reviewed driver commit from the handoff:

```sh
sudo /usr/bin/python3 -I /home/mignon/projects/resmgrcheck/web/ops/production/deploy_https.py \
  --release 544f22c174ad48e1c8d741db0afdd3bf5b54f947 \
  --driver-revision REVIEWED_FULL_DRIVER_SHA --apply
```

No password, token, key or private configuration belongs in chat. The existing sudo
prompt stays on the server. No separate nginx -t, file-copy, reload, readiness,
Certbot or browser-diagnostic commands are required. The command prints safe step/
result JSON and periodic browser progress. Allow several minutes for renewal and
actual clock-based code expiry. Failure returns nonzero and a controlled failed_check;
retain its protected reports. Reply with the safe summary only. The agent can read
the operator-owned browser/cleanup evidence and verify public HTTPS externally.

The script takes its config from committed reviewed renderers, not the mutable
664 /tmp/resmgrcheck-https.candidate. The candidate was reviewed; finalized changes
include security headers on errors, preservation of evidence sandbox headers,
POST-only MFA/login/code rate limiting, raw peer-IP handling, explicit cache/
buffering protection, confidential logs and persistent HTTP ACME routing.

## Automatic deployment checks and scope

The helper verifies exact source/application ancestry, clean tracked source,
unchanged application/dependencies/units, expected active release and known enabled
site link. Root preflight checks current-invocation runtime_check/nonroot process
facts, canonical unchanged units without drop-ins, private socket identity/mode,
runner/AI disabled context, immutable static CSS, dedicated trusted certificate/
key match/ownership/permissions/expiry, exact Certbot webroot renewal and active
existing timer. No app/DB/QNX service is restarted to repeat a successful gate.

Existing own logs are validated by descriptor; eligible legacy public-read modes
are tightened without reading/truncating/chowning them or broadening0600. This
privacy correction persists across rollback and touches no unrelated log.

An exclusive protected deployment lock guards:

- /etc/nginx/sites-available/qnx-resmgrcheck.gestionatech.de
- /etc/nginx/conf.d/resmgrcheck-security.conf
- /etc/letsencrypt/renewal-hooks/deploy/resmgrcheck-nginx

The first two existing files must match the reviewed bootstrap or the helper's
own recorded completed files. An occupied unknown hook is refused. Root600 original
backups and completion/failure records live under
/var/lib/resmgrcheck/private/operator/https-deployment (root700). Unrelated Nginx
files and links are inventoried before/after; their bytes are never printed or
replaced. The existing enabled symlink remains. Config publication is atomic,
nginx -t must pass, and only then may Nginx gracefully reload. No firewall, DNS,
other vhost, PostgreSQL, SSH/QNX or application-unit change occurs.

Verified local HTTPS probes bound their deadlines/body sizes and verify trust and
hostname with no redirects/proxies/TLS bypass. They check landing/readiness/login/
access/private denials, disabled runner routes, exact static CSS hash, secure/HttpOnly/
SameSite cookies, CSRF denial, body bounds (isolated qualification), authentication
rate limiting and headers on errors. A random nonsecret marker proves confidential
access/error logging. A new uniquely owned HTTP ACME probe is removed only if its
exact inode/bytes still match; unknown challenge files are never deleted.

Certbot2.9 dry-run targets only this certificate, with directory hooks suppressed
and no production key/certificate rotation. Configured pre/post/deploy commands
require separate review rather than executing arbitrary hooks. Its own deploy hook
is installed for future renewals and does nothing for other lineages/domains;
nginx -t precedes its reload. The existing Certbot timer/service is not changed.
Dry-run and isolated hook tests do not claim an actual future renewal event passed.

## Actual rollback drill and failure recovery

Before authenticated acceptance, the command restores only its original site/http
settings/hook, validates/reloads, verifies the original HTTP404 and working ACME
route, then reinstalls/validates/reloads and rechecks HTTPS. Private release544f22c,
its service/database/keys and all unrelated vhosts stay unchanged. This qualifies
HTTPS-configuration rollback; it is not a live database restore or application
schema downgrade. The already successful encrypted isolated DB restore is preserved.

On failure, only known owned changes are rolled back, with another nginx -t before
reload. Unknown concurrent edits or unrelated-config drift cause refusal instead
of overwriting another operator's work; the report says rollback requires review.
Interrupted initial backups are reused only if protected/exact. Same-command retries
retain receipts and original backups. Completed renewal/browser proofs are reused;
new native approval can justify another acceptance attempt. Never delete state,
backups or unknown resources to force retry. A different driver commit is a new
review boundary. The narrowly reviewed W023 recovery accepts only the known failed
f8a6009/e1ef88c/8000144 drivers after exact originals are restored. Their recorded candidate
hashes must match their own committed configuration examples and the application
release must remain identical. Only then may the reviewed descendant install its
corrected candidate. Previous records and original backups remain intact; verified
deployments, unknown candidates and concurrent edits cannot use this recovery.

Dynamic HTTPS responses always carry Cache-Control: no-store, including anonymous
private-route redirects whose Django response supplies only no-cache. Upstream
cache headers are hidden. Static assets retain their separate public300 policy.
W023 tests the exact deployment probes against real isolated Django/PostgreSQL/
Nginx as well as the synthetic backend; the earlier fixture missed this redirect.

W024 corrects rollback verification after the8000144 attempt. Its protected record
confirms the dedicated Certbot dry run completed before the rollback drill failed.
Read-only inspection proves original site/http bytes, hashes, root0644 permissions,
enabled link, absent own renewal hook, nginx -T and actual HTTP404 are correct;
private readiness remains200. The old driver did not record the first probe's
status, so its exact historical response cannot be recovered.

The installed nginx unit's ExecReload sends a reload signal and returns before
new workers necessarily serve requests. The former immediate single HTTP check
can observe an old HTTPS redirect despite correctly restored files. The new check
first proves exact original files/modes/link, then makes at most six fresh HTTP
requests with one-second intervals and four-second socket timeouts, requiring404
without redirect plus an actual unique ACME probe.
Persistent wrong routing, wrong files/modes, failed ACME or unknown edits still
fail. HTTPS reactivation uses bounded verified-TLS probes as initial activation
already did. Failure cleanup and explicit rollback now verify restored behavior
too; success is not inferred merely from restoring files or a reload exit0.

Safe status-only observations are retained in protected state and failure JSON,
including separate drill/final restoration observations. The known rolled-back
8000144 driver can transition through the same reviewed hash/originals/history
checks; no state reset is needed. A completed renewal proof is retained and reused
only while the certificate hash matches. The rollback drill remains required.

If protected inspection is needed, inspect_https.py is read-only and emits only
metadata, booleans and health status. Agent access still requires actual local
sudo authorization; terminal-scoped sudo caching may require the operator to run
the single probe. Never paste protected state, diagnostics or configurations.

If explicitly needed after a successful rollout, the one rollback command is the
same reviewed command with --rollback added:

```sh
sudo /usr/bin/python3 -I /home/mignon/projects/resmgrcheck/web/ops/production/deploy_https.py \
  --release 544f22c174ad48e1c8d741db0afdd3bf5b54f947 \
  --driver-revision REVIEWED_FULL_DRIVER_SHA --apply --rollback
```

It restores the pre-HTTPS HTTP-only ResMgrCheck host and leaves its ACME route,
private service, DB, all evidence and keys intact. Other sites remain unchanged.

## Automated real-HTTPS acceptance

After TLS/readiness/rollback pass, the local root coordinator appends an isolated,
audited temporary administrator with a random password and no new authenticator. Existing user
passwords/MFA and application/MFA/backup keys remain unchanged. New acceptance
credentials are root600 and passed only over an owned pipe to Playwright running
as the repository operator, never root. No credentials/cookies, traces, HARs or
secret screenshots are saved in browser artifacts or printed.

The browser uses the intended public HTTPS origin with normal certificate validation.
It checks real username/password login, wrong-password denial, deferred MFA routes, code
issuance/redemption, project/admin scope, active-session revocation, usage limits,
actual short-code expiry, secure cookies, hostile-origin CSRF, desktop/mobile/no-JS
pages and accessibility. Thirty-minute idle and12-hour absolute session duration
remain unit-qualified unless actually waited; the report distinguishes them.

Native testing uses only an already registered operator-approved managed lab and
an unambiguous approved before/defect and after/corrected/fixed source-build pair.
The source hashes must differ, both manifests must match the existing private
registry, and no existing work/slot may be active. No SSH keys/host are copied,
new route blessed, fixture binary rebuilt or external service restarted. Missing
or ambiguous custody/approval is BLOCKED with a safe reason, never fabricated PASS.
Only then may the dedicated executor start if it was inactive. The dashboard/code
session must produce sensor source-defect FAIL, same-contract corrected-source replay
PASS, sensor PASS and job PASS; the canonical comparison badge must be fixed.
Status polling and downloads verify exact native IDs, original verdicts/cleanup,
export member hashes and bounded archive sizes. A timeout never submits a second run.
The mobile client inspects those same real results without JavaScript.

Finally, only the temporary account/codes/sessions are disabled/revoked; its audit,
runs and immutable evidence remain. Interrupted intents are reconciled by protected
receipt plus creation audit. A newly started executor stops only after no work is
active; uncertainty is retained for same-ID recovery. Nothing guesses QNX PIDs or
claims cleanup from a restart. A missing native route does not convert successful
browser checks into complete production acceptance.

Safe browser evidence/cleanup metadata is written under the operator-owned700
.local/web/evidence/production-https-UUID directory. Root diagnostics and receipts
remain protected. The agent verifies the intended URL from an independent external
client afterward. External health, existing-administrator independent UAT and real
native evidence must be recorded before applicable P8–P10 gates can pass.

## Qualification references

W021 evidence is under evidence/https-rollout. Isolated tests include actual Nginx/
TLS/Unix proxy and Django/PostgreSQL/browser flows; modeled root/file recovery is
explicitly separate. The rehearsal uses a private fixture CA/SPKI pin and Node CA
trust; production CLI offers no insecure-TLS switch. No rehearsal executes QNX or
writes production data.

[Nginx header inheritance](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header)
requires repeated headers in the static location on1.24; the1.29 inheritance API
is deliberately unused. [Nginx real-IP variables](https://nginx.org/en/docs/http/ngx_http_realip_module.html)
explain retaining the original peer despite global trusted-proxy processing.
[Certbot renewal documentation](https://eff-certbot.readthedocs.io/en/stable/using.html#renewing-certificates)
is cross-checked against installed2.9 CLI/source for the exact flags used here.

## W033 HTTPS preserved

HTTPS/readiness remain200 on3f4bafb. Current blocker is a sealed native collection
ERROR and held executor lease, not TLS/authentication. Use only the reviewed
executor recovery in PRODUCTION_EXECUTOR.md; do not rerun HTTPS deployment. Actual
native recovery/acceptance, full application rollback and independent UAT remain open.
