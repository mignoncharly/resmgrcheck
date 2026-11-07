import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from control.models import Run,AccountDeletion,RateBucket
from control.retention import purge_run,erase_account,eligible
from control.engine import PolicyError

class Command(BaseCommand):
    help='Bounded local retention. Default dry run; never contacts QNX. --apply explicitly enables eligible removal.'
    def add_arguments(self,parser):parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        results=[]
        for run in Run.objects.filter(purged_at=None,finished_at__isnull=False).select_related('project__organization').order_by('finished_at')[:200]:
            if len(results)>=20:break
            if not eligible(run,timezone.now()):continue
            try:results.append(purge_run(run.pk,apply=options['apply']))
            except (OSError,ValueError,PolicyError) as error:results.append({'run_id':str(run.pk),'error':str(error) if isinstance(error,PolicyError) else 'local_retention_error','removed_claimed':False})
        for record in AccountDeletion.objects.filter(completed_at=None,due_at__lte=timezone.now())[:20]:
            try:results.append(erase_account(record.pk,apply=options['apply']))
            except PolicyError as error:results.append({'account_request_id':record.pk,'error':str(error)})
        if options['apply']:RateBucket.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(json.dumps({'apply':options['apply'],'results':results,'qnx_target_contacted':False}))
