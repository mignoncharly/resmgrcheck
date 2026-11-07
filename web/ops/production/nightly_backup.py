#!/usr/bin/env python3
"""Root-only timer wrapper. Exact private archive; no shell, key output or deletion."""
import os,sys
from datetime import datetime,timezone
from pathlib import Path
if os.geteuid()!=0:raise SystemExit('Protected local operator required')
base=Path(__file__).resolve().parent
archive='/var/backups/resmgrcheck/snapshot_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.rmc'
os.umask(0o077)
os.execv(sys.executable,[sys.executable,str(base/'runtime.py'),'--config','/etc/resmgrcheck/backup.json','manage.py','backup_snapshot','create','--archive',archive,'--key-file','/etc/resmgrcheck/keys/backup-key'])
