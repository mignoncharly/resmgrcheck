"""Immutable engine evidence, safe artifact inventories and no-follow reads."""
import hashlib,json,mimetypes,os,re,stat
from pathlib import Path,PurePosixPath
from django.conf import settings
from django.db import transaction
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.workflow import inspect_execution,compare_executions
from resmgrcheck.reports import report
from resmgrcheck.contracts import canonical,ProducerEvent,loads
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
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size!=artifact.byte_count:raise PolicyError('artifact_integrity_failed')
        digest=hashlib.sha256()
        for block in iter(lambda:stream.read(65536),b''):digest.update(block)
        if digest.hexdigest()!=artifact.sha256:raise PolicyError('artifact_integrity_failed')
        stream.seek(0);return stream
    except BaseException:stream.close();raise


def seal(run):
    path=run_path(run)
    previous={artifact.relative_path:artifact for artifact in Artifact.objects.filter(run=run)}
    for artifact in previous.values():
        with open_artifact(artifact):pass
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
    if 'report.html' not in previous:report(path,path/'report.html')
    if run.operation=='replay':
        comparison=compare_executions(run_path(run.original),path)
        if 'comparison.json' not in previous:(path/'comparison.json').write_bytes(canonical(comparison)+b'\n')
        comparison_dir=path/'comparison-view';comparison_dir.mkdir(exist_ok=True)
        if 'comparison-view/comparison.json' not in previous:(comparison_dir/'comparison.json').write_bytes(canonical(comparison)+b'\n')
        if 'comparison-view/report.html' not in previous:report(comparison_dir,comparison_dir/'report.html')
        sealed.extend(comparison_dir.iterdir())
    sealed.extend(path/name for name in ROOT_FILES if (path/name).is_file())
    sealed.extend(path/'cases'/case['case_id']/'result.json' for case in summary['cases'])
    for case in summary['cases']:
        if not case['bundle_id']:
            sealed.extend(path/'cases'/case['case_id']/name for name in ('plan.json','status.json','partial-events.jsonl','stderr.txt','replay.json') if (path/'cases'/case['case_id']/name).is_file())
    # P3 inventories remain immutable. A v2 inventory extends coverage to preserved
    # history and references the original inventory bytes instead of replacing it.
    if (path/'web-evidence.json').exists():
        if 'web-evidence.json' not in previous:raise PolicyError('unregistered_legacy_inventory')
        sealed.append(path/'web-evidence.json')
    # Earlier uncertainty is evidence too. These are original collection snapshots,
    # not a newly evaluated result or a replacement for the final native bundle.
    history=path/'history'
    if history.exists():
        if history.is_symlink() or not history.is_dir():raise PolicyError('history_type_invalid')
        for snapshot in history.iterdir():
            if not re.fullmatch(r'collection-[0-9]{6}',snapshot.name) or snapshot.is_symlink() or not snapshot.is_dir():raise PolicyError('history_path_invalid')
            for member in snapshot.rglob('*'):
                if member.is_symlink():raise PolicyError('history_type_invalid')
                parts=member.relative_to(snapshot).parts
                valid=(len(parts)==1 and parts[0] in {'result.json','state.json'} or
                       len(parts)==2 and parts[0] in {r['case_id'] for r in summary['cases']} and parts[1] in {'result.json','status.json','partial-events.jsonl'})
                if member.is_file():
                    if not valid:raise PolicyError('history_path_invalid')
                    sealed.append(member)
                elif not member.is_dir() or len(parts)!=1 or parts[0] not in {r['case_id'] for r in summary['cases']}:raise PolicyError('history_path_invalid')
    inventory={}
    for member in sorted(set(sealed)):
        if member.is_symlink() or not member.is_file() or member.stat().st_nlink!=1:raise PolicyError('artifact_type_invalid')
        raw=member.read_bytes()
        if len(raw)>32*1024*1024 or raw.startswith(b'\x7fELF'):raise PolicyError('artifact_bound_or_type_invalid')
        relative=member.relative_to(path).as_posix()
        inventory[relative]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if sum(v['bytes'] for v in inventory.values())>64*1024*1024:raise PolicyError('run_storage_quota_exceeded')
    seal_data={'kind':'web-evidence-inventory','schema_version':2,'run_id':str(run.pk),'native_run_id':run.native_run_id,
               'organization_id':str(run.project.organization_id),'project_id':str(run.project_id),'files':inventory}
    marker=path/'web-evidence-v2.json';encoded=canonical(seal_data)+b'\n'
    if marker.exists():
        if marker.is_symlink() or marker.read_bytes()!=encoded:raise PolicyError('sealed_inventory_changed')
    else:
        descriptor=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o640)
        with os.fdopen(descriptor,'wb') as stream:stream.write(encoded)
    inventory[marker.name]={'sha256':hashlib.sha256(marker.read_bytes()).hexdigest(),'bytes':marker.stat().st_size}
    with transaction.atomic():
        for name,entry in inventory.items():
            mime='text/html' if name.endswith('.html') else 'application/json' if name.endswith('.json') else 'text/plain'
            artifact,created=Artifact.objects.get_or_create(run=run,relative_path=name,defaults={'sha256':entry['sha256'],'byte_count':entry['bytes'],'content_type':mime})
            if not created and (artifact.sha256,artifact.byte_count,artifact.content_type)!=(entry['sha256'],entry['bytes'],mime):raise PolicyError('sealed_artifact_changed')
    return summary,bool(cleanup)


def run_directory_fd(run,relative=()):
    parts=(*run_path(run).relative_to(settings.MEDIA_ROOT).parts,*relative)
    descriptor=os.open(settings.MEDIA_ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for component in parts:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        return descriptor
    except BaseException:os.close(descriptor);raise


def detail_cases(run):
    """Use the existing canonical verifier; never invent a verdict in Django."""
    import json
    cases=[]
    for row in run.summary.get('cases',[]):
        name=row['case_id']
        if not row.get('bundle_id'):
            artifact=Artifact.objects.filter(run=run,relative_path='cases/'+name+'/result.json').first()
            if not artifact:
                cases.append({'name':name,'result':row,'events':[],'sealed':False});continue
            with open_artifact(artifact) as source:result=json.load(source)
            cases.append({'name':name,'result':result,'events':[],'sealed':False});continue
        descriptor=run_directory_fd(run,('cases',name,'bundle'))
        try:bundle=inspect_bundle(Path('/proc/self/fd')/str(descriptor))
        finally:os.close(descriptor)
        if bundle.manifest.data['bundle_id']!=row['bundle_id']:raise PolicyError('case_bundle_binding_changed')
        events=[];first=None
        for index,line in enumerate(bundle.raw.splitlines(keepends=True)):
            if not line.endswith(b'\n'):break
            try:event=loads(line,16384)
            except ValueError:break
            if event.get('kind')!='producer-event':continue
            try:ProducerEvent.parse(event)
            except ValueError:break
            ns=int(event['ns']);first=ns if first is None else first
            events.append({'index':index,'event':event['event'],'producer':event['producer'],'offset_ms':round((ns-first)/1000000,3),'data':event['data']})
        cases.append({'name':name,'result':bundle.result.data,'events':events,'sealed':True,'plan':bundle.plan.data,
                      'manifest':bundle.manifest.data,'status':bundle.status,'target':json.loads(bundle.raw.splitlines()[0])})
    return cases


def verify_inventory(run):
    """Check the immutable web inventory graph as well as original engine seals."""
    if run.purged_at:raise PolicyError('evidence_expired')
    artifacts={a.relative_path:a for a in Artifact.objects.filter(run=run)}
    name='web-evidence-v2.json' if 'web-evidence-v2.json' in artifacts else 'web-evidence.json'
    if name not in artifacts:raise PolicyError('sealed_inventory_missing')
    with open_artifact(artifacts[name]) as stream:inventory=json.load(stream)
    if (inventory.get('kind'),inventory.get('run_id'),inventory.get('native_run_id'),inventory.get('organization_id'),inventory.get('project_id'))!=('web-evidence-inventory',str(run.pk),run.native_run_id,str(run.project.organization_id),str(run.project_id)):raise PolicyError('inventory_identity_mismatch')
    files=inventory.get('files')
    if not isinstance(files,dict) or set(files)|{name}!=set(artifacts):raise PolicyError('inventory_graph_mismatch')
    for path,artifact in artifacts.items():
        if path!=name and files[path]!={'sha256':artifact.sha256,'bytes':artifact.byte_count}:raise PolicyError('inventory_artifact_mismatch')
        with open_artifact(artifact):pass
    return inventory
