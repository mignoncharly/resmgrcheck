import time,os
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.conf import settings
from control.ai_worker import refresh_provider,claim,execute

class Command(BaseCommand):
    help='Private optional AI worker; no QNX credentials/tools and no automatic provider retries.'
    def add_arguments(self,parser):parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        if settings.ENVIRONMENT=='production' and settings.SERVICE_ROLE!='ai':raise CommandError('Private AI role required')
        os.umask(0o077)
        while True:
            refresh_provider();job=claim()
            if job:execute(*job)
            if options['once']:return
            time.sleep(5)
