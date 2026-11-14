#!/usr/bin/env python3
"""Fetch only locked public sources; never SDK files, images or upstream history."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local/qfuse-review'


def prepare():
    lock = json.loads(Path(__file__).with_name('sources.lock.json').read_text())
    for project, base, prefix in (
        ('qfuse', 'https://raw.githubusercontent.com/gowtham0992/qfuse/' + lock['qfuse_revision'], CACHE),
        ('libfuse', 'https://raw.githubusercontent.com/libfuse/libfuse/' + lock['libfuse_tag'], CACHE / 'libfuse'),
    ):
        for name, expected in lock[project].items():
            path = prefix / name
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
                continue
            data = urllib.request.urlopen(base + '/' + name, timeout=30).read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('locked source differs: ' + project + '/' + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    output = CACHE / 'generated'; output.mkdir(exist_ok=True)
    source = (CACHE / 'libfuse/lib/fuse_opt.c').read_text()
    for header in ('fuse_config.h', 'fuse_i.h', 'fuse_misc.h'):
        include = '#include "' + header + '"'
        if source.count(include) != 1:
            raise ValueError('upstream parser include changed')
        source = source.replace(include, '/* QFuse standalone parser: private include removed. */')
    (output / 'fuse_opt.c').write_text('#include "fuse_log.h"\n' + source)
    (output / 'libfuse_config.h').write_text('/* Standalone QFuse parser configuration. */\n')
    print('Pinned public sources verified; LGPL parser preparation follows QFuse build recipe.')


if __name__ == '__main__':
    prepare()
