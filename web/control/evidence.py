"""Authenticated, bounded offline exports. Original native bytes are never edited."""
import hashlib,io,json,os,posixpath,tempfile,zipfile
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from django.conf import settings
from django.http import FileResponse,Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET
from resmgrcheck.contracts import canonical
from .models import Artifact
from .security import secure_account,audit,consume_rate,permission
from .execution_views import authorized_run
from .engine import PolicyError
from .storage import detail_cases,open_artifact,verify_inventory

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in {'href','src'} and value:self.links.append(value)

def verify_local_links(name,raw,members):
    parsed=Links();parsed.feed(raw.decode('utf-8'))
    for value in parsed.links:
        target=urlsplit(value)
        if target.scheme or target.netloc:raise PolicyError('offline_report_external_link')
        if not target.path:continue
        leaf=posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(target.path)))
        if leaf not in members:raise PolicyError('offline_report_missing_member')

def bundle_export(run):
    if run.purged_at or run.state not in {'completed','blocked'}:raise PolicyError('evidence_unavailable')
    detail_cases(run)
    verify_inventory(run)
    artifacts=list(Artifact.objects.filter(run=run).order_by('relative_path'))
    if not artifacts or len(artifacts)>512 or sum(a.byte_count for a in artifacts)>64*1024*1024:raise PolicyError('export_bound_or_missing_inventory')
    members={artifact.relative_path for artifact in artifacts}
    # Spool outside public/static roots. The private tmp directory is deployment owned.
    temporary=settings.PRIVATE_ROOT/'exports';temporary.mkdir(mode=0o700,parents=True,exist_ok=True)
    stream=tempfile.TemporaryFile(dir=temporary)
    index={'kind':'resmgrcheck-authorized-export','schema_version':1,'web_run_id':str(run.pk),
           'native_run_id':run.native_run_id,'project_id':str(run.project_id),'organization_id':str(run.project.organization_id),
           'evidence_scope':'Original sealed native bundles plus separately identified host/collection/report artifacts. Prior uncertainty remains history; cleanup is separate from service verdicts.',
           'native_verdicts':'Authoritative original deterministic evaluator only','files':{}}
    try:
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            for artifact in artifacts:
                with open_artifact(artifact) as source:raw=source.read()
                if artifact.content_type=='text/html':verify_local_links(artifact.relative_path,raw,members)
                archive.writestr('evidence/'+artifact.relative_path,raw)
                index['files']['evidence/'+artifact.relative_path]={'sha256':artifact.sha256,'bytes':artifact.byte_count}
            archive.writestr('EXPORT.json',canonical(index)+b'\n')
            archive.writestr('SHA256SUMS',''.join(entry['sha256']+'  '+name+'\n' for name,entry in index['files'].items()))
            archive.writestr('START_HERE.txt',
                'ResMgrCheck authorized offline evidence export\n\nExtract all files together, then open evidence/report.html in a browser.\n'
                'No QNX installation, server or JavaScript is required to inspect the report.\n'
                'Verify SHA256SUMS before inspection. EXPORT.json binds this package to its authorized web/native run identities.\n'
                'PASS: required obligations satisfied by complete evidence. FAIL: an established service obligation failed.\n'
                'ERROR: harness/infrastructure or required-evidence failure. UNSUPPORTED: required capability unavailable.\n'
                'NOT_RUN: required work withheld/not executed. Cancellation intent and cleanup are separate facts.\n'
                'history/ retains earlier partial collection where present; its uncertainty is not erased by later collection.\n'
                'Source/build hashes, original target observations, contracts and fixture controls remain in the original native manifests.\n'
                'Share only with explicitly authorized project members. This archive is not an access token and contains private engineering evidence.\n')
        stream.seek(0);return stream
    except BaseException:stream.close();raise

@secure_account
@require_GET
def download(request,run_id):
    run,role=authorized_run(request,run_id)
    permission(request.user,run.project_id,'download',target=run.target,run=run)
    if not consume_rate('evidence-export',str(request.user.pk),6,60):return render(request,'control/message.html',{'title':'Export rate limit','message':'Wait before requesting another evidence archive.'},status=429)
    try:stream=bundle_export(run)
    except (ValueError,OSError,PolicyError):
        audit(request.user,'evidence.export_withheld',run.project.organization,run.pk)
        return render(request,'control/message.html',{'title':'Evidence export unavailable','message':'Required evidence, inventory or local report links did not verify. No incomplete archive was returned.'},status=409)
    audit(request.user,'evidence.exported',run.project.organization,run.pk)
    response=FileResponse(stream,as_attachment=True,filename='resmgrcheck-'+str(run.pk)+'.zip',content_type='application/zip')
    response['Content-Security-Policy']="sandbox; default-src 'none'";return response
