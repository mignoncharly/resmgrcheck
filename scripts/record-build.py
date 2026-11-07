#!/usr/bin/env python3
"""Run after Make's QNX prerequisites have succeeded."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resmgrcheck.build_identity import source_hash
from resmgrcheck.registrations import REGISTRY
root=Path(__file__).resolve().parents[1]
out=root/'build/qnx-x86_64'
names=['runner','worker','targetctl']+sorted({r.fixture for r in REGISTRY.values()})
value={'kind':'native-build-record','schema_version':1,
       'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
       'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)),
       'source_tree_sha256':source_hash(root), 'compiler_variant':'gcc_ntox86_64',
       'binaries':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}}
(out/'build-info.json').write_text(json.dumps(value,indent=2)+'\n')
