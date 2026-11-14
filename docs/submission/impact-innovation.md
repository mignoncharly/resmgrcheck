# Stronger impact and innovation evidence

These additions are qualified on QNX 8.0.0 x86_64 in the separate review guest
from clean source **5e1fb8a**. They extend the CLI; the deployed web application,
existing public review ZIP and held YouTube draft retain their earlier revisions.
[The qualification index](../evidence/impact-innovation/qualification/index.json)
records the builds and outcomes. Independent developer validation remains pending.

## A correct timeout return can conceal a failed service obligation

In both service fixtures, the deliberate `retain-waiter` control returns the
expected native `ETIMEDOUT`260. A predicate checking only the return value and
error therefore succeeds. ResMgrCheck also observes **pending1**, where the
declared contract requires zero, and reports **FAIL**.

| Actual QNX case | Limited return predicate | Full declared contract |
| --- | --- | --- |
| [Sensor baseline](../evidence/impact-innovation/qualification/sensor-baseline/report.html) | SATISFIED | PASS |
| [Sensor retained waiter](../evidence/impact-innovation/qualification/sensor-retained/report.html) | SATISFIED | FAIL: pending state not released |
| [Job baseline](../evidence/impact-innovation/qualification/job-baseline/report.html) | SATISFIED | PASS |
| [Job retained waiter](../evidence/impact-innovation/qualification/job-retained/report.html) | SATISFIED | FAIL: pending state not released |

Inspect the [sensor comparison JSON](../evidence/impact-innovation/qualification/sensor-retained-return.json)
and [job comparison JSON](../evidence/impact-innovation/qualification/job-retained-return.json).
Each points to the exact native return and failed assertion, including the original
event references. This is our explicit limited predicate over sealed evidence;
no third-party testing tool was executed or benchmarked. The deliberately injected
faults are in our own fixtures. Existing source-correction evidence remains separate.

```sh
python3 -m resmgrcheck return-check runs/retained/cases/timeout/bundle \
  --out runs/retained-return.json
```

This gives service developers a concrete reason to examine server state after
cancellation rather than stopping at the client return. It demonstrates a missed
obligation, without claiming measured debugging-time savings or outside adoption.

## Reduce a repeated failure to a smaller reproduced input

The new bounded reducer starts with a saved, established repeat failure and uses
its exact deployment, target identity and fixture mode. It changes only
`profile.suite.cycles`, recording a fresh owned run before every launch.

| Requested count on a new instance | Sensor | Job |
| --- | --- | --- |
| 1 | PASS | PASS |
| 2 | PASS | PASS |
| 3 | FAIL: pending state not released | FAIL: pending state not released |

Both original inputs requested20 cycles with the `retain-third` fault. Both
searches reproduced the same failure signature at3. Review the
[sensor search](../evidence/impact-innovation/qualification/sensor-reduction/reduction.json),
[three-cycle sensor report](../evidence/impact-innovation/qualification/sensor-reduction/attempt-3/report.html),
[job search](../evidence/impact-innovation/qualification/job-reduction/reduction.json)
and [three-cycle job report](../evidence/impact-innovation/qualification/job-reduction/attempt-3/report.html).
Every attempt retains its request, raw observations, cleanup status and result.

```sh
python3 -m resmgrcheck run --target lab --profile profiles/sensor-repeat.json \
  --suite profile --fixture-mode retain-third --out runs/repeated-failure
# The deliberate defect leaves later cycles NOT_RUN; the CLI returns3.
python3 -m resmgrcheck reduce runs/repeated-failure --target lab \
  --out runs/reduced --max-attempts 20
python3 -m resmgrcheck report runs/reduced/attempt-3 \
  --out runs/reduced/attempt-3/report.html
```

Separate [sensor](../evidence/impact-innovation/qualification/sensor-budget/reduction.json)
and [job](../evidence/impact-innovation/qualification/job-budget/reduction.json)
one-attempt budgets stopped as `budget_exhausted`, without claiming a minimum.
Uncertain evidence/cleanup or a different failure stops further launches. Interrupted
launch intent retains the exact run ID for the ordinary status/collect workflow;
the search never silently relaunches an uncertain attempt.

This is the smallest reproduced cycle count **in this recorded ascending search**,
with one execution per count. It is not exhaustive scheduling, arbitrary sequence
minimization or an unchanged-input source-fix replay. The original20-cycle run
already stopped at the third failure; reducing its requested input is not evidence
of an85% runtime improvement. Search attempts perform additional native work.

The first search exposed a final-cycle classification bug in our evaluator. It
stopped safely at ERROR. The [original sealed trial](../evidence/impact-innovation/trials/README.md)
is preserved, and a regression checks the correction while keeping missing state
observations as ERROR. Fresh native qualification then reproduced the expected FAIL.

## Exercise an independently authored backend

The optional [QFuse integration](../../integrations/qfuse/README.md) links a pinned,
unmodified, independently authored MIT QNX resource-manager backend with an
original two-file test filesystem. Both actual
[timeout](../evidence/impact-innovation/qualification/qfuse-timeout/events.jsonl)
and [signal](../evidence/impact-innovation/qualification/qfuse-signal/events.jsonl)
runs show:

1. The held client returns ETIMEDOUT260 or EINTR4 before callback release.
2. The public authenticated admin channel observes one active operation and one
   cumulative cancellation while the callback remains held.
3. Another path returns the expected byte81 on the same service.
4. Releasing the callback drains active operations and deferred cleanup to zero.
5. Both owned children are reaped and the unique mount disappears.

The continuing callback is permitted by QFuse's contract. Its cumulative
`cancelled_waits` count correctly stays at1 after drainage. The first probe used
an incorrect zero-count expectation; its
[original FAIL](../evidence/impact-innovation/trials/cumulative-counter-assumption/result.json)
is retained as a test-contract correction, not an upstream vulnerability.

This expands the evidence beyond our two demonstration services and exercises
different service semantics. The workload remains controlled and synthetic; the
backend is independently authored. It is a separate integration probe, without
a frozen ABI1 adapter, production filesystem qualification, upstream endorsement
or independent tester. No contact or contribution claim is implied.

## What these additions establish

There is now a verifiable missed-obligation example, a working bounded native
reduction workflow, and an independently authored backend integration. Together
they give judges more concrete evidence of usefulness and technical creativity.
They do not determine a judging score or a winning probability. External feedback,
adoption and independent UAT remain open.
