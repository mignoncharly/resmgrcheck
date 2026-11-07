"""Protected local observability; observations never establish native service health."""
import json,os,re,shutil,stat,subprocess
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db.models import Count
from django.utils import timezone
from .provision_administrator import local_operator
from control.models import Run,Target,ExecutorSlot,AIProviderState

class Command(BaseCommand):
    help='Protected local JSON operations status: queue/lease/quarantine, free disk, backup age and (production) dedicated unit states. No QNX contact.'
    def add_arguments(self,parser):parser.add_argument('--backup-dir',default='/var/backups/resmgrcheck')
    def handle(self,*args,**options):
        local_operator();now=timezone.now();oldest=Run.objects.filter(state='queued').order_by('created_at').first()
        leases=list(ExecutorSlot.objects.filter(run__isnull=False).values('expires_at'));unknown_lease=any(not x['expires_at'] or x['expires_at']<=now for x in leases)
        receipts=[]
        root=Path(options['backup_dir'])
        if root.is_dir() and not root.is_symlink():
            for p in sorted(root.glob('*.rmc.receipt.json'))[-100:]:
                if p.is_symlink() or p.stat().st_uid not in {0,os.getuid()} or p.stat().st_mode&0o077 or p.stat().st_size>4096:continue
                try:
                    data=json.loads(p.read_text());created=datetime.fromisoformat(data['created_at'])
                    archive=p.with_name(p.name.removesuffix('.receipt.json'));info=archive.stat(follow_symlinks=False)
                    valid_file=stat.S_ISREG(info.st_mode) and info.st_uid in {0,os.getuid()} and not info.st_mode&0o077 and info.st_nlink==1 and info.st_size>=36
                    unchanged_time=created.tzinfo and abs(info.st_mtime-created.timestamp())<.01
                    if data.get('passed') and re.fullmatch(r'[0-9a-f]{64}',data.get('encrypted_sha256','')) and valid_file and unchanged_time and created<=now:receipts.append(created)
                except (OSError,ValueError,TypeError,KeyError):continue
        age=(now-max(receipts)).total_seconds() if receipts else None
        queue_age=(now-oldest.created_at).total_seconds() if oldest else None;units={}
        if settings.ENVIRONMENT=='production':
            for unit in ['resmgrcheck-db.service','resmgrcheck-web.service','resmgrcheck-executor.service']:
                result=subprocess.run(['systemctl','is-active',unit],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
                units[unit]=result.returncode==0
        disk=shutil.disk_usage(settings.MEDIA_ROOT if settings.MEDIA_ROOT.exists() else settings.MEDIA_ROOT.parent).free
        concerns=[]
        if unknown_lease:concerns.append('expired_or_unknown_executor_lease')
        if queue_age is not None and queue_age>120:concerns.append('old_queued_work')
        if age is None or age>36*3600:concerns.append('missing_or_stale_backup_receipt')
        if disk<1024**3:concerns.append('host_storage_low')
        if units and not all(units.values()):concerns.append('dedicated_service_inactive')
        if Target.objects.filter(state='quarantined').exists():concerns.append('target_quarantined')
        result={'observed_at':now.isoformat(),'production':settings.ENVIRONMENT=='production','queue_states':dict(Run.objects.values('state').annotate(n=Count('pk')).values_list('state','n')),
            'oldest_queue_seconds':queue_age,'expired_or_unknown_lease':unknown_lease,'quarantined_targets':Target.objects.filter(state='quarantined').count(),
            'host_free_bytes':disk,'backup_age_seconds':age,'backup_receipt_is_restore_proof':False,'service_active':units,'concerns':concerns,'qnx_contacted':False,'native_service_health':'not_measured'}
        self.stdout.write(json.dumps(result))
        if concerns:raise CommandError('Operational attention required: '+','.join(concerns))
