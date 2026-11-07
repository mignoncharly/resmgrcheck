# Private operator integrations

Never paste credentials or protected files into chat. Use dedicated ResMgrCheck
accounts; do not borrow another VPS application's database/mail/provider secrets.

## Transactional email required before production onboarding

Staging currently writes messages only into private local files. Real signup,
verification and password-reset protocols pass tests, but external delivery is
not yet verified. Configure a dedicated SMTP sender locally by adding these keys
to the existing0600 file `.local/web/runtime/operator-settings.json`, preserving
its engine/registry path entries:

```json
{
  "RMC_WEB_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
  "RMC_WEB_EMAIL_HOST": "your-provider-host",
  "RMC_WEB_EMAIL_PORT": "587",
  "RMC_WEB_EMAIL_TLS": "1",
  "RMC_WEB_EMAIL_USER": "your-dedicated-account",
  "RMC_WEB_EMAIL_PASSWORD": "configure-locally-only",
  "RMC_WEB_FROM_EMAIL": "your-verified-sender"
}
```

These are field names/placeholders, not working credentials. The application will
not mark delivery or an account's email ownership verified from this file existing.
The staged application must restart with that configuration, send an actual message
and have its verification link completed. Production secrets will move to dedicated
root-controlled runtime files/credentials during the gated installation.

The current private staging URL is `http://127.0.0.1:8431`. An authorized operator
can reach it through their existing SSH route with local forwarding, for example
`ssh -L 8431:127.0.0.1:8431 mignon@YOUR_VPS`. Use your real route outside chat. The
loopback HTTP staging endpoint is not production HTTPS and is not publicly exposed.

## Optional AI

No provider key or model is currently configured/verified. Provider integration
and consent/budget controls are P6 work. Configure any later dedicated provider
credential locally using the documented P6 keys once implemented. Disabled AI must
never prevent native testing. No existing unrelated provider account is accessed.

## Administrative deployment and UAT

Noninteractive sudo is unavailable. Dedicated production accounts, database/service
permissions, Nginx/TLS and backups require an administrator to run the prepared
installation steps after the applicable gates. DNS changes for the requested new
hostname wait for readiness. Independent operator UAT is a distinct P9 gate;
agent-driven tests do not claim it. No password or private config disclosure is needed.
