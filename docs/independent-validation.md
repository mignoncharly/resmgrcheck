# Try ResMgrCheck on your own QNX lab

This exercise asks an independent QNX developer to reproduce a cancellation
failure, verify a source correction, and assess the effort to adapt the tool.
It is an invitation to test, not a completed adoption claim. No outreach has been
sent by the project agent. Use only a lab you own or are authorized to test.

## Exercise A: review without installing QNX

Open https://qnx-resmgrcheck.gestionatech.de/demo/. Read the sensor failure,
corrected replay and job case. Follow one assertion to its native event and
download its canonical result. These are recorded QNX observations. This route
does not execute a new experiment or prove that your own target is supported.

Answer these questions without help from the author:

1. Which two obligations failed before the source correction?
2. Was fresh-client health established for that defective instance?
3. Did the source-corrected replay keep the same contract and fixture setting?
4. Why is retaining the job different from retaining its waiter?
5. Can you find the original source/build and the supporting event references?

Record how long the review took and which words/screens caused confusion.

## Exercise B: reproduce on your own machine

Start a timer before setup. Follow [the fresh-lab guide](fresh-lab.md), then the
[source-correction codelab](codelab.md). Preserve original and candidate checkouts,
commands, build records, native bundles and comparison. Use your own SDK license,
keys and image; none should be sent to the project owner.

Required evidence: actual `qcc` build; target version/architecture; intentional
sensor failure; unchanged-contract source-corrected replay; distinct fixture
hashes; original-instance fresh-client health before cleanup; exact observed
cleanup; a second-service job result. Report failed or blocked steps as such.
An offline inspection alone does not complete this exercise.

## Exercise C: assess a service integration

Choose a small resource manager that you wrote independently or may lawfully
modify. Before changing it, read [the adapter ABI](adapters.md) and the
[integration boundary](web/ADAPTER_INTEGRATION.md). Record its source URL/revision
and license. Do not upload proprietary driver or SDK source.

Identify its operation, return convention, required retained state, and permitted
test controls. List the hooks needed to observe a pending request, current unblock,
post-state and same-instance health. Measure adapter/instrumentation changes
separately. ABI1 uses fixed compiled parameters; a new device path/profile alone
does not provide lifecycle support. Do not claim an integration passed until its
actual native evidence has been reviewed.

If integration is impractical, explain the concrete missing interface. That is
useful feedback; it must not be replaced with a successful fixture demonstration.

## Feedback record

Copy this table into your response or a new issue. Contact the owner through your
usual channel; no public issue or external message is created automatically.
Review all attachments for private hostnames, paths, credentials and licensed code.

| Field | Your observation |
| --- | --- |
| Date and tested source revision | |
| Relationship to project / prior involvement | |
| Host and QNX version / target | |
| Exercise A: minutes, answers, confusing screens | |
| Exercise B: setup/build minutes; PASS/FAIL/BLOCKED per step | |
| Actual original/candidate native run IDs and verdicts | |
| Contract/settings unchanged; source and fixture hashes | |
| Cleanup and fresh-client observations | |
| Exercise C: independent service origin/license | |
| Integration hours, changed files/lines and missing hooks | |
| Problem caught or deliberately injected, clearly distinguished | |
| Would you use this in development? Why? | |
| Permission to quote specific feedback publicly | No unless explicitly granted |

The author may help unblock setup, but must record that help. Agent-run checks,
owner-run checks, and independent developer results remain separate evidence.
