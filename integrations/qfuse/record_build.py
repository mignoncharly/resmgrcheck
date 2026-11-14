#!/usr/bin/env python3
"""Bind the optional qcc build to its original probe and pinned public sources."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
record = {'kind': 'qfuse-qnx-build', 'compiler': 'qcc', 'variant': sys.argv[1],
          'source_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
          'probe_source_sha256': sha(Path(__file__).with_name('probe.c')),
          'sources_lock_sha256': sha(Path(__file__).with_name('sources.lock.json')),
          'binary_sha256': sha(root / 'build/qfuse-integration/probe')}
(root / 'build/qfuse-integration/build.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
