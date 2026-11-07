import os,time
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.conf import settings
from control.worker import claim,execute_claim

class Command(BaseCommand):
    help='Private bounded executor. Do not run in the public HTTP process.'
    def add_arguments(self,parser):parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        if settings.ENVIRONMENT=='production' and settings.SERVICE_ROLE!='executor':raise CommandError('Private executor role required')
        os.umask(0o027)
        while True:
            job=claim()
            if job:execute_claim(*job)
            if options['once']:return
            time.sleep(1)
