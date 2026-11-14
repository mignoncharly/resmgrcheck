"""Compare an explicitly limited return-code predicate with canonical evidence."""
from pathlib import Path
from .artifacts import inspect_bundle, atomic_write, guard_derived_output
from .contracts import canonical, require, loads


def return_check(source, output):
    bundle = inspect_bundle(source)
    require(bundle.plan.data['case_id'] in {'timeout', 'signal'}, 'return-check requires a single timeout or signal case')
    guard_derived_output(output, [source])
    require(not Path(output).exists(), 'return-check output already exists')
    operation = 'timed' if bundle.plan.data['case_id'] == 'timeout' else 'signal'
    expected = bundle.plan.data['profile']['expectations']['cancel_error']
    records = [loads(line) for line in bundle.raw.splitlines()]
    matches = [(index, row) for index, row in enumerate(records) if row.get('producer') == 'worker'
               and row.get('event') == 'result' and row['data']['operation'] == operation]
    observed = None
    if len(matches) == 1:
        ref, row = matches[0]; data = row['data']; native = records[0]
        satisfied = (data['api'] == 'MsgSendv' and data['raw_return'] == -1
                     and data['error_name'] == expected and data['api_error'] == native['error_codes'][expected])
        observed = {'event_ref': ref, 'data': data}
        limited = 'SATISFIED' if satisfied else 'NOT_SATISFIED'
    else:
        limited = 'UNESTABLISHED'
    result = {'kind': 'return-code-comparison', 'schema_version': 1,
              'bundle_id': bundle.manifest.data['bundle_id'], 'native_run_id': bundle.plan.data['run_id'],
              'expected_error': expected, 'limited_predicate': limited, 'observed_return': observed,
              'canonical_verdict': bundle.result.data['verdict'], 'canonical_reasons': bundle.result.data['reasons'],
              'missed_obligations': [a for a in bundle.result.data['assertions'] if a['verdict'] == 'FAIL'],
              'meaning': 'Host analysis of one explicit return-code predicate over verified native observations. '
                         'No external test tool was executed or benchmarked. Canonical service verdict is unchanged.'}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    atomic_write(output, canonical(result) + b'\n')
    return result
