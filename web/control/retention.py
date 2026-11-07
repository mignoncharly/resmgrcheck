"""Exact owned local retention only. Never contacts or cleans the QNX target."""
from datetime import timedelta
import hashlib,os,re,stat
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.usersessions.models import UserSession
from .models import Run,Artifact,AccountDeletion,Membership,Invitation,User
from .jobs import ACTIVE
from .engine import PolicyError
from .storage import open_artifact,run_directory_fd,detail_cases,verify_inventory
from .security import audit

def eligible(run,now):
    return (not run.purged_at and not run.retention_hold and run.state in {'completed','cancelled','rejected'}
        and run.finished_at is not None and run.finished_at<now-timedelta(days=run.project.organization.retention_days)
        and not Run.objects.filter(original=run,state__in=ACTIVE).exists())

def permitted(name,case_names):
    parts=name.split('/')
    if len(parts)==1:return name in {'request.json','replay.json','state.json','result.json','comparison.json','report.html','web-evidence.json','web-evidence-v2.json','inventory.json'}
    if len(parts)==2 and parts[0]=='diagnostics':return parts[1] in {'commands.json','deployment-hashes.json'}
    if len(parts)==2 and parts[0]=='comparison-view':return parts[1] in {'comparison.json','report.html'}
    if parts[0]=='cases' and len(parts)>=3 and parts[1] in case_names:
        if len(parts)==3:return parts[2] in {'ack.json','plan.json','profile.json','status.json','events.jsonl','partial-events.jsonl','stderr.txt','replay.json','result.json'}
        return len(parts)==4 and parts[2]=='bundle' and parts[3] in {'bundle.json','plan.json','profile.json','builds.json','target-manifest.json','observations.jsonl','status.json','result.json','replay.json','notes.txt','stderr.txt'}
    if parts[0]=='history' and len(parts)>=3 and re.fullmatch(r'collection-[0-9]{6}',parts[1]):
        return (len(parts)==3 and parts[2] in {'state.json','result.json'} or len(parts)==4 and parts[2] in case_names and parts[3] in {'result.json','status.json','partial-events.jsonl'})
    return False

def removal_plan(fd,case_names,prefix='',entries=None):
    entries=[] if entries is None else entries
    if len(entries)>1024:raise PolicyError('retention_tree_bound')
    for name in sorted(os.listdir(fd)):
        if '/' in name or '\\' in name or name in {'.','..'}:raise PolicyError('retention_path_invalid')
        info=os.stat(name,dir_fd=fd,follow_symlinks=False);relative=prefix+name
        if info.st_uid!=os.getuid():raise PolicyError('retention_owner_unknown')
        if stat.S_ISDIR(info.st_mode):
            parts=relative.split('/')
            known=(relative in {'cases','diagnostics','comparison-view','history'} or
                len(parts)==2 and parts[0]=='cases' and parts[1] in case_names or
                len(parts)==3 and parts[0]=='cases' and parts[1] in case_names and parts[2]=='bundle' or
                len(parts)==2 and parts[0]=='history' and re.fullmatch(r'collection-[0-9]{6}',parts[1]) or
                len(parts)==3 and parts[0]=='history' and re.fullmatch(r'collection-[0-9]{6}',parts[1]) and parts[2] in case_names)
            if not known:raise PolicyError('retention_unknown_directory')
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try:removal_plan(child,case_names,relative+'/',entries)
            finally:os.close(child)
            entries.append((relative,info.st_dev,info.st_ino,'directory',0))
        elif stat.S_ISREG(info.st_mode) and info.st_nlink==1 and permitted(relative,case_names):
            if info.st_size>32*1024*1024:raise PolicyError('retention_file_bound')
            entries.append((relative,info.st_dev,info.st_ino,'file',info.st_size))
        else:raise PolicyError('retention_unknown_file_or_type')
    if sum(row[4] for row in entries)>128*1024*1024:raise PolicyError('retention_storage_bound')
    return entries

def remove_exact(root,entries):
    for relative,device,inode,kind,size in entries:
        parts=relative.split('/');parent=os.dup(root)
        try:
            for component in parts[:-1]:
                nextfd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);os.close(parent);parent=nextfd
            info=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
            if (info.st_dev,info.st_ino)!=(device,inode) or (kind=='file' and info.st_size!=size):raise PolicyError('retention_identity_changed')
            if kind=='directory':os.rmdir(parts[-1],dir_fd=parent)
            else:os.unlink(parts[-1],dir_fd=parent)
        finally:os.close(parent)

def purge_run(identifier,apply=False):
    now=timezone.now()
    with transaction.atomic():
        run=Run.objects.select_for_update().select_related('project__organization','actor').get(pk=identifier)
        if not eligible(run,now):raise PolicyError('retention_not_eligible')
        # Preserve unresolved cleanup/ownership. This service cannot guess it.
        if run.state=='completed' and run.operation!='inventory' and not (run.target_cleanup_verified or run.process_facts.get('no_native_launch_observed')):raise PolicyError('retention_cleanup_unknown')
        artifacts=list(Artifact.objects.filter(run=run))
        for artifact in artifacts:
            with open_artifact(artifact):pass
        if run.state=='completed' and run.operation!='inventory':
            verify_inventory(run);cases=detail_cases(run)
            if not run.process_facts.get('no_native_launch_observed') and any(not case['sealed'] or not case['status']['cleanup_ok'] or case['status']['unresolved'] for case in cases):raise PolicyError('retention_native_cleanup_unverified')
        try:descriptor=run_directory_fd(run)
        except FileNotFoundError:
            if artifacts or run.started_at:raise PolicyError('retention_evidence_missing')
            descriptor=None
        keep_descriptor=False
        try:
            names={row['case_id'] for row in run.summary.get('cases',[])}
            entries=removal_plan(descriptor,names) if descriptor is not None else []
            if apply:
                # Deny readers before deletion; metadata/hashes/audit remain immutable.
                run.purged_at=now;run.save(update_fields=['purged_at'])
                audit(None,'retention.purge_started',run.project.organization,run.pk,files=sum(row[3]=='file' for row in entries))
                keep_descriptor=True
        finally:
            if not keep_descriptor and descriptor is not None:os.close(descriptor)
    if not apply:return {'run_id':str(run.pk),'files':sum(row[3]=='file' for row in entries),'dry_run':True}
    try:
        if descriptor is not None:remove_exact(descriptor,entries)
    except (OSError,PolicyError):
        Run.objects.filter(pk=run.pk).update(purge_error='local_purge_incomplete_preserve_for_operator')
        audit(None,'retention.purge_incomplete',run.project.organization,run.pk)
        raise
    finally:
        if descriptor is not None:os.close(descriptor)
    audit(None,'retention.purged',run.project.organization,run.pk,metadata_retained=True,qnx_target_contacted=False)
    return {'run_id':str(run.pk),'files':sum(row[3]=='file' for row in entries),'dry_run':False}

def erase_account(identifier,apply=False):
    with transaction.atomic():
        record=AccountDeletion.objects.select_for_update().select_related('user').get(pk=identifier)
        user=User.objects.select_for_update().get(pk=record.user_id)
        if record.completed_at or record.due_at>timezone.now() or user.is_active:raise PolicyError('account_retention_not_due')
        if Membership.objects.filter(user=user,active=True).exists() or Run.objects.filter(actor=user,state__in=ACTIVE).exists():raise PolicyError('account_has_active_authority_or_work')
        if apply:
            replacement='deleted-'+user.pk.hex+'@deleted.invalid'
            for session in UserSession.objects.filter(user=user):session.end()
            UserSession.objects.filter(user=user).delete();EmailAddress.objects.filter(user=user).delete();Authenticator.objects.filter(user=user).delete()
            Invitation.objects.filter(email__iexact=user.email).update(email=replacement)
            user.email=replacement;user.first_name='';user.last_name='';user.last_login=None;user.set_unusable_password();user.session_version+=1
            user.save(update_fields=['email','first_name','last_name','last_login','password','session_version'])
            record.completed_at=timezone.now();record.save(update_fields=['completed_at']);audit(user,'account.personal_data_erased')
        return {'user_id':str(user.pk),'dry_run':not apply}
