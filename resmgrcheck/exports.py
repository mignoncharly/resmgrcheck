"""Derived JUnit, execution exit precedence and contract-aware comparisons."""
import json
import xml.etree.ElementTree as ET

from .contracts import EvaluatedResult


def execution_exit(results, interrupted=False):
    if interrupted:
        return 130
    entries = [r.data if isinstance(r, EvaluatedResult) else r for r in results]
    verdicts = {r['verdict'] for r in entries}
    verdicts.update(c['verdict'] for r in entries for c in r.get('cycles', []))
    if 'ERROR' in verdicts:
        return 2
    if not entries or verdicts & {'UNSUPPORTED', 'NOT_RUN'}:
        return 3
    if any(r['completion'] != 'complete' for r in entries):
        return 3
    return 1 if 'FAIL' in verdicts else 0


def junit(bundles):
    """All currently expanded families/cycles are required; never waive them here."""
    return junit_runs([(b.plan.data, b.result.data, b.manifest.data['bundle_id'], str(b.path)) for b in bundles])


def junit_runs(runs):
    """A missing native bundle stays explicitly uncollected, never a forged ID."""
    root = ET.Element('testsuites')
    for plan, result, bundle_id, reference in runs:
        suite = ET.SubElement(root, 'testsuite', name='resmgrcheck.' + plan['profile']['id'])
        properties = ET.SubElement(suite, 'properties')
        for name, value in {'bundle_id': bundle_id or 'uncollected',
                            'bundle_path': json.dumps(reference, ensure_ascii=True),
                            'profile_sha256': plan['profile_sha256'], 'attempt_id': plan['attempt_id'],
                            'source_revision': plan['builds']['source_revision']}.items():
            ET.SubElement(properties, 'property', name=name, value=value)
        cases = [(plan['case_id'], result)]
        cases.extend((plan['case_id'] + '.cycle' + str(c['cycle']).zfill(2), c) for c in result.get('cycles', []))
        for name, entry in cases:
            case = ET.SubElement(suite, 'testcase', name=name, classname='resmgrcheck.' + plan['profile']['adapter']['id'])
            verdict = entry['verdict']
            tag = {'FAIL': 'failure', 'ERROR': 'error', 'UNSUPPORTED': 'skipped', 'NOT_RUN': 'skipped'}.get(verdict)
            if tag:
                child = ET.SubElement(case, tag, type=verdict, message=', '.join(entry['reasons']))
                child.text = json.dumps(entry, sort_keys=True, ensure_ascii=True)
            ET.SubElement(case, 'system-out').text = json.dumps({'bundle_id': bundle_id,
                                                               'assertions': entry['assertions']}, sort_keys=True, ensure_ascii=True)
        incomplete = result['completion'] != 'complete' or any(e['verdict'] in {'UNSUPPORTED', 'NOT_RUN'} for _, e in cases)
        if incomplete:
            case = ET.SubElement(suite, 'testcase', name='required-coverage', classname='resmgrcheck.coverage')
            ET.SubElement(case, 'error', type='incomplete_required_coverage',
                          message='Required cases or obligations did not complete; inspect ' + (bundle_id or reference))
        for key, tag in [('failures', 'failure'), ('errors', 'error'), ('skipped', 'skipped')]:
            suite.set(key, str(len(suite.findall('testcase/' + tag))))
        suite.set('tests', str(len(suite.findall('testcase'))))
    for key in ('tests', 'failures', 'errors', 'skipped'):
        root.set(key, str(sum(int(s.get(key)) for s in root)))
    return ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'


def compare(original, candidate):
    left, right = original.plan.data, candidate.plan.data
    before, after = original.result.data, candidate.result.data
    same_contract = (left['case_id'] == right['case_id'] and left['profile_sha256'] == right['profile_sha256']
                     and left['suite_sha256'] == right['suite_sha256'] and left['fixture_mode'] == right['fixture_mode'])
    from .contracts import loads
    old_target = loads((original.path / 'target-manifest.json').read_bytes())['target']
    new_target = loads((candidate.path / 'target-manifest.json').read_bytes())['target']
    target_compatible = old_target == new_target and left['builds']['recipe_id'] == right['builds']['recipe_id']
    compatible = same_contract and target_compatible
    if not compatible:
        label = 'incomparable'
    elif 'UNSUPPORTED' in (before['verdict'], after['verdict']):
        label = 'unsupported'
    elif any(r['completion'] != 'complete' or r['verdict'] in {'ERROR', 'NOT_RUN'} for r in (before, after)):
        label = 'incomplete'
    elif before['verdict'] == 'FAIL' and after['verdict'] == 'PASS':
        label = 'fixed'
    elif before['verdict'] == after['verdict'] == 'FAIL':
        label = 'still-failing'
    elif before['verdict'] == 'PASS' and after['verdict'] == 'FAIL':
        label = 'newly-failing'
    else:
        label = 'still-passing'
    def failures(result):
        assertions = list(result['assertions'])
        assertions.extend(a for cycle in result.get('cycles', []) for a in cycle['assertions'])
        return sorted({a.get('reason', a['id']) for a in assertions if a['verdict'] == 'FAIL'})
    old_failures, new_failures = failures(before), failures(after)
    known = compatible and after['verdict'] not in {'ERROR', 'UNSUPPORTED', 'NOT_RUN'} and after['completion'] == 'complete'
    return {'kind': 'run-comparison', 'schema_version': 1, 'label': label, 'same_contract': same_contract,
            'original_bundle_id': original.manifest.data['bundle_id'], 'candidate_bundle_id': candidate.manifest.data['bundle_id'],
            'original_builds': left['builds'], 'candidate_builds': right['builds'],
            'original_target': old_target, 'candidate_target': new_target,
            'contract_changes': {k: left[k] != right[k] for k in ('case_id','profile_sha256','suite_sha256','fixture_mode')},
            'target_compatible': target_compatible, 'recipe_changed': left['builds']['recipe_id'] != right['builds']['recipe_id'],
            'original_reasons': before['reasons'], 'candidate_reasons': after['reasons'],
            'original_failures': old_failures, 'candidate_failures': new_failures,
            'new_failures': sorted(set(new_failures) - set(old_failures)) if compatible else [],
            'reproduced': bool(set(old_failures) & set(new_failures)) if old_failures and known else None}
