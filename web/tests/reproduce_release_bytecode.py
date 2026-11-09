#!/usr/bin/env python3
"""Unprivileged reproduction from trusted Git source + captured cache metadata.

No cache is opened, imported, decoded or changed. Only source bytes are compiled.
"""
import argparse,hashlib,importlib.util,json,re,struct,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ops/production'))
from release_bytecode import trusted_payloads

def main(observations):
    repo=Path(__file__).resolve().parents[2]
    data=json.loads(Path(observations).read_text());revision=data['revision']
    assert re.fullmatch('[0-9a-f]{40}',revision)
    root=Path('/opt/resmgrcheck/releases')/revision;rows=[]
    for row in data['caches']:
        name=row['source'];assert re.fullmatch(r'[A-Za-z0-9_/]+[.]py',name) and '..' not in Path(name).parts
        source=subprocess.check_output(['git','show',revision+':'+name],cwd=repo)
        assert hashlib.sha256(source).hexdigest()==row['source_sha256']
        path=root/name;live_source=path.read_bytes()
        assert live_source==source and int(path.stat().st_mtime)==row['source_mtime']
        header=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,row['source_mtime'],len(source))
        matches=[index+1 for index,payload in enumerate(trusted_payloads(source,str(path)))
            if hashlib.sha256(header+payload).hexdigest()==row['sha256']]
        rows.append({'source':name,'source_matches_Git':True,'full_cache_hash_reproduced':bool(matches),'trusted_compile_passes':matches})
    return {'scope':'unprivileged Git/source/header/full-cache-hash reproduction; no protected cache reads or modifications',
        'interpreter':sys.version.split()[0],'compared':len(rows),'passed':all(row['full_cache_hash_reproduced'] for row in rows),'files':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observations',required=True);args=parser.parse_args()
    result=main(args.observations);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
