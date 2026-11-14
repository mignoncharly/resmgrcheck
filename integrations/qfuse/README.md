# QFuse cancellation integration

This optional probe links the independently authored [QFuse backend](https://github.com/gowtham0992/qfuse/tree/2f4f6ecd79d23d7d4365b274160129cc2ff43c8f)
unchanged, at the exact commit in `sources.lock.json`. QFuse contributors own that
backend. ResMgrCheck supplies a small original two-file FUSE test filesystem and
an owned-child supervisor. This is an integration qualification, not a frozen
ABI1 service adapter, an upstream endorsement, or evidence of outside adoption.

The contract exercises a held read callback and verifies:

1. A timeout or non-restart signal returns the expected native error before the
   callback is released.
2. QFuse's authenticated public admin channel reports the active callback and
   records cancellation while the callback is still held.
3. A different file remains readable on the same running service.
4. Releasing the callback drains active operations and deferred cleanup.
5. Both exact owned children are reaped and the unique mount disappears.

`cancelled_waits` is a **cumulative count**, despite its name. It increments in
`src/qnx_requests.inc:cancel_waiter` and resets when the pool starts; it is not a
count of outstanding waits. The final count must remain stable after release,
not become zero. A continuing filesystem callback is allowed by this contract.
The probe does not modify or claim to repair an upstream defect.

## Reproduce

Use the existing installed QNX SDP 8.0 environment, Make and Python 3.10+.
The first build needs HTTPS access to download the locked public sources.
Downloads stay under ignored `.local/qfuse-review`; binaries stay under `build`.
The MIT backend and LGPL libfuse headers/parser/logging source are hash checked.
Their original license files are downloaded with the source; no GPL example is
used. The standalone parser preparation follows QFuse's public build recipe.
The repository MIT license covers our original probe and host tools.

```sh
source /path/to/qnx800/qnxsdp-env.sh
make -C integrations/qfuse QNX_VARIANT=gcc_ntox86_64
python3 integrations/qfuse/run.py --target lab --config config/target.local.json \
  --out runs/qfuse-timeout
python3 integrations/qfuse/run.py --target lab --config config/target.local.json \
  --out runs/qfuse-signal --signal
```

Use an explicitly configured, disposable QNX 8.0.0 x86_64 lab with root access
to QFuse's admin channel. The tool verifies the target identity and round-trip
binary bytes, reserves a new remote directory and uses a unique mount path.
It never installs a service or changes the selected ABI1 deployment. Its 25-second
native watchdog acts only on its exact unreaped children; transport uncertainty
is not success and never triggers a retry. Remote artifacts remain for review.

`events.jsonl` contains native observations; `result.json` is the host's scoped
evaluation. `execution.json` records target/build/source identities and native
exit status. `transport.json` retains the exact launch route, and `stderr.txt`
contains backend diagnostics. Preserve the whole directory. A missing cleanup
event or incomplete execution is ERROR; an observed violated service obligation
is FAIL. This is functional lab evidence, without hardware timing guarantees.
