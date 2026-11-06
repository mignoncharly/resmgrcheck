"""Hash project source inputs without SDK, credentials or generated images."""
from pathlib import Path
import hashlib
from .contracts import canonical

def source_hash(root=Path('.')):
    root=Path(root)
    paths=[]
    for directory in ('native','resmgrcheck','scripts','third_party/cjson'):
        paths.extend(p for p in (root/directory).rglob('*') if p.is_file() and p.suffix in ('.c','.h','.py'))
    paths.append(root/'Makefile')
    return hashlib.sha256(canonical({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})).hexdigest()
