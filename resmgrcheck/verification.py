"""Expected-outcome qualification; individual red service results remain red."""
from pathlib import Path
import re

from .artifacts import atomic_write
from .contracts import Profile, canonical, enum, load, obj, require, text, version
from .deployment import load_deployment
from .workflow import execute, inspect_execution, make_request, run_id


def verify(target, output, progress=print):
    definition = load('suites/release.json')
    obj(definition, 'kind schema_version id cases'); version(definition, 'verification-suite')
    require(definition['id'] == 'release' and type(definition['cases']) is list and 1 <= len(definition['cases']) <= 64, 'verification suite')
    prepared = []
    for case in definition['cases']:
        obj(case, 'id profile fixture_mode expected'); text(case['id'])
        require(type(case['profile']) is str and re.fullmatch(r'profiles/[A-Za-z0-9_-]+\.json', case['profile']), 'verification profile path')
        p = Profile.parse(load(case['profile']))
        require(case['fixture_mode'] in p.registration.fixture_modes, 'verification mode')
        obj(case['expected'], 'verdict reasons'); enum(case['expected']['verdict'], {'PASS', 'FAIL', 'ERROR', 'UNSUPPORTED', 'NOT_RUN'})
        require(type(case['expected']['reasons']) is list and 1 <= len(case['expected']['reasons']) <= 32 and
                len(set(case['expected']['reasons'])) == len(case['expected']['reasons']), 'verification expected reasons')
        for reason in case['expected']['reasons']: text(reason)
        prepared.append((case, p))
    require(len({c['id'] for c, _ in prepared}) == len(prepared), 'duplicate verification case')
    deployment = load_deployment(target)
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); path.mkdir()
    atomic_write(path / 'definition.json', canonical(definition) + b'\n')
    rows = []; stopped = False
    try:
        for case, profile in prepared:
            if stopped:
                rows.append({'id': case['id'], 'verdict': 'NOT_RUN', 'reasons': ['verification_quarantined'], 'matched': False, 'execution_exit': 3})
                continue
            request = make_request(target, profile, 'profile', case['fixture_mode'], deployment)
            progress('verify ' + case['id'])
            try:
                summary = execute(target, request, path / case['id'], lambda _: None)
                _, _, results = inspect_execution(path / case['id'])
                result = results[0].data
                matched = result['verdict'] == case['expected']['verdict'] and set(result['reasons']) == set(case['expected']['reasons'])
                rows.append({'id': case['id'], 'run_id': request.data['run_id'], 'verdict': result['verdict'],
                             'reasons': result['reasons'], 'matched': matched, 'execution_exit': summary['execution_exit']})
                for bundle in (path / case['id']).glob('cases/*/bundle/status.json'):
                    status = load(bundle)
                    if not status['cleanup_ok'] or status['unresolved']: stopped = True
            except (ValueError, OSError) as error:
                rows.append({'id': case['id'], 'run_id': request.data['run_id'], 'verdict': 'ERROR',
                             'reasons': [type(error).__name__], 'matched': False, 'execution_exit': 2})
                stopped = True
            progress(case['id'] + ': ' + rows[-1]['verdict'] + (' (expected)' if rows[-1]['matched'] else ' (MISMATCH)'))
    finally:
        code = 2 if stopped else 0 if len(rows) == len(prepared) and all(r['matched'] for r in rows) else 1
        value = {'kind': 'verification-result', 'schema_version': 1, 'suite': 'release',
                 'execution_exit': code, 'qualification_passed': code == 0, 'cases': rows,
                 'meaning': 'Expected-outcome checker qualification; individual service verdicts are unchanged'}
        atomic_write(path / 'result.json', canonical(value) + b'\n')
    return value
