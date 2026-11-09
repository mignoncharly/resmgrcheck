# Production QNX executor qualification

W029 prepares one operator workflow for active application
`3f4bafbd7d423fb5e55fc1e0f6a8ef326a273f58`, pinned engine
`ca4f74e0fcff33b6f6ebf6c553b3f8379f6440e0` and the already qualified QNX8 lab.
It does not redeploy HTTPS, change authentication settings or patch either immutable
tree. W030 supersedes the original pending state: operatorce97df9 completed private
registry provisioning, the actual systemd qualification probe and approval publication.
Root acceptance then stopped at exact_approved_native_plan_required before any
temporary principal, native intent or browser batch. Existing W028 HTTPS/password/code
acceptance remains passed. Native acceptance is pending; P8 is IN PROGRESS.

## W030 correction and exact completed-state resume

The root coordinator had reused acceptance.native_plan, whose generic worker binding
validator accepts only root/self ownership. Under UID0 it rejected the correctly
executor-owned registry; the selector swallowed that PolicyError into zero pairs.
The fixed root selector explicitly checks expected executor UID/GID0600 custody,
exact registry/route/host/manifests, approved tenant/target/build IDs, retained actual
runtime proof and database guard metadata. Worker ownership policy is unchanged.

The new operator command below resumes the existing ce97 attempt. It requires the
exact known completed phase and failure, no native intent/result, unchanged application/
engine/unit/HTTPS baseline and all seven private-file hashes. The full old journal,
failure and runtime proof are archived root0600 under native-acceptance/attempt-ce97....json.
Only after read-only preflight passes does the journal bind the new driver, retaining
resumed_from_driver/runtime_proof_driver=ce97. The old proof is never relabeled as new.
Interrupted archive/journal publication is resumable; unknown histories are refused.

This path does not copy credentials again, reissue grants, repeat the actual probe,
republish approvals or stop a healthy idle dispatcher. The lock-guard checker is
read-only. It proceeds directly to the approved native browser batch and guarded
executor rehearsal. Changed/revoked/quarantined approval or unexpected work still
fails closed. Do not repeat the old ce97 command or reset protected state.

## One reviewed operator command

Use the new full committed driver SHA supplied in the handoff, replacing the placeholder:

```sh
sudo /usr/bin/python3 -I -B \
  /home/mignon/projects/resmgrcheck/web/ops/production/provision_executor.py \
  --driver-revision REVIEWED_FULL_DRIVER_SHA \
  --apply
```

Without --apply, this runs an unprivileged exact-commit read-only plan. Do not use
prepare.py or recover_https_auth.py for this step. Local sudo is required because
initial provisioning creates dedicated private executor files, additive approval/audit
records and restricted database locking permissions. The current completed-state
resume instead reads protected state, records its preserved history and coordinates
the actual production executor/acceptance. The fresh-provisioning behavior described
below is retained as reference; completed gates are reused on this resume.
Never send passwords, SSH files, configuration contents or license material in chat.

## Fixed scope and prerequisites

The existing lab route is pinned to loopback22220, the previously verified host-key
file and the existing local Ed25519 identity. No key is generated or changed. The
workflow makes private copies under /etc/resmgrcheck/executor, owned by resmgr-exec
(actual UID981/GID973 on this host), directories0700/files0600. Originals are untouched.
The web process still cannot read these resources; the systemd executor retains
ProtectHome, ProtectSystem, credential isolation and loopback-only IP policy.
No SDK or license configuration is given to the executor. No QNX build is performed.

The tracked phase10 original/candidate manifests are hash-pinned in executor_plan.py.
They bind the exact recipe/QNX8/x86_64/x86pc identity, immutable deployment directories,
two ABI1 adapters and each native file's hash. The original is ae1211e774c0..., source
d9d2a1a36702; corrected is44d2629791e9..., source39b99d7a163c. The sensor fixture/source
differs while runner/worker remain shared. Preflight independently read both remote
manifests and SHA256-verified all ten native file copies as development UID1000.
This is read-only deployment identity evidence, not production executor qualification.

The registry contains one deterministic approved organization/project/target and two
exact build UUIDs. Custody uses a new disabled account with an unusable password and
no administrator memberships. Existing users/projects/codes/approvals are untouched.
Approvals are withheld until the actual executor probe succeeds. Neither browser
forms nor codes can supply hosts, SSH options, executable paths or registry entries;
the unchanged common engine bridge constructs fixed operation arguments and checks
tenant/target/build binding again before launch. Modified/revoked/quarantined bindings
are refused, never repaired automatically.

## Database row-lock compatibility

The existing start_authority guard serializes code revocation and process creation
using SELECT FOR UPDATE on authorization rows. PostgreSQL requires UPDATE permission
on at least one column for that lock; the original executor grants provide SELECT
only. Staging-owner success did not qualify this runtime-role path.

executor_locking.py installs an invoker-role function and two BEFORE UPDATE guards,
then grants UPDATE(id) only on control_user/control_accesscode to resmgr_exec. Every
actual executor UPDATE, including id=id, raises executor_authorization_update_forbidden.
Other columns/table UPDATE, TRIGGER privilege, ownership, role membership and schema
CREATE remain unavailable. The role cannot disable/drop the guards. No authorization
row is modified; administrator/web writes retain their existing behavior. Existing
unknown functions/triggers or wider grants cause refusal. Installation is transactional
and idempotent, verifies exact function owner/body/search_path and enabled trigger
metadata, and appends an audit event. It is not SECURITY DEFINER and does not add a
migration or change application authentication settings. Real disposable PostgreSQL
nonprivileged-role tests prove both locking success and actual mutation rejection.

## Actual service-context probe and dashboard acceptance

The canonical executor unit is first checked byte-for-byte and must have no unknown
overrides or active work. A reviewed temporary own drop-in changes only Type/ExecStart/
Restart/TimeoutStartSec to run a read-only probe. The original ExecStartPre runtime_check,
User/Group, LoadCredential, network and filesystem isolation remain active. The probe
therefore uses the actual /run/credentials/resmgrcheck-executor.service context. It
checks nonroot identity, DB role/permissions/authorization-row locks, forbidden-file
denial, registry/route/host identity, both remote manifests/file hashes and actual
compiled capabilities. It reports service-instance health UNKNOWN until native runs.
No SDK readiness or universal adapter support is inferred. The override is removed
and systemd configuration reloaded before the canonical dispatcher is started.

The public HTTPS browser runs as the development operator, with temporary generated
credentials sent through an owned stdin pipe. Cookies/codes/passwords/traces are not
saved. It requests exactly three native cases through dashboard confirmation forms:

1. Original sensor, ignore-unblock, expected canonical FAIL. A root observer waits
   for the exact timed native pending event, then SIGSTOPs only a pidfd-pinned local
   collection SSH child in the executor service cgroup. It cannot signal a launcher,
   another service or a QNX PID. The existing engine times out/reaps that child; the
   existing lease/recovery path must collect the same run ID/supervisor. Partial
   evidence/incident history and the intentional failure reasons must survive.
2. Saved-input replay against the corrected source, expected PASS. ignore-unblock,
   contract/settings remain unchanged. Native build identity, common evaluator and
   canonical comparison must prove fixed; HTTP completion alone is insufficient.
3. Corrected job, expected PASS. After actual timed pending is observed, collection
   is briefly held while a second job is queued and its code revoked through HTTPS.
   Existing supervision/collection completes the first run; the queued job must be
   rejected before any child launch. Revoked sessions lose browser access. This
   proves revocation during live collection after observed pending, not a claim that
   the native request remains pending at the exact revocation instant.

All three completed runs require original sealed evaluator verdicts, cleanup,
approved source/build identity, inventory integrity and verified ZIP-download hashes.
The revoked queued operation receives no fabricated native result or cleanup claim.
Desktop/mobile/no-JS report checks and cross-tenant/administrator denial remain active.
The temporary acceptance account is disabled and codes revoked on success/failure;
audit/evidence and existing identities remain. No customer runner/AI is enabled.

The lab had148 free file entries during read-only preflight. The initial qualification
requires128 as a reserve and the unchanged worker checks its per-case minimum too.
No old run, start guard, build, evidence or QNX process is removed. Insufficient space
fails closed; archiving/cleanup requires separate reviewed exact custody, not guessing.

## Resume, failure and rollback boundaries

Root receipts/diagnostics live under /var/lib/resmgrcheck/private/operator/native-acceptance.
The operator receives safe stage/failure JSON and, on success, actual native IDs,
verdicts, recovery/revocation/cleanup summaries and report paths. Unprivileged browser
metadata lives in .local/web/evidence/production-native-<id>. It contains no raw secrets.
Existing protected state/history is never deleted or reset. Partial stages are retained.

Retry the same committed command. Exact existing private bytes/ownership/modes must
match before reuse; unknown resources are not overwritten. Publication is atomic with
no-replace semantics. Unpublished private temporaries remain protected and unreferenced.
Interrupted public tool temporaries are recognized only by exact trusted bytes and
metadata; unknown payloads stop recovery. A known probe override can be removed safely
on retry; unknown overrides are untouched. An active native run/slot is not killed or
reset. Preserve the dispatcher so same-ID cleanup can finish, then reconcile its safe
receipt. Native evidence already fully verified/recorded is revalidated and reused,
without another batch consuming target file entries. Partial failed batches are retained
and may need review or more free entries; no passing completion is inferred.

After native acceptance, a guarded idle executor stop/start rehearsal locks the enqueue
and claim rows so new work cannot race into it. It re-runs canonical systemd startup and
checks unchanged HTTPS configuration/pointer and verified public readiness. This is an
executor recovery rehearsal, **not full immutable application rollback qualification**.
Do not switch public traffic to original544: its older authentication behavior is not
the approved password-only release. Full application rollback needs a separately
reviewed compatible release/maintenance plan and remains open. No Nginx/web/database
service restart is part of this command. See [INDEPENDENT_UAT.md](INDEPENDENT_UAT.md).
