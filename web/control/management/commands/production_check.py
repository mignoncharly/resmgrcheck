"""Do not silently accept new deployment warnings; document deliberate HSTS choices."""
import json
from django.conf import settings
from django.core.checks import run_checks,WARNING
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help='Fail on unexpected Django deployment findings. Only non-preload/non-child-domain HSTS policy warnings are explicitly reviewed.'
    def handle(self,*args,**options):
        findings=run_checks(include_deployment_checks=True)
        approved={'security.W005':'HSTS covers this exact hostname only; no automatic child-domain commitment.',
            'security.W021':'No unreviewed browser preload submission or irreversible preload commitment.'}
        unexpected=[item.id for item in findings if item.level>=WARNING and item.id not in approved]
        self.stdout.write(json.dumps({'production_environment':settings.ENVIRONMENT=='production','finding_ids':[item.id for item in findings],
            'reviewed_exceptions':{item.id:approved[item.id] for item in findings if item.id in approved},'unexpected':unexpected,'https_runtime_verified':False}))
        if settings.ENVIRONMENT!='production' or unexpected:raise CommandError('Production configuration check failed')
