import json
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from control.models import Run
from control.storage import seal,verify_inventory
from control.security import audit

class Command(BaseCommand):
    help='Verify an exact completed web run and add a v2 history inventory; never rewrites an older seal or launches QNX.'
    def add_arguments(self,parser):parser.add_argument('--run-id',required=True,type=str)
    def handle(self,*args,**options):
        with transaction.atomic():
            run=Run.objects.select_for_update(of=('self',)).select_related('project__organization','original').get(pk=options['run_id'])
            if run.state not in {'completed','blocked'} or run.purged_at or run.operation=='inventory':raise CommandError('Exact run is not eligible for local evidence inventory')
            summary,cleanup=seal(run)
            if summary!=run.summary:raise CommandError('Saved canonical summary changed; preserve evidence for inspection')
            verify_inventory(run);audit(None,'evidence.inventory_verified',run.project.organization,run.pk,version=2,qnx_target_contacted=False)
            self.stdout.write(json.dumps({'web_run_id':str(run.pk),'native_run_id':run.native_run_id,'inventory_version':2,'canonical_summary_unchanged':True,'qnx_target_contacted':False}))
