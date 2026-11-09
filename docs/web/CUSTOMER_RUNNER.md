# Customer-owned outbound runner, protocol1

Enrollment/heartbeat is implemented and staged (W015), disabled in production.
Job delivery/evidence ingestion and additional-adapter qualification are the next
checkpoints. No separate customer runner host is available. Actual loopback HTTPS
tests use fixture discovery, not a licensed remote QNX target or public service.

The customer retains their own legally licensed QNX SDK/runtime, SSH identity,
pinned host keys and target routing. No QNX software/license or SSH private key is
distributed or accepted by the central site. Use a dedicated nonroot customer OS
identity and immutable reviewed checkout/venv, with only outbound central HTTPS
and customer-private target connectivity. No inbound runner listener is provided.
The separate customer_runner package uses the pinned cryptography dependency from
web/requirements.lock; the original engine/CLI stays standard-library-only.

An MFA project administrator creates enrollment under Targets. Privately deliver
the one-time600s credential; save it locally in an owned0600 regular file, never
argv/URL/chat. Compare the displayed public server key via a trusted channel.
Create an absolute owned0600 configuration with this schema (replace placeholders
locally; neither private configuration nor token belongs in Git):

```json
{
  "origin": "https://qnx-resmgrcheck.gestionatech.de",
  "server_public_key": "<64 lowercase hex public Ed25519 key>",
  "target_id": "<enrollment target UUID>",
  "organization_id": "<approved organization UUID>",
  "project_id": "<approved project UUID>",
  "engine_root": "/srv/customer/resmgrcheck-engine",
  "target_config": "/etc/customer-runner/target.json",
  "alias": "customer-qnx",
  "manifests": {},
  "attachment": "managed-fixture"
}
```

Use the existing CLI guide to configure the customer's local target/SSH route.
Strict host-key verification is mandatory. Real doctor discovery must establish
reachability/compatibility/transfer/compiled capabilities. Its public identity and
capability facts are signed; routing/SSH configuration contents never leave the
runner. Local configuration hashes pin the route; changes require a new target
identity. `manifests` maps deployment hashes to approved existing local manifest
files; no remote executable path is trusted. Managed-fixture mode authorizes only
owned test fixtures. external-attach permits only supported read-only health;
missing lifecycle instrumentation is UNSUPPORTED.

From the immutable runner checkout, after installing the pinned dependency:

```sh
/srv/customer/venv/bin/python -B -m customer_runner enroll \
  --config /etc/customer-runner/runner.json --state /var/lib/customer-runner \
  --enrollment-file /etc/customer-runner/enrollment
/srv/customer/venv/bin/python -B -m customer_runner heartbeat \
  --config /etc/customer-runner/runner.json --state /var/lib/customer-runner
```

Output is limited to public fingerprints/state and explicit no-native-test status.
Compare it with the project administrator before separate exact-inventory approval.
A lost enrollment response can retry only with the same device key before expiry.
Preserve device-key, binding and future job journals across reconnection; do not
copy them across customers or delete them to relaunch. Unknown occupied files and
changed bindings are refused. Revocation is permanent and preserves audit/evidence.

TLS/hostname verification is always enabled, with no redirects or inherited HTTP
proxies. An explicit private CA bundle can be supplied with --ca-file for isolated
testing; there is no insecure TLS option. Server-key rotation needs out-of-band
review and explicit re-pinning. Application/MFA/backup keys remain separate from
the new runner signing key. Enrollment/heartbeat alone cannot execute anything.
