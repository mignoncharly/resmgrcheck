"""Immutable engine evidence, safe artifact inventories and no-follow reads."""
import hashlib,json,mimetypes,os,stat
from pathlib import Path,PurePosixPath
from django.conf import settings
from django.db import transaction
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.workflow import inspect_execution,compare_executions
from resmgrcheck.reports import report
from resmgrcheck.contracts import canonical
from .engine import run_path,PolicyError
from .models import Artifact

ROOT_FILES={'request.json','replay.json','state.json','result.json','comparison.json','report.html','comparison.html'}

def open_artifact(artifact):
    """Open every component relative to the private root without following symlinks."""
    relative=PurePosixPath(artifact.relative_path)
    if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):raise PolicyError('artifact_path_invalid')
    root=run_path(artifact.run)
    components=(*root.relative_to(settings.MEDIA_ROOT).parts,*relative.parts)
    fd=os.open(settings.MEDIA_ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for component in components[:-1]:
            new=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
        final=os.open(components[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
    finally:os.close(fd)
    stream=os.fdopen(final,'rb')
    try:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size!=artifact.byte_count:raise PolicyError('artifact_integrity_failed')
        digest=hashlib.sha256()
        for block in iter(lambda:stream.read(65536),b''):digest.update(block)
        if digest.hexdigest()!=artifact.sha256:raise PolicyError('artifact_integrity_failed')
        stream.seek(0);return stream
    except BaseException:stream.close();raise


def seal(run):
    path=run_path(run)
    request,summary,results=inspect_execution(path)
    if request.data['run_id']!=run.native_run_id:raise PolicyError('native_run_identity_mismatch')
    if request.data['mode']!=run.fixture_mode and not (run.fixture_mode=='fixed' and request.data['mode']=='corrected'):
        raise PolicyError('native_fixture_setting_mismatch')
    cleanup=True;sealed=[]
    for case in summary['cases']:
        if not case['bundle_id']:
            cleanup=False;continue
        bundle=inspect_bundle(path/'cases'/case['case_id']/'bundle')
        cleanup=cleanup and bundle.status['cleanup_ok'] and not bundle.status['unresolved']
        sealed.extend(bundle.path.iterdir())
    report(path,path/'report.html')
    if run.operation=='replay':
        comparison=compare_executions(run_path(run.original),path)
        (path/'comparison.json').write_bytes(canonical(comparison)+b'\n')
        comparison_dir=path/'comparison-view';comparison_dir.mkdir(exist_ok=True)
        (comparison_dir/'comparison.json').write_bytes(canonical(comparison)+b'\n')
        report(comparison_dir,comparison_dir/'report.html')
        sealed.extend(comparison_dir.iterdir())
    sealed.extend(path/name for name in ROOT_FILES if (path/name).is_file())
    sealed.extend(path/'cases'/case['case_id']/'result.json' for case in summary['cases'])
    inventory={}
    for member in sorted(set(sealed)):
        if member.is_symlink() or not member.is_file():raise PolicyError('artifact_type_invalid')
        raw=member.read_bytes()
        if len(raw)>32*1024*1024 or raw.startswith(b'\x7fELF'):raise PolicyError('artifact_bound_or_type_invalid')
        relative=member.relative_to(path).as_posix()
        inventory[relative]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if sum(v['bytes'] for v in inventory.values())>64*1024*1024:raise PolicyError('run_storage_quota_exceeded')
    seal_data={'kind':'web-evidence-inventory','schema_version':1,'run_id':str(run.pk),'native_run_id':run.native_run_id,
               'organization_id':str(run.project.organization_id),'project_id':str(run.project_id),'files':inventory}
    marker=path/'web-evidence.json';marker.write_bytes(canonical(seal_data)+b'\n')
    inventory[marker.name]={'sha256':hashlib.sha256(marker.read_bytes()).hexdigest(),'bytes':marker.stat().st_size}
    with transaction.atomic():
        for name,entry in inventory.items():
            mime='text/html' if name.endswith('.html') else 'application/json' if name.endswith('.json') else 'text/plain'
            Artifact.objects.update_or_create(run=run,relative_path=name,defaults={'sha256':entry['sha256'],'byte_count':entry['bytes'],'content_type':mime})
    return summary,bool(cleanup)
