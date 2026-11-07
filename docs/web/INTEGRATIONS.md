# Private operator integrations

Never paste credentials or protected files into chat. Use dedicated ResMgrCheck
accounts; do not borrow another VPS application's database/mail/provider secrets.

## Authentication has no SMTP dependency

The approved administrator/access-code decision in ACCESS_MODEL.md replaces the
former registration/email model. Do not configure SMTP for ResMgrCheck. Previous
SMTP setup requests are canceled. Public signup, verification, invitations and
email password reset are removed. Legacy private SMTP entries are ignored and
never loaded into the application's environment; their values are not printed.

Provision administrator usernames locally with the protected command documented
in OPERATIONS.md. Administrators use passwords plus MFA; developers/testers redeem
scoped codes into browser sessions without accounts. Code secrets are shown only
once and cannot be recovered from the server. Recovery is a protected local server
procedure, never email. No user should send credentials or codes in chat.

Private staging remains at http://127.0.0.1:8431; reach it only through the operator's
existing SSH forwarding route. It is not production HTTPS. An example forwarding
command is `ssh -L 8431:127.0.0.1:8431 mignon@YOUR_VPS`; use your actual route locally.

## Optional AI

No provider key/model is currently configured or verified. The optional P6 adapter
uses OpenAI Responses at the fixed HTTPS endpoint api.openai.com; it has no tools,
arbitrary endpoints, execution or patch/deployment permission. A dedicated AI worker
reads a separate0600 file `.local/web/runtime/ai-provider.json`. The HTTP service
reads only the worker's nonsecret recorded policy, never this file's credential.
Create this file locally if you want real provider qualification; do not send its
contents in chat. These are field names/placeholders:

```json
{
  "provider": "openai",
  "model": "YOUR_ENABLED_STRUCTURED_OUTPUT_MODEL",
  "api_key": "CONFIGURE_LOCALLY_ONLY",
  "input_microusd_per_million": 1000000,
  "output_microusd_per_million": 4000000,
  "global_daily_microusd": 500000,
  "request_cap_microusd": 100000,
  "pricing_reviewed_at": "2026-11-07"
}
```

Use your actual enabled model and verify its current standard input/output prices
at https://developers.openai.com/api/docs/pricing before setting conservative
ceilings. Units are millionths of USD per million tokens:1000000 means USD1 per
million tokens, not USD1 per token. The example ceilings cover the currently
documented gpt-4.1-mini prices (USD0.40 input/USD1.60 output per million tokens,
checked2026-11-07); this is not an account-access guarantee or a claim all models
fit those rates. Use a model supporting Responses structured JSON output. No model
is silently substituted. Prices must be reviewed within30 days; configured daily
global maximum is at mostUSD2 and per-request maximum at mostUSD0.10. The example
daily global ceiling isUSD0.50. Set an additional provider-project billing limit.

Enabling configuration does not send data. The project must separately opt in with
a nonzero daily budget, and an authenticated developer must review the exact redacted
payload and consent per request. Real qualification will use only this project's
existing genuine test evidence plus reviewed original MIT source, not unrelated
customer/private files. All native verdicts remain unchanged. store:false is used,
but it is not a zero-retention promise: provider abuse-monitoring/account policies
still apply; see https://developers.openai.com/api/docs/guides/your-data.

The provider response has a25-second total owned-child bound (20-second socket
timeout),1600 output-token limit, no automatic retry, exact citation checks and
conservative transactional reservations. Provider usage permits an estimate at
configured ceilings, not invoice verification. A failed/uncertain call retains its
reservation. Missing provider configuration leaves deterministic testing usable.
No unrelated application's API keys or accounts are accessed.

## Administrative deployment and UAT

Noninteractive sudo is unavailable. Dedicated production accounts, database/service
permissions, Nginx/TLS and backups require an administrator to run the prepared
installation steps after the applicable gates. DNS changes for the requested new
hostname wait for readiness. Independent operator UAT is a distinct P9 gate;
agent-driven tests do not claim it. No password or private config disclosure is needed.
