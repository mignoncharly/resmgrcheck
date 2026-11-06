"""Phase 3 local validation/expansion/evaluation tools; deployment remains manual."""
import argparse
import json
from pathlib import Path
import sys
from .contracts import load, Profile, Plan, Invalid, canonical
from .planning import expand
from .evaluator import evaluate, evaluate_persistent

def main():
    parser=argparse.ArgumentParser(prog='python3 -m resmgrcheck')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('validate'); p.add_argument('profile')
    p=sub.add_parser('plan'); p.add_argument('profile'); p.add_argument('--run-id',required=True); p.add_argument('--fixture-mode',choices=('corrected','ignore-unblock'),default='corrected'); p.add_argument('--output',required=True)
    p=sub.add_parser('evaluate'); p.add_argument('plan'); p.add_argument('events'); p.add_argument('--output',required=True); p.add_argument('--status')
    args=parser.parse_args()
    try:
        if args.command=='validate':
            Profile.parse(load(args.profile)); print('profile valid'); return 0
        if args.command=='plan':
            value=expand(Profile.parse(load(args.profile)),args.run_id,args.fixture_mode).data
            code=0
        else:
            with Path(args.events).open('rb') as f: raw=f.read(32*1024*1024+1)
            if len(raw)>32*1024*1024: raise Invalid('event stream exceeds 32 MiB')
            value=(evaluate_persistent(Plan.parse(load(args.plan)),raw,load(args.status)) if args.status else evaluate(Plan.parse(load(args.plan)),raw)).data
            code={'PASS':0,'FAIL':1,'ERROR':2,'UNSUPPORTED':3,'NOT_RUN':4}[value['verdict']]
        with Path(args.output).open('xb') as f: f.write(canonical(value)+b'\n')
        if args.command=='evaluate': print(value['verdict']+': '+', '.join(value['reasons']))
        return code
    except (Invalid,OSError) as e:
        print(f'ERROR: {e}',file=sys.stderr); return 2
if __name__=='__main__': sys.exit(main())
