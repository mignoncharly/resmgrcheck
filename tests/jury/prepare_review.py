#!/usr/bin/env python3
"""Package existing reviewed QNX evidence; never build or contact a target."""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.build_identity import source_hash

EVIDENCE = Path('docs/evidence/phase10')
LABELS = ('broken', 'after', 'job')
DOCS = ('docs/JURY_START_HERE.md', 'docs/jury/EVIDENCE_INDEX.md',
        'docs/jury/identities.json', 'docs/jury/source-fix.patch',
        'docs/submission/demo.srt', 'LICENSE')
RENDERED = {'docs/JURY_START_HERE.md': 'START_HERE.html',
            'docs/jury/EVIDENCE_INDEX.md': 'docs/jury/EVIDENCE_INDEX.html'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'href', 'src', 'poster'} and value: self.links.append(value)
            if key == 'id': self.ids.append(value)


def check_links(root):
    """Check every HTML/Markdown local reference and fragment after extraction."""
    root = Path(root).resolve(); count = 0; external = set()
    for path in sorted(root.rglob('*')):
        if path.suffix not in {'.html', '.md'}: continue
        if path.suffix == '.html':
            parser = Links(); parser.feed(path.read_text()); links = parser.links
            assert len(parser.ids) == len(set(parser.ids)), ('duplicate anchor', path)
        else:
            links = re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', path.read_text())
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme in {'https', 'http'}:
                external.add(link); continue  # Explicit source links, not fetched resources.
            assert not parsed.scheme and not parsed.netloc, ('nonportable URL', path, link)
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
            assert target == root or root in target.parents, ('outside package', path, link)
            assert target.is_file(), ('missing local artifact', path, link)
            if parsed.fragment:
                if target.suffix == '.html':
                    anchors = Links(); anchors.feed(target.read_text()); valid = anchors.ids
                else:
                    valid = [slug(line.lstrip('#').strip()) for line in target.read_text().splitlines() if line.startswith('#')]
                assert unquote(parsed.fragment) in valid, ('missing fragment', path, link)
            count += 1
    return {'local_references_checked': count, 'external_source_links': sorted(external)}


def slug(text):
    return re.sub(r'[^a-z0-9 -]', '', text.lower()).replace(' ', '-')


def markdown_document(text, source, destination):
    """Small presentation-only renderer for this guide's headings/tables/code/links."""
    def inline(value):
        def link(match):
            label, href = match.groups(); parts = urlsplit(href)
            if not parts.scheme and parts.path:
                target = os.path.normpath(str(Path(source).parent / parts.path))
                target = RENDERED.get(target, target)
                href = os.path.relpath(target, str(Path(destination).parent))
                if parts.fragment: href += '#' + parts.fragment
            return '<a href="' + escape(href, quote=True) + '">' + escape(label) + '</a>'
        # Escape all prose first; only deliberate Markdown spans create markup.
        value = escape(value)
        value = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', link, value)
        value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    output = []; paragraph = []; code = []; in_code = False; table = []
    def flush():
        if paragraph: output.append('<p>' + inline(' '.join(paragraph)) + '</p>'); paragraph.clear()
        if table:
            rows = [line.strip().strip('|').split('|') for line in table]
            for i, row in enumerate(rows):
                if i == 1 and all(re.fullmatch(r'\s*:?-+:?\s*', cell) for cell in row): continue
                cells = ''.join('<' + ('th' if i == 0 else 'td') + '>' + inline(cell.strip()) + '</' + ('th' if i == 0 else 'td') + '>' for cell in row)
                if i == 0: output.append('<div class="table"><table>')
                output.append('<tr>' + cells + '</tr>')
            output.append('</table></div>'); table.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            if in_code: output.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>'); code.clear(); in_code = False
            else: flush(); in_code = True
        elif in_code: code.append(line)
        elif line.startswith('#'):
            flush(); level = len(line) - len(line.lstrip('#')); title = line[level:].strip()
            output.append(f'<h{level} id="{slug(title)}">{inline(title)}</h{level}>')
        elif line.startswith('|'):
            if paragraph: flush()
            table.append(line)
        elif not line.strip(): flush()
        elif re.match(r'^\d+\. ', line):
            flush(); paragraph.append(line.strip())
        else: paragraph.append(line.strip())
    flush(); assert not in_code
    css = 'body{font:17px/1.55 system-ui,sans-serif;margin:0;color:#18283a;background:#fff}main{max-width:960px;margin:auto;padding:24px}h1,h2,h3{line-height:1.25}h2{margin-top:2em}a{color:#005bb5;overflow-wrap:anywhere}p,td{overflow-wrap:anywhere}pre{overflow:auto;background:#eef2f6;padding:16px;font-size:14px}code{font-family:monospace;overflow-wrap:anywhere}.table{overflow:auto}table{border-collapse:collapse;width:100%;min-width:480px}td,th{text-align:left;vertical-align:top;padding:10px;border:1px solid #cbd4df}@media(max-width:500px){main{padding:16px}}'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ResMgrCheck jury review</title><style>' + css + '</style><main>' + '\n'.join(output) + '</main></html>\n'


def scan(root):
    patterns = [rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----',
                rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'AKIA[0-9A-Z]{16}']
    count = 0
    for path in root.rglob('*'):
        if not path.is_file(): continue
        assert not path.is_symlink()
        assert not (set(path.relative_to(root).parts) & {'.local', '.qnx', 'build'})
        data = path.read_bytes()
        assert not data.startswith(b'\x7fELF'), ('native executable', path)
        assert not any(re.search(pattern, data) for pattern in patterns), ('secret signature', path)
        if path.suffix != '.mp4':
            assert b'/home/mignon/' not in data and b'ionos' not in data.lower(), ('private machine path', path)
        count += 1
    return {'files_scanned': count, 'findings': [], 'scope': 'Explicit allowlist plus ELF, private-machine paths, private-key and common-token signatures; not an exhaustive detector.'}


def prepare(out, video):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    package = out / 'resmgrcheck-jury'; package.mkdir()
    identities = json.loads((ROOT / 'docs/jury/identities.json').read_text())
    runtime = source_hash(ROOT)
    assert runtime == identities['cases']['broken']['builds']['source_tree_sha256']
    assert sha(video) == identities['recording']['sha256']
    selected = list(DOCS)
    for label in LABELS:
        case = EVIDENCE / 'executions' / ('p10demo2-' + label)
        bundle = inspect_bundle(ROOT / case / 'cases/timeout/bundle')
        expected = identities['cases'][label]
        assert bundle.manifest.data['bundle_id'] == expected['bundle_id']
        assert bundle.result.data['verdict'] == expected['verdict']
        assert bundle.status['cleanup_ok'] and not bundle.status['unresolved']
        selected.extend(str(case / name) for name in ('request.json','replay.json','state.json','result.json','report.html'))
        selected.extend(str(case / 'cases/timeout' / name) for name in ('plan.json','ack.json','events.jsonl','status.json','stderr.txt','result.json'))
        selected.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / case / 'cases/timeout/bundle').iterdir()))
        if label == 'after': selected.append(str(case / 'comparison.json'))
    selected.extend(str(EVIDENCE / name) for name in ('comparison/comparison.json', 'comparison/report.html', 'original-deployment.json', 'candidate-deployment.json'))
    originals = {name: sha(ROOT / name) for name in selected}
    for name in selected:
        destination = package / name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    shutil.copyfile(video, package / 'demo.mp4')
    for source, destination in RENDERED.items():
        (package / destination).write_text(markdown_document((ROOT / source).read_text(), source, destination))
    links = check_links(package); privacy = scan(package)
    manifest = {'kind':'portable-jury-review','schema_version':1,'product_checkpoint':identities['product_checkpoint'],
                'runtime_sha256':runtime,'packager_sha256':sha(__file__),'native_execution_for_packaging':False,
                'video_sha256':sha(video),'video_seconds':170,'public_video_url':None,
                'original_files':originals,'omissions':['private transport diagnostics','unrelated histories','SDK, runtime images, native executables and authenticated configuration'],
                'redactions_to_sealed_bundles':False,'link_checks':links,'privacy_review':privacy}
    (package / 'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sums = {str(p.relative_to(package)):sha(p) for p in sorted(package.rglob('*')) if p.is_file()}
    (package / 'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in sums.items()))
    archive = out / 'resmgrcheck-jury.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as target:
        for path in sorted(package.rglob('*')):
            if path.is_file(): target.write(path, str(path.relative_to(out)))
    with zipfile.ZipFile(archive) as target: assert target.testzip() is None
    (out / 'resmgrcheck-jury.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    assert originals == {name:sha(ROOT / name) for name in selected}, 'original material changed'
    return {'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'original_files_copied':len(originals),**links}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True); parser.add_argument('--video',required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, Path(args.video)),indent=2))
