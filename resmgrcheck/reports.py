"""Minimal offline CLI report. Detailed presentation follows the Phase 8 gate."""
import html
import json
from pathlib import Path

from .artifacts import atomic_write, guard_derived_output, inspect_bundle
from .contracts import require
from .workflow import inspect_execution


def report(source, output):
    source, output = Path(source), Path(output)
    guard_derived_output(output, [source])
    escape = lambda value: html.escape(str(value), quote=True)
    if (source / 'bundle.json').exists():
        require(source.resolve() not in output.resolve().parents, 'report output must be outside an immutable bundle')
        bundle = inspect_bundle(source)
        rows = [(bundle.plan.data['case_id'], bundle.result.data)]
        identity = bundle.manifest.data['bundle_id']
    else:
        request, summary, results = inspect_execution(source)
        for p in source.glob('cases/*/bundle'):
            require(p.resolve() not in output.resolve().parents, 'report output must be outside immutable case bundles')
        rows = [(r.data['case_id'], r.data) for r in results]
        identity = summary['request_sha256']
    body = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ResMgrCheck</title><main><h1>ResMgrCheck evidence</h1>'
    body += '<p>Recorded identity: <code>' + escape(identity) + '</code></p><p>Fixture defects and incomplete coverage retain their recorded outcomes. No verdict is calculated in the browser.</p>'
    body += '<table><caption>Required cases</caption><thead><tr><th scope="col">Case</th><th scope="col">Verdict</th><th scope="col">Completion</th><th scope="col">Reasons</th></tr></thead><tbody>'
    for name, result in rows:
        body += '<tr>' + ''.join('<td>' + escape(v) + '</td>' for v in (name, result['verdict'], result['completion'], ', '.join(result['reasons']))) + '</tr>'
    body += '</tbody></table>'
    for name, result in rows:
        body += '<details><summary>' + escape(name) + ' assertions and event references</summary><pre>' + escape(json.dumps(result, indent=2, sort_keys=True)) + '</pre></details>'
    body += '</main></html>\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(output, body.encode('utf-8'))
