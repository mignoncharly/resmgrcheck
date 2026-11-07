"""Offline views of canonical saved outcomes; browser code only filters presentation."""
from collections import Counter
from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import shlex
from urllib.parse import quote

from .artifacts import atomic_write, bounded_read, guard_derived_output, inspect_bundle
from .contracts import Plan, canonical, load, loads, require
from .workflow import Request, inspect_execution

CSS = '''
:root{color-scheme:light;--ink:#182b3b;--muted:#465868;--line:#ccd6de;--paper:#f4f6f8}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.55 system-ui,sans-serif}
main{max-width:1280px;margin:auto;padding:24px}h1{font-size:2rem;line-height:1.2}h2{margin-top:2rem}h3{margin-top:1.5rem}
a{color:#084f9e}a:hover{text-decoration-thickness:3px}:focus-visible{outline:3px solid #965200;outline-offset:3px}
p,li,td,th,dd,code,summary{overflow-wrap:anywhere}code,pre{font-family:ui-monospace,monospace;font-size:.875rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:.4rem 0;max-width:100%}nav{display:flex;gap:1rem;flex-wrap:wrap}
section,.case-detail{background:white;border:1px solid var(--line);border-radius:8px;padding:16px;margin:16px 0}
.table-scroll{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;min-width:800px;font-size:.9rem}caption{text-align:left;font-weight:700;padding:8px 0}
th,td{min-width:120px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:10px 8px}th{background:#eef2f5}th:first-child{min-width:110px}
.badge{font-weight:750;padding:2px 7px;border:1px solid currentColor;border-radius:4px;white-space:nowrap;display:inline-block}
.PASS{color:#075b34;background:#e6f6ed}.FAIL{color:#8a2020;background:#ffecec}.ERROR{color:#793900;background:#fff0da}
.UNSUPPORTED,.NOT_RUN,.UNRECORDED{color:#465267;background:#eef1f6}.warning{border-left:5px solid #965200;padding:12px;background:#fff0da}
.muted{color:var(--muted)}.facts{display:grid;grid-template-columns:minmax(120px,180px) minmax(0,1fr);gap:6px 16px}.facts dt{font-weight:700}.facts dd{margin:0}
summary{cursor:pointer;font-weight:650;padding:6px 0}details:target{outline:3px solid #965200}button,select{font:inherit;padding:6px;margin-right:8px}
.filter{padding:12px 0}small{font-size:.85rem}[hidden]{display:none!important}.event-list{padding-left:20px}
@media(max-width:600px){main{padding:12px}h1{font-size:1.6rem}section,.case-detail{padding:12px}.facts{grid-template-columns:1fr}.facts dd{margin-bottom:8px}th,td{padding:7px 6px}}
@media print{body{background:white}main{max-width:none}.filter{display:none}.table-scroll{overflow:visible}}
'''
JS = '''
const controls = document.getElementById('filters');
const select = document.getElementById('verdict-filter');
if (controls && select) {
  controls.hidden = false;
  select.addEventListener('change', () => {
    document.querySelectorAll('[data-verdict]').forEach(node => {
      node.hidden = select.value !== 'ALL' && node.dataset.verdict !== select.value;
    });
  });
  document.getElementById('reset-filter').addEventListener('click', () => {
    select.value = 'ALL'; select.dispatchEvent(new Event('change')); select.focus();
  });
}
function discloseAnchor() {
  const target = document.getElementById(location.hash.slice(1));
  if (target) { target.hidden = false; let parent = target; while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement; } }
}
window.addEventListener('hashchange', discloseAnchor); discloseAnchor();
'''


def esc(value):
    return html.escape(str(value), quote=True)


def pretty(value):
    return '<pre>' + esc(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)) + '</pre>'


def badge(verdict):
    # Class names are chosen from fixed labels, never input text.
    style = verdict if verdict in {'PASS', 'FAIL', 'ERROR', 'UNSUPPORTED', 'NOT_RUN', 'UNRECORDED'} else 'UNRECORDED'
    return '<span class="badge ' + style + '">' + esc(verdict) + '</span>'


def table(caption, headers, rows):
    return ('<div class="table-scroll"><table><caption>' + esc(caption) + '</caption><thead><tr>' +
            ''.join('<th scope="col">' + esc(h) + '</th>' for h in headers) + '</tr></thead><tbody>' +
            ''.join('<tr>' + ''.join('<td>' + cell + '</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table></div>')


@dataclass
class Case:
    plan: dict
    result: dict
    bundle: object = None
    location: Path = None


def _events(bundle):
    if not bundle:
        return {}
    # Stop at the first malformed frame. Later bytes remain raw evidence, not a
    # trusted timeline. Integrity/canonical evaluation was checked before rendering.
    records = {}
    for index, line in enumerate(bundle.raw.splitlines(keepends=True)):
        try:
            if not line.endswith(b'\n'): break
            value = loads(line, 16384)
        except ValueError:
            break
        if value.get('kind') == 'producer-event': records[index] = value
    return records


def _elapsed(events, refs=None):
    rows = [v for k, v in events.items() if refs is None or k in refs]
    times = [int(e['ns']) for e in rows]
    return f'{(max(times)-min(times))/1000000:.2f} ms' if times else 'unobserved'


def _facts(values):
    return '<dl class="facts">' + ''.join('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>' for k, v in values) + '</dl>'


class Renderer:
    def __init__(self, source, output):
        self.source = source
        self.output = output

    def link(self, path, label):
        relative = os.path.relpath(Path(path).resolve(), self.output.parent.resolve())
        return '<a href="' + esc(quote(relative, safe='/')) + '">' + esc(label) + '</a>'

    def artifacts(self, directory, names):
        links = [self.link(directory / n, n) for n in names if (directory / n).is_file()]
        return '<ul>' + ''.join('<li>' + link + '</li>' for link in links) + '</ul>' if links else '<p>No finalized artifacts available.</p>'

    def page(self, content, title='ResMgrCheck report'):
        return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
                '<title>' + esc(title) + '</title><style>' + CSS + '</style></head><body><main>' +
                '<h1>' + esc(title) + '</h1>' + content +
                '<footer><p class="muted">ResMgrCheck · Offline evidence view · No network assets. '
                'Saved evaluator outcomes are authoritative; filters only change presentation.</p></footer>'
                '</main><script>' + JS + '</script></body></html>\n')

    def partial(self):
        info = {}
        for name in ('partial.json', 'state.json'):
            if (self.source / name).exists(): info[name] = load(self.source / name)
        plan = None
        if (self.source / 'plan.json').exists(): plan = Plan.parse(load(self.source / 'plan.json')).data
        request = Request.parse(load(self.source / 'request.json')).data if (self.source / 'request.json').exists() else None
        body = ('<section id="summary"><h2>Run summary</h2>' + badge('ERROR') +
                '<p class="warning">INCOMPLETE: no finalized evaluated results. Required coverage and service health are unestablished. '
                'No passing conclusion is available.</p><p>Source: <code>' + esc(self.source) + '</code></p>')
        if request: body += pretty({'run_id': request['run_id'], 'required_cases': [p['case_id'] for p in request['cases']], 'target': request['target_identity']})
        if plan: body += pretty({'run_id': plan['run_id'], 'case_id': plan['case_id'], 'profile': plan['profile']['id']})
        body += '</section><section><h2>Cases and observations</h2><p>No sealed case results are available. Missing pending, result, state, health and cleanup observations are not inferred.</p>'
        body += pretty(info) if info else '<p>No collection state was recorded.</p>'
        body += '</section><section><h2>Replay</h2><p>Use the existing run ID with status/collect to recover evidence. Do not relaunch an uncertain request. Replay requires finalized saved inputs.</p></section>'
        body += '<section><h2>Evidence</h2>' + self.artifacts(self.source, ('partial.json', 'request.json', 'state.json', 'plan.json', 'observations.jsonl', 'status.json', 'replay.json')) + '</section>'
        return self.page(body, 'ResMgrCheck incomplete evidence')

    def case_detail(self, case, entry, cycle, index, records):
        key = 'case-' + str(index)
        refs = {r for a in entry['assertions'] for r in a['event_refs']}
        title = case.plan['case_id'] + (' · cycle ' + str(cycle) if cycle else ' · aggregate')
        body = '<details class="case-detail" id="' + key + '" data-verdict="' + esc(entry['verdict']) + '"><summary>' + badge(entry['verdict']) + ' ' + esc(title) + '</summary>'
        body += _facts([('Attempt', esc(case.plan['attempt_id'])), ('Completion', esc(entry.get('completion', case.result['completion']))),
                        ('Reasons', esc(', '.join(entry['reasons']))), ('Elapsed observed interval', esc(_elapsed(records, refs) if cycle else _elapsed(records)))])
        assertions = []
        for a in entry['assertions']:
            observed = a.get('observed', {})
            links = ' '.join('<a href="#event-' + str(case.plan['case_id']) + '-' + str(ref) + '">#' + str(ref) + '</a>' if ref in records else esc('#' + str(ref) + ' unavailable') for ref in a['event_refs'])
            # Expected/observed records were produced by the canonical evaluator.
            event_values = [{'ref': ref, 'event': records[ref]['event'], 'data': records[ref]['data']} for ref in a['event_refs'] if ref in records]
            actual = {'events': event_values, 'status': observed.get('status')}
            assertions.append([esc(a['id']) + '<br>' + badge(a['verdict']) + '<br>' + esc(a.get('reason', 'unrecorded')),
                               pretty(a.get('expected', 'unrecorded')), links + pretty(actual)])
        body += table('Declared obligations and actual observations', ['Obligation / verdict / reason', 'Expected', 'Observed / source event references'], assertions)
        if not records: body += '<p class="warning">Required raw observations were not collected. No service health or cleanup success is inferred.</p>'
        return body + '</details>'

    def run(self, cases, summary, request=None):
        complete = summary['completion'] == 'complete'
        counts = Counter(c.result['verdict'] for c in cases)
        required_missing = any(v in counts for v in ('UNSUPPORTED', 'NOT_RUN')) or not complete or not cases
        root_exit = summary.get('execution_exit')
        outcome = ('ERROR' if root_exit in {2, 130} else 'UNSUPPORTED' if root_exit == 3 else
                   'FAIL' if 'FAIL' in counts else 'ERROR' if 'ERROR' in counts else
                   'UNSUPPORTED' if 'UNSUPPORTED' in counts else 'NOT_RUN' if required_missing else 'PASS')
        body = '<nav aria-label="Report sections">' + ''.join('<a href="#' + k + '">' + label + '</a>' for k, label in [('summary','Summary'),('cases','Cases'),('timeline','Timeline'),('replay','Replay'),('evidence','Evidence')]) + '</nav>'
        body += '<section id="summary"><h2>Run summary</h2>' + badge(outcome)
        body += '<p>Completion: <strong>' + esc(summary['completion']) + '</strong>. Required coverage: <strong>' + ('INCOMPLETE / unavailable' if required_missing else 'complete') + '</strong>.</p>'
        if required_missing: body += '<p class="warning">Required coverage is incomplete or unsupported. Successful diagnostics do not replace missing obligations.</p>'
        if summary.get('host_error'): body += '<p class="warning">Host/infrastructure condition: ' + esc(summary['host_error']) + '</p>'
        profile = cases[0].plan['profile'] if cases else None
        observed_target = loads((cases[0].bundle.path / 'target-manifest.json').read_bytes())['target'] if cases and cases[0].bundle else None
        body += _facts([('Run ID', esc(summary['run_id'])), ('Profile / adapter', esc(profile['id'] + ' / ' + profile['adapter']['id']) if profile else 'unrecorded'),
                        ('Configured service path', esc(profile['service']['device']) if profile else 'unrecorded'),
                        ('Observed target', esc(observed_target['sysname'] + ' ' + observed_target['release'] + ' / ' + observed_target['machine']) if observed_target else 'unobserved'),
                        ('Native source', esc(cases[0].plan['builds']['source_revision'] + (' (dirty source; see full digest)' if cases[0].plan['builds']['dirty'] else ' (clean)')) if cases else 'unrecorded'),
                        ('Fixture setting', esc(cases[0].plan['fixture_mode']) if cases else 'unrecorded'),
                        ('Case counts', esc(', '.join(k + '=' + str(counts[k]) for k in ('PASS','FAIL','ERROR','UNSUPPORTED','NOT_RUN')))),
                        ('Source location', '<code>' + esc(self.source) + '</code>')])
        if request:
            body += '<details><summary>Configured target and deployment · ' + esc(request['target']) + '</summary>' + pretty({'target': request['target'], 'compatibility': request['target_identity'], 'deployment_id': request['deployment']['deployment_id'], 'native_build': request['deployment']['build'], 'management_helper': request['deployment']['manager']}) + '</details>'
        else: body += '<details><summary>Native build and executable hashes</summary>' + pretty(cases[0].plan['builds']) + '</details>'
        for c in cases:
            if c.bundle:
                manifest = loads((c.bundle.path / 'target-manifest.json').read_bytes())
                body += '<details><summary>Observed QNX target / evaluator · ' + esc(c.plan['case_id']) + '</summary>' + pretty({'target': manifest['target'], 'tool_version': manifest['tool_version'], 'adapter_abi': manifest['adapter_abi'], 'capabilities': manifest['capabilities'], 'bundle_id': c.bundle.manifest.data['bundle_id'], 'evaluator': c.bundle.manifest.data['evaluator']}) + '</details>'
        body += '<details><summary>Service usability and recovery scope</summary>'
        for c in cases:
            checks = [a for e in [c.result] + c.result.get('cycles', []) for a in e['assertions'] if a['id'] in {'fresh_client_health','owned_process_cleanup','single_instance'}]
            body += '<p><strong>' + esc(c.plan['case_id']) + '</strong>: ' + '; '.join(esc(a['id']) + ' ' + badge(a['verdict']) for a in checks) + ('' if checks else 'No health or cleanup conclusion recorded.') + '</p>'
            if c.plan['profile']['service']['mode'] == 'external-attach':
                body += '<p class="warning">External diagnostic only: running service build and instance identity are unverified. Public health does not establish original-instance survival.</p>'
            elif 'service_interference' in c.result['reasons']:
                body += '<p class="warning">Service interference was observed. A later probe cannot establish health of the original instance. Restart/recovery is separate from original health.</p>'
            else:
                body += '<p class="muted">Health obligations refer to the original managed service instance. Recovery after restart cannot satisfy them.</p>'
        body += '</details></section><section id="cases"><h2>Required cases and cycles</h2><p>Each repeat cycle is required. Aggregate and cycle verdicts are saved separately.</p>'
        body += '<div id="filters" class="filter" hidden><label for="verdict-filter">Show verdict: </label><select id="verdict-filter"><option value="ALL">All recorded outcomes</option>' + ''.join('<option value="' + v + '">' + v + '</option>' for v in ('PASS','FAIL','ERROR','UNSUPPORTED','NOT_RUN')) + '</select><button type="button" id="reset-filter">Show all</button></div><noscript><p>All cases and details are available without JavaScript.</p></noscript>'
        rows, details, timelines = [], [], []
        index = 0
        for c in cases:
            records = _events(c.bundle)
            entries = [(None, c.result)] + [(e['cycle'], e) for e in c.result.get('cycles', [])]
            for cycle, entry in entries:
                refs = {r for a in entry['assertions'] for r in a['event_refs']}
                pre = next((a['verdict'] for a in entry['assertions'] if a['id']=='pending_precondition'), 'not recorded / see obligations')
                index += 1
                cells = ['<a href="#case-' + str(index) + '">' + esc(c.plan['case_id']) + '</a>', esc(cycle if cycle else 'aggregate'), esc(c.plan['attempt_id']), badge(entry['verdict']), esc(', '.join(entry['reasons'])), esc(_elapsed(records, refs) if cycle else _elapsed(records)), esc(pre)]
                rows.append('<tr data-verdict="' + esc(entry['verdict']) + '">' + ''.join('<td>' + cell + '</td>' for cell in cells) + '</tr>')
                details.append(self.case_detail(c, entry, cycle, index, records))
            timelines.append(self.timeline(c, records))
        body += '<div class="table-scroll"><table><caption>Saved evaluated outcomes</caption><thead><tr>' + ''.join('<th scope="col">' + x + '</th>' for x in ('Scenario','Cycle','Attempt','Verdict','Reasons','Elapsed observed interval','Pending precondition')) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></section>'
        body += '<section><h2>Case details</h2><p>Open a case to compare the declared obligation with exact recorded values. Event numbers reference zero-based NDJSON records.</p>' + ''.join(details) + '</section>'
        body += '<section id="timeline"><h2>Observed event timeline</h2><p>Times are target CLOCK_MONOTONIC offsets within each native case, not wall-clock or host durations. A configured/armed deadline is not an observed expiry. No events are invented to fill gaps.</p>' + ''.join(timelines) + '</section>'
        body += self.replay(cases, request)
        body += '<section id="evidence"><h2>Evidence and instrumentation</h2><p>Managed examples use explicit lab pending/unblock/state and ordering instrumentation. Deliberate defect settings remain disclosed and are checked against the corrected contract. These directed tests do not establish exhaustive concurrency or absence of memory leaks.</p>'
        body += self.artifacts(self.source, ('request.json','replay.json','state.json','result.json','comparison.json'))
        for c in cases:
            directory = c.bundle.path if c.bundle else c.location
            body += '<details><summary>' + esc(c.plan['case_id']) + ' raw artifacts</summary>' + self.artifacts(directory, ('bundle.json','plan.json','profile.json','builds.json','target-manifest.json','observations.jsonl','status.json','result.json','replay.json','notes.txt','partial-events.jsonl','stderr.txt')) + '</details>'
        if (self.source / 'history').is_dir():
            body += '<h3>Prior collection history</h3><p>Earlier uncertainty/interruption remains preserved even after successful collection.</p>'
            for p in sorted((self.source / 'history').glob('collection-*')): body += '<p>' + self.link(p / 'result.json', p.name + '/result.json') + ' · ' + self.link(p / 'state.json', 'state.json') + '</p>'
        return self.page(body + '</section>')

    def timeline(self, case, records):
        if not records: return '<h3>' + esc(case.plan['case_id']) + '</h3><p class="warning">No trusted raw producer observations available. Pending, trigger, result, state, health and cleanup are unobserved.</p>'
        first = min(int(e['ns']) for e in records.values())
        groups = {'Pending': {'pending', 'pending_confirmed'}, 'Arming / directed trigger': {'deadline','trigger_requested','ordering_stage','barrier_wait','operation_armed'},
                  'Operation result': {'result','harness_error'}, 'State': {'control_result'}, 'Fresh client': {'result'}, 'Cleanup': {'cleanup','reaped','fixture_stop'}}
        all_refs = {r for e in [case.result] + case.result.get('cycles', []) for a in e['assertions'] for r in a['event_refs']}
        body = '<details><summary>' + esc(case.plan['case_id']) + ' · ' + str(len(records)) + ' producer observations</summary>'
        # Explicit coverage of absent stages is distinct from a synthetic event.
        for label, names in groups.items():
            found = [e for e in records.values() if e['event'] in names and (label != 'Fresh client' or e['data'].get('operation')=='health') and (label != 'State' or e['data'].get('operation')=='state')]
            body += '<p>' + esc(label) + ': ' + ('observed (' + str(len(found)) + ')' if found else '<strong>not observed</strong>') + '</p>'
        rows = []
        for ref, e in sorted(records.items(), key=lambda pair:(int(pair[1]['ns']), pair[0])):
            # Keep every event used by any saved assertion plus all actual trigger,
            # result, deadline and cleanup records. Full bytes stay linked below.
            if ref not in all_refs and e['event'] not in set.union(*groups.values()) and e['event'] not in {'unblock','cycle_start','cycle_end','run_final','phase','stage','signal_request','signal_sent','armed'}: continue
            rows.append(['<span id="event-' + esc(case.plan['case_id']) + '-' + str(ref) + '">#' + str(ref) + '</span>', f'{(int(e["ns"])-first)/1000000:.3f}', esc(e.get('cycle',1)), esc(e['producer']) + ' ' + esc(e['pid']), esc(e['event']), pretty(e['data'])])
        body += table('Actual events and assertion source references', ['Record','Target offset ms','Cycle','Producer / PID','Event','Recorded values'], rows)
        return body + '<p>' + self.link(case.bundle.path / 'observations.jsonl', 'Complete raw event stream') + '</p></details>'

    def replay(self, cases, request):
        body = '<section id="replay"><h2>Replay these saved inputs</h2><p>Run from the repository root with the lab prerequisites from README. Use a new output directory. Do not automatically retry an uncertain launch.</p>'
        pointer = self.source / 'replay.json'
        body += '<p>Saved inputs: ' + self.link(pointer, str(pointer)) + '</p>'
        if request:
            command = ['python3','-m','resmgrcheck','replay',str(pointer),'--target',request['target'],'--out','runs/replay-new']
            body += '<pre>' + esc(shlex.join(command)) + '</pre>'
            body += '<p>Original selected deployment: <code>' + esc(request['deployment']['deployment_id']) + '</code>. Native source/build and hashes are shown in the summary.</p>'
            if request['origin']: body += '<h3>Replay origin and disclosed changes</h3>' + pretty(request['origin'])
        else:
            body += '<pre>' + esc(shlex.join(['python3','-m','resmgrcheck','replay',str(self.source),'--candidate-manifest','PATH_TO_VERIFIED_CANDIDATE.json','--attempts','runs/replay-attempts','--run-id','new-unique-id'])) + '</pre>'
            body += '<p>Legacy sealed-case replay requires an explicit per-adapter candidate manifest and the reviewed local SSH route; replace PATH_TO_VERIFIED_CANDIDATE.json with the verified selection. See cli.md for prerequisites.</p>'
        body += '<p>Without candidate selection, workflow replay retains the original immutable deployment. To test an actual source correction, build and deploy it, then add <code>--candidate-manifest build/qnx-x86_64/manifest.json</code>. Keep the saved contract and fixture setting unchanged. Changing fixture mode is a disclosed incomparable contrast.</p>'
        if any(c.plan['profile']['service']['mode']=='external-attach' for c in cases): body += '<p class="warning">External changed-build replay is UNSUPPORTED: the actual running service build cannot be verified by this adapter. Use the scoped health diagnostic explicitly.</p>'
        return body + '</section>'

    def comparison(self, value):
        require(value.get('kind') in {'execution-comparison','run-comparison'} and value.get('schema_version')==1, 'report: expected version1 comparison')
        label = value.get('label', 'unrecorded')
        rows = value.get('cases', [value])
        body = '<section><h2>Comparison summary</h2><p class="badge">' + esc(label) + '</p>'
        if label in {'incomparable','incomplete','unsupported'}: body += '<p class="warning">This comparison cannot establish a corrected service. Inspect changed contracts, targets, settings and missing coverage.</p>'
        body += '<p>This view displays saved comparison metadata; it does not independently revalidate its source bundles. Verify the original/candidate bundle IDs in the source reports. A changed service build, contract and target are separate facts.</p>'
        body += _facts([('Original evidence',esc(value.get('original_location',value.get('original_bundle_id','unrecorded')))),
                            ('Candidate evidence',esc(value.get('candidate_location',value.get('candidate_bundle_id','unrecorded')))),
                            ('Original fixture setting',esc(value.get('original_mode','see case contract changes'))),
                            ('Candidate fixture setting',esc(value.get('candidate_mode','see case contract changes')))])
        body += '<details><summary>Full comparison identities and configured targets</summary>' + pretty({k:v for k,v in value.items() if k!='cases'}) + '</details></section>'
        for entry in rows:
            body += '<section><h2>' + esc(entry.get('case_id','Saved case')) + '</h2><p>Result: <strong>' + esc(entry.get('label','unrecorded')) + '</strong></p>'
            changes=entry.get('contract_changes')
            body += '<p>Same declared contract/settings: <strong>' + esc(entry.get('same_contract','unrecorded')) + '</strong>. Changed fields: ' + esc(', '.join(k for k,v in changes.items() if v) or 'none' if changes is not None else 'unrecorded') + '.</p>'
            body += '<p>Same recorded target/recipe context: <strong>' + esc(entry.get('target_compatible','unrecorded')) + '</strong>. Recipe changed: ' + esc(entry.get('recipe_changed','unrecorded')) + '.</p>'
            body += table('Saved outcome reasons', ['Original','Candidate'], [[esc(', '.join(entry.get('original_reasons',['unrecorded']))),esc(', '.join(entry.get('candidate_reasons',['unrecorded'])))]])
            body += table('Build, contract and target context', ['Context','Original','Candidate'], [
                ['Native source / executable hashes',pretty(entry.get('original_builds','unrecorded')),pretty(entry.get('candidate_builds','unrecorded'))],
                ['Observed QNX target',pretty(entry.get('original_target','not recorded in this comparison; inspect source bundles')),pretty(entry.get('candidate_target','not recorded in this comparison; inspect source bundles'))]])

            body += '<details><summary>Case comparison facts and bundle identities</summary>' + pretty({k:v for k,v in entry.items() if k not in {'original_builds','candidate_builds','original_target','candidate_target'}}) + '</details></section>'
        body += '<section><h2>Evidence and replay</h2><p>Open the original and candidate run reports for obligations, observations and replay inputs. Unknown target metadata is not evidence of compatibility.</p>' + self.link(self.source / 'comparison.json' if self.source.is_dir() else self.source, 'Saved comparison JSON') + '</section>'
        return self.page(body, 'ResMgrCheck comparison')


def report(source, output):
    source, output = Path(source), Path(output)
    require(source.exists(), 'report source does not exist')
    require(source.resolve() != output.resolve(), 'report output cannot replace its source')
    guard_derived_output(output, [source])
    renderer = Renderer(source, output)
    if source.is_file():
        body = renderer.comparison(load(source))
    elif (source / 'bundle.json').exists() and not (source / 'partial.json').exists():
        bundle = inspect_bundle(source)
        r = bundle.result.data
        body = renderer.run([Case(bundle.plan.data,r,bundle,source)], {'run_id':r['run_id'],'completion':r['completion']})
    elif (source / 'request.json').exists() and (source / 'result.json').exists():
        request, summary, results = inspect_execution(source)
        cases = []
        for plan, row, result in zip(request.data['cases'],summary['cases'],results):
            path = source / 'cases' / plan['case_id']
            bundle = inspect_bundle(path / 'bundle') if row['bundle_id'] else None
            cases.append(Case(plan,result.data,bundle,path))
        body = renderer.run(cases,summary,request.data)
    elif (source / 'comparison.json').exists():
        require(output.resolve() != (source / 'comparison.json').resolve(), 'report cannot replace comparison JSON')
        body = renderer.comparison(load(source / 'comparison.json'))
    else:
        body = renderer.partial()
    output.parent.mkdir(parents=True,exist_ok=True)
    atomic_write(output,body.encode('utf-8'))
