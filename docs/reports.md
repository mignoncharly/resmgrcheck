# Reading an offline report

Generate from a collected execution, a sealed native case bundle, or a comparison:

```sh
python3 -m resmgrcheck report runs/sensor-replay --out runs/sensor-replay/report.html
python3 -m resmgrcheck report runs/comparison --out runs/comparison/report.html
```

Open the HTML file directly in a browser. CSS and the small optional filter script
are embedded; there is no server, CDN, fetched font, API or network dependency.
Copy the referenced evidence directories too when sharing local artifact links.
The report itself opens offline; raw links require the accompanying files.

The summary states run completion, required coverage, case counts, fixture setting,
profile/adapter, configured deployment and observed target/evaluator identities.
Incomplete and unsupported coverage remain explicit even when an independent
cleanup/status assertion passed. Build/source hashes are available in disclosures;
these are integrity/provenance records, not malicious-target attestation.

The case table includes aggregate verdicts and every required repeat cycle. Open a
case to see the declared obligation alongside actual values, exact error codes,
normalization and source event references. Reasons retain independent service
FAILs and infrastructure ERRORs. A successful export does not turn the run green.
All details work with keyboard disclosure controls and without JavaScript. Optional
filters hide rows/details; they do not calculate verdicts or change counts.

The timeline uses actual target CLOCK_MONOTONIC offsets within each native case.
Record numbers are zero-based NDJSON positions. It shows assertion references and
actual pending/arming/trigger/result/state/health/cleanup records. Missing stages
are explicitly unobserved. A logged absolute deadline is an armed/configured bound,
not evidence that a timer expired. Elapsed intervals describe observed records,
not guaranteed execution latency. Full raw streams remain linked.

Health obligations refer to the original managed instance. A restart or later
recovery cannot satisfy them. External diagnostics disclose unverified running
service build/instance identity. Cleanup facts are separate from service health;
a cleanup PASS with unsupported service coverage does not complete that coverage.

Replay shows the saved input location and command. Use a new output directory;
recover an uncertain launch by status/collect first. Explicit candidate manifests
select a deployed source fix. Keep the saved contract/settings unchanged for a
source-fix comparison. A fixture-mode change is a disclosed incomparable contrast.
Legacy sealed-case replay requires an explicit per-adapter candidate manifest;
external changed-build replay remains unavailable without running-build identity.

Comparison views separate source/executable hashes, contract/settings changes and
observed QNX target metadata. A changed recorded target fingerprint or recipe
makes the cases incomparable even with the same declared contract. Older comparisons without target fields say unknown.
The view displays saved comparison metadata, without independently revalidating
its original/candidate bundles; inspect their bundle IDs and reports. Incomplete,
unsupported and incomparable labels cannot establish a fix.

Empty or partially collected inputs produce an INCOMPLETE/ERROR view without a
passing conclusion. Finalized bundles must pass integrity and canonical evaluation
checks; tampered evidence is rejected. Reports cannot replace original inputs,
partial raw streams, case bundles, diagnostics or collection history. Every input
string is escaped; JSON is rendered as text. No raw JSON is embedded in scripts.

## Qualification

Host report regressions run with the standard library:

```sh
python3 -m unittest discover -s tests/host -p test_reports.py -q
```

Browser checks use optional test-only Playwright and Chromium in an ignored local
environment; they are not product dependencies. With that tooling installed:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/browser-binaries" \
  .local/browser-test/bin/python tests/browser/qualify_reports.py --out runs/report-qualification-new
```

The script opens real saved QNX reports at laptop/narrow widths and with JavaScript
disabled, checks keyboard disclosure/filtering, local evidence links, page overflow
and network requests, and saves screenshots. Empty/hostile long-error samples are
labelled synthetic formatting cases. Older failed-baseline/cleanup/interference
native streams are reused unchanged and resealed on the host; this does not claim
new QNX execution against the report implementation. Source evidence and JUnit
bytes are checked before/after. E014 records the actual run and browser version.
