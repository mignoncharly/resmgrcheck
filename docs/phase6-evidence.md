# Evidence and replay workflow

Phase6 is qualified by E012. Commands below operate in the repository using the
reviewed local QNX lab. Source the installed environment and use `make qnx` when
building. The complete host transport workflow remains Phase7.

Seal an already collected persistent run (including a valid failed run):

```sh
python3 -m resmgrcheck bundle PLAN.json EVENTS.jsonl --status STATUS.json --output NEW_BUNDLE
python3 -m resmgrcheck inspect NEW_BUNDLE
python3 -m resmgrcheck junit NEW_BUNDLE --output report.xml
```

The bundle output must be new. Preserve partial directories after errors. A final
bundle marker means complete artifact collection, not a passing service. Inspect/
export return0 for successfully processed red evidence. Reports must be outside
the source bundle; regeneration cannot rewrite raw observations. Never edit marker
hashes to hide missing evidence.

Describe an explicitly selected existing deployment:

```sh
python3 -m resmgrcheck candidate NEW_BUNDLE/plan.json --directory /data/resmgrcheck/SELECTED --output SELECTED.json
```

For a changed build, additionally pass `--build-record PATH/build-info.json` from
its successful real Make/qcc build. The target recipe must remain compatible.
Keep original/candidate records. Replay requires explicit selection even when
using the original deployment:

```sh
python3 -m resmgrcheck replay NEW_BUNDLE --candidate-manifest SELECTED.json --attempts ATTEMPT_HISTORY --run-id FRESH_ID
```

The tool checks processor/machine and actual target executable hashes before one
persistent launch. It preserves attempt count, preflight/launch-request/acknowledge/
collection facts and every partial or completed attempt. A missing acknowledgement
never authorizes automatic relaunch. Keep the run ID for later collection. No
stored PID or rcvid is process-cleanup authority or replay input.

Compare/export completed replay bundles:

```sh
python3 -m resmgrcheck compare ORIGINAL_BUNDLE CANDIDATE_BUNDLE --output comparison.json
python3 -m resmgrcheck junit ORIGINAL_BUNDLE CANDIDATE_BUNDLE --output comparison.xml
```

Changed expectations/profile/settings mean incomparable. Incomplete coverage stays
incomplete. A candidate PASS after the same recorded contract FAIL can be fixed;
exact replay inputs do not guarantee identical scheduler interleavings. Execution
exit precedence is130/2/3/1/0, while offline processing success remains separate.

Actual before/after gate: `tests/qnx/qualify-phase6.py --prefix UNIQUE --fixed-source
LOCAL_SOURCE_WORKTREE`. Its source-fixed candidate must be committed, built with
qcc and have changed fixture hashes. The retained patch removes real broken
unblock behavior with the saved fixture setting unchanged. Main's intentional
negative controls are preserved. This gate's success never disguises the saved
and reproduced FAIL service runs.
