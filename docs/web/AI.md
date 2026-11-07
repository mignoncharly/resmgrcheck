# Optional evidence-grounded engineering assistant

Implementation branch:feature/production-web-ai. Current provider qualification is
recorded in TEST_EVIDENCE/STATUS, not inferred from this document. OpenAI is the one
implemented provider; other providers are unsupported. A model is explicitly
operator configured, never invented/substituted. AI is off by default and remains
independent of native execution, deterministic evaluation and offline reporting.

## Trust and consent

A project owner/admin with verified email/MFA sets opt-in and a daily budget.
A verified developer with recent MFA selects one collected native case, optionally
a reviewed original source excerpt and an earlier same-project run. The browser
previews the exact redacted packet and a named provider/model/price ceiling. A
signed five-minute confirmation binds actor, run, exact packet/provider and request
key; the next POST must explicitly consent. Changing inputs invalidates consent.
The HTTP process never calls the provider or reads its credential.

Only server-authorized original engine results, contract/build/manifest excerpts,
referenced native events and a canonical same-project comparison are retrieved.
Assertion observed-object duplicates/cycle detail are explicitly omitted from the
bounded AI packet; the complete original evidence remains authoritative and linked.
At most24 referenced events are sent, and omitted counts are disclosed. Original
record#0 is the target run manifest, not a fabricated producer event. Timeline
records retain exact native frame indexes and nanosecond observations. No private
SSH/SDK configuration or diagnostic command logs are retrieved.

Optional source is at most12KiB/240 UTF-8 lines, original authorized C/header/Python/
text/diff only. Binary, recognized private-key and marked proprietary QNX content
are refused. Only the redacted copy and original/redacted digests are retained.
Known credential assignments, key prefixes, email and private paths are redacted.
This is best effort: the developer must inspect the preview and cannot use it to
authorize sharing protected material. Source/log instructions remain untrusted
data. There are no tools, shell access, patch application or service controls.

Every finding must cite an existing supplied reference. Source review must cite
source; before/after interpretation must cite the canonical comparison. A patch
requires source-line references and remains an untested suggestion. Output is
strictly validated, size bounded and escaped; unknown citations, absent uncertainty,
verdict fields, incomplete/refused or malformed responses are withheld. Reference
existence does not establish that an AI claim is semantically correct. Human review
and separate approved native build/deploy/replay remain necessary.

## Durable execution and cost controls

The separate private `manage.py dispatch_ai` service reads its dedicated0600
provider file and records only nonsecret policy in PostgreSQL. Use the exact fields
in INTEGRATIONS.md. Missing/stale worker policy, missing provider, zero budget or
project opt-out prevent enqueue. Requests use the fixed HTTPS Responses endpoint,
TLS verification, explicit standard/default pricing tier, no proxy inheritance/
redirects, no tools, no stored Responses
state, and no automatic provider retries. store:false is not zero provider
retention; the provider's abuse-monitoring/account-specific policies still apply.

A transactional ledger reserves a conservative bound before queueing: serialized
input bytes, policy/schema allowance and1600 output tokens, at operator-reviewed
standard rate ceilings. Input is at most24000 bytes. Maximum per request isUSD0.10;
project daily budget at mostUSD1, global daily configuration at mostUSD2,20 requests/
project/day and100 global/day, three new actor requests/minute, ten queued/running
globally. Signed duplicate consent returns the existing job and does not respend.
Prices require a review within30 days. Also set provider account billing limits;
application estimates are not invoices and cannot validate a provider's billing.
The returned processing tier must verify as default; absent/other tiers are
withheld rather than assumed to match the reviewed standard prices.

One database lease plus a local owned flock bounds concurrency. The provider runs
in an exact owned child with a25-second total deadline and20-second socket timeout;
the key crosses an anonymous pipe, never argv/environment/logs. The child has
memory/CPU/file-descriptor limits, no QNX/SDK credential in argv/environment and no
tools. Separate filesystem/OS account enforcement is a P8 production requirement;
same-user private staging does not establish it. Expired
in-flight state becomes uncertain without reissue. Uncertain/error calls retain
their full reservation, explicitly not a confirmed charge. Valid observed usage
permits reconciliation at the configured ceilings. Queued cancellation withholds
the request; it does not claim to terminate an in-flight remote operation.

The worker repeats user/role/project/evidence/source/build-policy authorization
before egress and authorization before disclosure. Provider/model/request IDs,
usage, consent/input/output hashes, immutable pricing and citation references are
recorded. PostgreSQL protects consent identity/input and completed output/provenance.
Rendering verifies original evidence and saved output integrity before disclosure.
AI never writes canonical Run summary/verdicts or native artifacts.

## Retention and operations

Source and AI content expire after30 days through bounded private maintenance;
consent/hash/budget/audit metadata remain. Erasing an inactive source also erases
derivative source-bearing analysis content. Active requests must be cancelled
before dispatch or finish their bound first. Local deletion cannot retract data
already sent to the provider or change its retention policy. Organization native
evidence has a separate policy; active AI dependencies withhold local native purge.

Start/stop only the dedicated AI service. AI downtime must not stop native testing.
Do not borrow unrelated API keys, print credential files or enable a model without
reviewing access, data policy and current pricing. Real provider qualification uses
`web/ops/qualify_ai_provider.py` through the private staging launcher only after
dedicated configuration. It performs four explicitly consented actual requests
against genuine existing QNX evidence and the project's original published patch;
it does not rerun QNX. Host mocks/disabled-browser tests are not provider proof.

Implementation references, checked2026-11-07: [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[data controls](https://developers.openai.com/api/docs/guides/your-data),
[pricing](https://developers.openai.com/api/docs/pricing). These document API behavior;
they do not establish this operator's model access, credit or retention approvals.
