"""Report regression over real saved QNX evidence and labelled synthetic edge cases."""
from html.parser import HTMLParser
from pathlib import Path
import json
import copy
from dataclasses import replace
import shutil
import tempfile
import unittest

from resmgrcheck.artifacts import create_bundle, sha256
from resmgrcheck.contracts import Invalid, canonical, load
from resmgrcheck.exports import junit
from resmgrcheck.reports import JS, esc, report
from resmgrcheck.workflow import compare_executions

ROOT=Path(__file__).resolve().parents[2]
RUNS=ROOT/'docs/evidence/phase7/executions'

class Structure(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.links=[];self.scripts=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.tags.append((tag,a))
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='script':self.scripts.append(a)

class Reports(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def render(self,source,name='report.html'):
        path=self.root/name;report(source,path);return path.read_text()
    def test_real_required_cycles_and_six_reader_questions(self):
        text=self.render(RUNS/'sensor-fixed');dom=Structure(text)
        for phrase in ('Run summary','Required cases and cycles','Declared obligations and actual observations',
                       'Observed event timeline','Replay these saved inputs','Evidence and instrumentation',
                       'pending_precondition','raw_errno','deadline_ns','original managed service instance'):
            self.assertIn(phrase,text)
        self.assertEqual(sum(tag=='details' and 'case-detail' in a.get('class','') for tag,a in dom.tags),26)
        self.assertTrue(any('observations.jsonl' in v for v in dom.links))
        self.assertIn('cycle 20',text);self.assertIn('target CLOCK_MONOTONIC',text)
        self.assertEqual(dom.scripts,[{}]);self.assertNotIn('innerHTML',JS)
        self.assertIn('<th scope="col">',text);self.assertIn('<noscript>',text)
    def test_real_unsupported_and_unknown_identity_are_explicit(self):
        text=self.render(RUNS/'sensor-external-lifecycle')
        self.assertIn('Required coverage: <strong>INCOMPLETE / unavailable',text)
        self.assertIn('service_mode_unsupported',text)
        self.assertEqual({a['data-verdict'] for tag,a in Structure(text).tags if 'data-verdict' in a}, {'UNSUPPORTED'})
        text=self.render(RUNS/'job-external')
        self.assertIn('running service build and instance identity are unverified',text)
        self.assertIn('External changed-build replay is UNSUPPORTED',text)
    def test_required_not_run_cycles_do_not_relabel_an_established_failure(self):
        text=self.render(RUNS/'release/sensor-repeat-retain-third')
        summary=text.split('<section id="summary">',1)[1].split('<section id="cases">',1)[0]
        self.assertTrue(summary.startswith('<h2>Run summary</h2><span class="badge FAIL">FAIL</span>'))
        self.assertIn('Required coverage: <strong>INCOMPLETE / unavailable',summary)
        self.assertIn('NOT_RUN',text)
        self.assertEqual(load(RUNS/'release/sensor-repeat-retain-third/result.json')['execution_exit'],3)

    def test_partial_or_empty_data_has_no_passing_conclusion(self):
        source=self.root/'empty';source.mkdir()
        for i in range(2):
            if i:(source/'partial.json').write_bytes(canonical({'kind':'partial-run','schema_version':1,'error_type':'synthetic formatting <script>alert(1)</script>'}))
            text=self.render(source,str(i)+'.html')
            self.assertIn('INCOMPLETE: no finalized evaluated results',text)
            self.assertNotIn('<span class="badge PASS">',text)
            self.assertNotIn('<script>alert(1)</script>',text)
            if i:self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',text)
    def test_actual_artifacts_and_junit_remain_byte_identical(self):
        from resmgrcheck.artifacts import inspect_bundle
        source=RUNS/'sensor-broken';files=[p for p in source.rglob('*') if p.is_file()]
        before={p:sha256(p.read_bytes()) for p in files}
        bundles=[inspect_bundle(p) for p in source.glob('cases/*/bundle')]
        xml=junit(bundles);text=self.render(source)
        self.assertIn('departure_unobserved',text);self.assertIn('pending_state_not_released',text)
        self.assertEqual(xml,junit(bundles));self.assertEqual(before,{p:sha256(p.read_bytes()) for p in files})
    def test_reports_cannot_replace_raw_partial_or_diagnostics(self):
        partial=self.root/'partial';partial.mkdir();(partial/'partial.json').write_text('{}')
        (partial/'observations.jsonl').write_text('synthetic preserved bytes')
        with self.assertRaises(Invalid):report(partial,partial/'observations.jsonl')
        self.assertEqual((partial/'observations.jsonl').read_text(),'synthetic preserved bytes')
        source=self.root/'run';shutil.copytree(RUNS/'uncertain',source)
        before=(source/'diagnostics/commands.json').read_bytes()
        with self.assertRaises(Invalid):report(source,source/'diagnostics/commands.json')
        self.assertEqual(before,(source/'diagnostics/commands.json').read_bytes())
    def test_tampered_sealed_result_cannot_be_presented_as_valid(self):
        source=self.root/'bundle';shutil.copytree(RUNS/'sensor-fixed/cases/timeout/bundle',source)
        (source/'result.json').write_text('{}')
        with self.assertRaises(Invalid):self.render(source)
        self.assertFalse((self.root/'report.html').exists())
    def test_changed_build_and_changed_setting_comparisons_remain_distinct(self):
        for tag,label in [('sensor-source-after','fixed'),('sensor-replay','incomparable')]:
            original='sensor-source-before' if label=='fixed' else 'sensor-broken'
            value=compare_executions(RUNS/original,RUNS/tag);self.assertEqual(value['label'],label)
            source=self.root/label;source.mkdir();(source/'comparison.json').write_bytes(canonical(value))
            text=self.render(source,label+'.html')
            self.assertIn('Observed QNX target',text);self.assertIn('contract_changes',text)
            self.assertIn(label,text);self.assertIn('Native source / executable hashes',text)
            self.assertEqual(load(source/'comparison.json'),value)
    def test_changed_target_or_recipe_cannot_claim_a_fixed_service(self):
        # Synthetic comparison-context mutations of actual saved native bundles;
        # these do not claim that another target/recipe was executed.
        from resmgrcheck.artifacts import inspect_bundle
        from resmgrcheck.contracts import Plan
        from resmgrcheck.exports import compare
        before=inspect_bundle(RUNS/'sensor-source-before/cases/timeout/bundle')
        after=inspect_bundle(RUNS/'sensor-source-after/cases/timeout/bundle')
        self.assertEqual(compare(before,after)['label'],'fixed')
        plan=copy.deepcopy(after.plan.data);plan['builds']['recipe_id']='0'*64
        result=compare(before,replace(after,plan=Plan.parse(plan)))
        self.assertEqual(result['label'],'incomparable');self.assertFalse(result['target_compatible'])
        native=load(after.path/'target-manifest.json');native['target']['version']='SYNTHETIC changed kernel'
        path=self.root/'target-context';path.mkdir();(path/'target-manifest.json').write_bytes(canonical(native))
        result=compare(before,replace(after,path=path))
        self.assertEqual(result['label'],'incomparable');self.assertIsNone(result['reproduced'])

    def test_strings_and_file_links_cannot_become_executable_markup(self):
        self.assertEqual(esc('</script><img src=x onerror="x">'),'&lt;/script&gt;&lt;img src=x onerror=&quot;x&quot;&gt;')
        source=self.root/'synthetic<svg onload=alert(1)>';source.mkdir()
        (source/'partial.json').write_bytes(canonical({'error_type':'SYNTHETIC '+('E'*3000)+' </script><img src=x onerror=alert(1)>'}))
        text=self.render(source);dom=Structure(text)
        self.assertFalse(any(tag in {'img','svg'} for tag,_ in dom.tags))
        self.assertTrue(any('%3Csvg' in v for v in dom.links))
        self.assertTrue(all(not href.startswith(('javascript:','https:','http:')) for href in dom.links))
    def test_actual_cleanup_failure_and_recovery_are_not_original_health(self):
        base=ROOT/'docs/evidence/phase5-clean-lifecycle';tag='sensor-repeat-ignore-unblock-cleanup'
        b=create_bundle(self.root/'cleanup',(base/(tag+'-plan.json')).read_bytes(),(base/(tag+'-events.jsonl')).read_bytes(),(base/(tag+'-status.json')).read_bytes())
        text=self.render(b.path);self.assertIn('cleanup_failed',text)
        self.assertIn('Recovery after restart cannot satisfy',text)
        self.assertIn('NOT_RUN',text);self.assertIn('FAIL',text);self.assertIn('ERROR',text)

if __name__=='__main__':unittest.main()
