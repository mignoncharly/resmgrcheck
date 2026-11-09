# Native adapter integration contract1

The public C contract is native/adapter_v1.h (ABI1, exact struct_size). It remains
statically linked, C11/QNX extensions, built with real qcc. The registry rejects
wrong ABI/size, missing callbacks, duplicate IDs, unknown capability bits and unsafe
fixture basenames. Native result/state serializers reject out-of-bound enum/fact
counts; malformed/incomplete evidence never becomes PASS. No runtime plugin,
browser-provided library, arbitrary shell string or raw message is accepted.

This branch preserves original sensor/job source files, generic supervisor/worker
and evaluator behavior. New mailbox source is an additional representative owned
service, not proof of arbitrary driver compatibility. Native compilation/execution
of the new adapter is pending at the initial W017 source checkpoint. Host112 and
web119 tests passed, including original saved evidence and legacy build parsing.
Only real QNX observations may advance that qualification.

## Registration and build

1. Define bounded fixed request/reply/control structures in a versioned service
   protocol header. Validate declared/current payload size, reply capacity, access
   mode, reserved fields, operation IDs and any generation/ownership token before
   state mutation. Reject combined unsupported custom operations.
2. Implement validate_parameters, control, ordinary, prepare and finish callbacks.
   Preserve raw return/errno separately and the installed API's error convention.
   prepare uses the two bounded iov arrays and512-byte aligned buffers; validate
   every reply header/reserved field/typed fact before reporting OK. ABI1 has no
   runtime parameter context: only exact compiled, validated parameters are
   supported here. A variable protocol/context requires a reviewed new ABI;
   do not claim arbitrary configuration from validate_parameters alone.
3. Add the reviewed static descriptor to native/adapters/catalog_v1.h and source
   under native/adapters. Make links those sources; add the service fixture build
   rule. No service-name branch belongs in runner, worker or evaluator.
4. Register exact operation/fixture/convention/parameter bounds and typed result/
   state facts in resmgrcheck/registrations.py. Register its profile in PROFILES,
   with managed and optional read-only external profiles. The central site needs
   this same reviewed registration to validate incoming evidence; customer-uploaded
   code cannot register itself. Unknown versions/IDs remain UNSUPPORTED or rejected.
5. Build in a new immutable checkout with the customer's own licensed SDK. Keep
   generated binaries/build records, credentials and runtime images outside Git.
   Use the existing Make/qcc build, CLI validate/deploy/doctor and independent
   readback hash verification. Do not replace the production/original engine tree.
   Historical deployment manifests bind their exact known adapter subset; new
   registrations do not invalidate old immutable two-adapter evidence. Missing
   adapters in a selected build never imply support.
6. In the outbound runner's private local configuration, explicitly allowlist the
   verified deployment hash/manifest and permitted fixture modes. Import that
   public manifest into the exact project/target and approve its identity separately.
   Enrollment, reachability and a compiled capability declaration are not native
   lifecycle qualification. See CUSTOMER_RUNNER.md.

## Obligations that must be observed

Required coverage needs actual pending request/owner identity, current unblock
notification, cancellation completion and post-state, exact worker reaping,
same-instance fresh-client health before fixture stop, and explicit cleanup facts.
A delay, successful connection, return code or service restart cannot substitute
for any missing observation. The common evaluator remains authoritative. FAIL,
ERROR, UNSUPPORTED and NOT_RUN stay distinct. Advertise only independently
qualified families; missing signal/departure/repeat/ordering observers must withhold
those suites. Externally managed services are never automatically restarted.

Managed owned fixtures bind build bytes and process ownership through the pinned
deployment/supervision path. External attachment still has no general private
pending/unblock observer or verified running-build identity, and full lifecycle
testing/changed-build external replay remain UNSUPPORTED. A reported PID/instance
tag is diagnostic identity, not cryptographic build attestation or proof of survival.
Source-candidate replay must preserve profile/settings/target and prove the actual
candidate build; a fixture-mode contrast cannot be labeled a source correction.

## Representative mailbox service

native/fixtures/mailbox_protocol.h defines protocol1, one retained channel1 message,
up to eight waiting consumers and a separate explicit matching-generation ACK.
FETCH is non-consuming. Cancelling a consumer must remove the waiter without
consuming/acknowledging the retained message. State predicates include
message_exists, message_ready and acknowledgements independently of pending.
ARM/PUBLISH are explicit owned-test controls. ACK checks writable access, exact
length/reserved/channel/generation and increments a bounded acknowledgement count;
stale/duplicate acknowledgements fail. IDENTITY provides protocol/PID/instance tag
read-only; it does not claim a running binary hash or external lifecycle support.

The adapter compares ordinary devctl and installed io_devctl_t/MsgSendv paths,
checks fixed channel/reserved/reply fields and preserves direct devctl errors.
Native callback discovery advertises the initial timeout/pending/unblock/state/
release/health/error-probe and read-only external-health surface only. Signal,
departure, repeat and ordering are unavailable until separately qualified.
tests/qnx/mailbox-input.c is an actual-QNX input/identity/ACK test owner with bounded
workers and exact direct-child wait status. It is not a host-native substitute.
The original sensor/job capabilities and evidence remain unchanged.
