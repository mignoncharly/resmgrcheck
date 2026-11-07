#!/usr/bin/env python3
"""Run a fixed Django management command with protected local path configuration."""
import argparse,json,os,stat,sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);parser.add_argument('arguments',nargs=argparse.REMAINDER);options=parser.parse_args()
descriptor=os.open(options.config,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
    info=os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077 or info.st_size>16384:raise SystemExit('Expected root-owned0600 runtime configuration')
    data=json.loads(os.read(descriptor,16385))
finally:os.close(descriptor)
if not isinstance(data,dict) or any(not k.startswith('RMC_WEB_') or not isinstance(v,str) for k,v in data.items()):raise SystemExit('Invalid runtime configuration')
if not options.arguments or options.arguments[0]!='manage.py':raise SystemExit('Only explicit Django management commands are accepted')
root=Path(__file__).resolve().parents[2]
env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1',**data}
os.chdir(root);os.execve(sys.executable,[sys.executable,str(root/'manage.py'),*options.arguments[1:]],env)
