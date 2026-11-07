import json,os
from datetime import datetime,timezone
from pathlib import Path
from django.core.management.base import BaseCommand
from .provision_administrator import local_operator
from control.backup import snapshot,restore_drill

class Command(BaseCommand):
    help='Protected local encrypted DB/evidence snapshot or isolated new-database restore drill. Never contacts QNX.'
    def add_arguments(self,parser):
        parser.add_argument('operation',choices=['create','restore-drill']);parser.add_argument('--archive',required=True);parser.add_argument('--key-file',required=True)
    def handle(self,*args,**options):
        local_operator()
        result=(snapshot if options['operation']=='create' else restore_drill)(options['archive'],options['key_file'])
        if options['operation']=='create':
            receipt=Path(options['archive']+'.receipt.json')
            result['created_at']=datetime.fromtimestamp(Path(options['archive']).stat().st_mtime,timezone.utc).isoformat()
            descriptor=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(descriptor,'w') as stream:json.dump(result,stream);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        self.stdout.write(json.dumps(result))
