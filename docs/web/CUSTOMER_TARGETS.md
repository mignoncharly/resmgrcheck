# Supported target onboarding

W015 stages the actual outbound enrollment/approval/heartbeat workflow described
in [CUSTOMER_RUNNER.md](CUSTOMER_RUNNER.md), replacing the request-only form when
the reviewed runner feature is activated. It is currently disabled in production.
Job delivery/evidence ingestion, additional-service native qualification and a
separate customer runner remain subsequent gates. The supported active release
scope below stays accurate until those gates pass; enrollment is not lifecycle
support or a connection proof for an arbitrary external resource manager.

This release supports operator-approved sensor/job fixtures on a private QNX8.0.0
x86_64 lab. The web executor reuses the qualified CLI and adapters. Public evidence
playback requires no target or code and grants no execution permission. Access
codes select existing approved target UUIDs; they never accept host credentials,
shell commands or a target address from a browser.

| Target mode | Actual scope |
| --- | --- |
| Managed fixture lab | Two qualified sensor/job adapters; deterministic native lifecycle evidence and source-candidate replay |
| Customer onboarding request | Records an unsupported request only; no connection, process or capability claim |
| Explicit external health | Operator-only approved fixed route/profile; read-only service health, running build/instance identity unknown |
| Arbitrary external lifecycle | UNSUPPORTED; no implemented general pending/unblock/identity observer |

An organization administrator can request a dedicated runner from Project → Targets.
Supplying `approved`, `binding`, `hostname` or command fields cannot approve it or
select a host. The request remains UNSUPPORTED until a local operator independently
provisions a tenant-specific route, pinned host key and compatible build. A browser
candidate-manifest import is also an unapproved proposal, not permission to deploy
or execute binaries. Never give a customer's code access to another tenant's lab.

## Operator procedure

The customer must supply their own properly licensed QNX SDK/runtime and compatible
private target. The public site does not distribute QNX software or licenses. Use
their isolated runner/network and authenticated SSH/SFTP route; validate host keys
out of band. Do not disable host-key checking or expose guest SSH to the internet.
The currently implemented executor is one serial private runner, not an outbound
customer-agent fleet. Self-service remote connection, automatic provisioning and
arbitrary external lifecycle execution are unavailable.

For the supported lab, follow the [CLI quickstart](../../README.md#tested-quickstart)
in the pinned engine checkout using operator-owned configuration. `doctor` must
actually establish compatibility/capabilities, then `validate`, QNX `qcc` build and
immutable `deploy` must succeed. An existing verified deployment can be reused;
local manifest existence alone does not prove target installation. Preserve its
real recipe, source/build hashes and actual execution evidence. For this staging
qualification, existing original d9d2a1a and corrected39b99d7 deployments were reused.

Approval is a protected local command with explicit project and paths, never an
HTTP endpoint. In the current private staging environment, from the repository:

```sh
.local/web/venv/bin/python web/ops/staging.py manage.py approve_target \
  --project PROJECT_UUID --target REQUEST_TARGET_UUID --kind managed-lab \
  --engine-root /operator/qualified-engine \
  --config /operator/private/target.local.json --alias lab \
  --manifest /operator/verified/deployment.json \
  --registry /operator/private/executor-registry.json \
  --build-label 'Verified candidate source identity'
```

These paths are placeholders for independently verified local operator inputs,
not browser fields or a claim that the operator has provisioned another host.
Production requires the root operator and dedicated production configuration.
Approval verifies deployment schema/build/recipe/architecture bindings and stores
an exact tenant/project/target/build registry entry. A previously approved route
cannot silently switch engine/config/alias; register a new target instead. Imported
candidate proposals remain historical; approval creates a distinct approved build
record. It does not rebuild, transfer or launch a test. Queue a real private inventory
and inspect unknown/unavailable/unsupported capabilities before requesting a run.

Issue a scoped code only after approval/inventory. Explicit live permission is
required for managed fixtures. Code sessions cannot approve targets, import builds,
change routes or widen their permissions. Current code issuance deliberately
withholds external-health execution; locally authenticated scoped administrators
may run that limited diagnostic. An external service is never implicitly restarted,
killed or reconfigured. Its health report cannot assert a known running build,
original-instance identity or passing lifecycle coverage.

## Qualification and limits

W007 proves six current code-authorized actual QNX cases, revocation and a real
source-fixed replay. Earlier W003 preserves bounded SSH-loss/same-ID recovery and
failed-transfer evidence. PostgreSQL negative tests prove customer request fields
cannot authorize a route, unobserved required capability cannot pass, external
lifecycle is withheld, and code sessions cannot administer routes or import builds.
No fresh customer installation or general remote agent is claimed. To add a service,
implement its versioned native adapter/observer and pass the original native gates
on real QNX before exposing its capabilities through the web registry.
