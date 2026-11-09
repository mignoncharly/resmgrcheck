# Customer-owned outbound runner, protocol1

Current policy (W026, owner-approved2026-11-09): administrators use username/password
only; MFA is deferred and not enforced. Existing authenticators/encryption keys are
retained. Scoped developer/jury codes, tenant/target/evidence authorization, CSRF,
rate limits, audit and session revocation remain mandatory. Customer machine
endpoints and AI stay disabled. Historical MFA qualification below is not the
current release policy. Actual private release remains544f22c; corrected immutable
activation/public acceptance is pending. See [HTTPS_DEPLOYMENT.md](HTTPS_DEPLOYMENT.md).

Enrollment/heartbeat is implemented and staged (W015), disabled in production.
W016 implements signed jobs, same-ID recovery, bounded upload and private ingestion.
Additional native and separate-host qualification remain pending. No separate customer runner host is available. Actual loopback HTTPS
tests use fixture discovery, not a licensed remote QNX target or public service.

The customer retains their own legally licensed QNX SDK/runtime, SSH identity,
pinned host keys and target routing. No QNX software/license or SSH private key is
distributed or accepted by the central site. Use a dedicated nonroot customer OS
identity and immutable reviewed checkout/venv, with only outbound central HTTPS
and customer-private target connectivity. No inbound runner listener is provided.
The separate customer_runner package uses the pinned cryptography dependency from
web/requirements.lock; the original engine/CLI stays standard-library-only.

A project administrator with recent password authentication creates enrollment under Targets. Privately deliver
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
  "attachment": "managed-fixture",
  "allowed_modes": ["corrected"]
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

## Run approved work

After separate inventory approval and explicit compatible-build approval, map each deployment hash to the customer-local immutable manifest in `manifests`. Only locally allowlisted modes can run; add deliberate defects only in an explicitly owned lab.

```sh
/srv/customer/venv/bin/python -B -m customer_runner work \
  --config /etc/customer-runner/runner.json --state /var/lib/customer-runner
```

Use --once for one poll. The fsynced launch intent precedes the single central grant. Any uncertain result selects exact-ID collect, never run/replay again. A lost upload acknowledgement retries the same immutable archive/chunk; accepted prefixes are journaled. New native results remain withheld until private canonical validation. Missing original local replay evidence, changed route/build/source, revoked authorization, missing capabilities or uncertain cleanup blocks work. Customer operator installation/build/deploy remains local and explicit; the control plane cannot supply shell strings, target addresses or binaries.

## W018 actual qualification and remaining host gate

The representative mailbox and existing sensor/job timeout profiles have now run
through the actual outbound process/HTTPS route on the approved QNX VM. The mailbox
source-defect FAIL and corrected-source replay PASS preserve exact IDs; an observed
upload interruption resumed without native relaunch. This is a same-VPS runner
process, not a separate customer-owned host. The owner has no separate host yet;
install/enroll/approve there before claiming customer deployment qualification. The
central site still does not receive SDK/license/SSH private material. Connection
alone proves neither lifecycle support nor cleanup. Full external lifecycle remains
UNSUPPORTED; external health rejects all fixture-control modes.

## Stable customer-local trust configuration

Use a dedicated owned400/600 SSH config with Host stanzas, explicit pinned public
UserKnownHostsFile and GlobalKnownHostsFile none if no reviewed global pins are
needed. Public pin files may be400/440/600/644 but must be trusted-owner regular
files without group/other write, hardlinks or symlinks, at most1MiB each. Missing
default trust files are fingerprinted as absent; at least one nonempty valid pin
source is required. Actual doctor/strict SSH authentication must still succeed.
No target connection is made by ssh -G itself. The effective settings use the same
fixed strict/BatchMode options as the native transport.

[OpenSSH documents effective configuration](https://www.openbsd.org/openssh/legacy.html)
and the [host-trust directives](https://man.openbsd.org/ssh_config). Match/Include
can make routing command-dependent and are outside this initial runner contract;
prepare a dedicated stable config locally instead. KnownHostsCommand, DNS trust,
canonicalization, multiplexing, RemoteCommand, agent/X11/port forwarding and local
commands are refused. No permissive SSH option is added to recover a failed check.
Use an explicitly reviewed nonempty RevokedHostKeys file if configured; tokenized
trust paths are unsupported. Customer-local ProxyCommand/Jump routing is trusted
configuration, never supplied by a central job, with strict end-target pins retained.

This changes the local route fingerprint for existing staged enrollments. Do not
edit binding.json, discard device/launch/upload journals or silently rebind an old
target. Retain original evidence, revoke the old enrollment and explicitly enroll/
approve a new target identity. When an inherited public pin file is group-writable,
leave the original lab/application file alone: have the customer prepare and verify
a dedicated owned public-pin copy and config. Never copy private SSH keys/licenses
to the central website or repository. Separate-host qualification is still pending.
