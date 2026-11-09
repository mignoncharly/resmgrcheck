# One-command HTTPS deployment and production acceptance

Application release:544f22c174ad48e1c8d741db0afdd3bf5b54f947, already active privately.
This procedure publishes that immutable release. It changes no application code,
schema, original credential, SSH route or QNX build. The owner now authorizes the
jury-facing HTTPS deployment while customer-runner endpoints and AI stay disabled.
The earlier requirement to wait for separate customer-host qualification before
any public jury deployment is superseded by that instruction; customer onboarding
itself is still unqualified and disabled. Off-server DR remains deferred, not passed.

## Only operator command

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
audited temporary administrator with a random password and TOTP. Existing user
passwords/MFA and application/MFA/backup keys remain unchanged. New acceptance
credentials are root600 and passed only over an owned pipe to Playwright running
as the repository operator, never root. No credentials/cookies, traces, HARs or
secret screenshots are saved in browser artifacts or printed.

The browser uses the intended public HTTPS origin with normal certificate validation.
It checks real username/password/TOTP, wrong password, password-only denial, code
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
