# QNX evidence map

Current additional proof: E019 builds a fresh image with new guest host keys and
runs four actual native cases, including same-contract source-fixed replay and
observed cleanup. [Fresh-target index](../evidence/fresh-target-20261114/README.md)
records exact source/build/run identities. It is agent-run, not independent adoption.

The qualified clean source is d2e0a43; its actual source/binary/evaluator identities
are in E015. The report-only successor is tracked separately. Demo manifests bind
any later actual source/build selection; a current file merely existing is not proof.

| Claim | Real source/API | Actual evidence / demo |
| --- | --- | --- |
| Native QNX build and execution | Makefile, scripts/record-build.py; qcc gcc_ntox86_64/C11 | E005/E013/E015 actual build/transfer/target manifests; demo target/build opening |
| A timed reply can require server cooperation | native/worker.c timed path; TimerTimeout(send/reply) immediately followed by prepared MsgSendv | Fixed/ignore-unblock native timeout bundles; demo deliberate failure |
| Cancellation belongs to a current pending request | sensor_unblock/job_unblock; iofunc_unblock_default, MsgInfo/_NTO_MI_UNBLOCK_REQ, MsgError | E011 directed barriers/obsolete/unmatched checks; actual source-fix patch and demo replay |
| Descriptor and final OCB lifetimes differ | native/fixtures/lifecycle.h; iofunc_close_dup_default/iofunc_close_ocb_default | E011/E015 departure callback/default/reap observations; demo exact-worker departure |
| Job survives waiter departure | native/fixtures/job.c bounded waiter table/service-owned job; job_protocol.h | Job departure/cancellation state and fresh retrieval; demo job path |
| Ordinary and prepared devctl semantics agree | native/adapters/job.c ordinary/prepare/finish; devctl/_IO_DEVCTL/MsgSendv | Native baseline results and raw error260 versus direct ENOENT2; E007/E015 |
| Supervisor remains independent | native/runner.c, common/scenario_v1.h/process/protocol/persistence | E009/E011 failure matrix and E013 recovery; exact owned-child ledger/reaping |
| Adapter reuse is real | adapter_v1.h, adapters/registry.c; resmgrcheck/registrations.py | Same runner/worker hashes for both services; unchanged generic core in E015 |
| Deployment/recovery use actual target bytes | deployment.py/transport.py/workflow.py; targetctl.c | E013 SFTP hashes, ACK-loss/SIGINT recovery, mismatch rejection and unchanged run IDs |
| Strict incomplete/unsupported behavior | contracts.py/evaluator.py/exports.py | E013/E015 expected red matrix, required NOT_RUN/JUnit coverage errors |
| Evidence/replay preserve source identity | artifacts.py/replay.py/workflow.py | Sealed raw/status/plan/build snapshots; both explicit candidate source fixes in E012/E013/E015 |
| Offline view preserves verdicts | reports.py | E014 45 browser views; E015 report follow-up/JSON-JUnit preservation |
| Malformed fixture controls cannot change state | message_bounds.h/lifecycle.h; exact current/reply bounds and OCB access | E015a/E015 real25-message input gate, unchanged generation/fresh health/reaping |

Original project code is MIT; cJSON has its pinned MIT notice. QNX SDK/runtime,
images, licensed components, machine configuration and credentials remain external.
No proprietary image is included as evidence. E015 explicitly reused its guest;
E019 separately qualifies a newly generated guest. Independent developer adoption,
memory measurement and exhaustive scheduling remain unverified.
