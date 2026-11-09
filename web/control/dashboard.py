"""Server-rendered dashboards use stored/verified engine data, not a second evaluator."""
from collections import Counter
import json,os,uuid
from pathlib import Path
from django.conf import settings
from django.db.models import Q
from django.http import Http404,HttpResponse,FileResponse
from django.shortcuts import render,get_object_or_404
from django.views.decorators.http import require_GET
from .models import Project,Run,Target,Membership,Artifact,AIAnalysis
from .security import secure_account,visible_projects,project_access,audit,is_code,visible_runs,visible_targets,visible_analyses,permission
from .execution_views import authorized_run
from .engine import run_path,PolicyError
from .storage import detail_cases,open_artifact,run_directory_fd,verify_inventory
from resmgrcheck.artifacts import inspect_bundle
from resmgrcheck.workflow import compare_executions
from resmgrcheck.registrations import PROFILES

PUBLIC_DEMOS={'before':'p10demo2-broken','after':'p10demo2-after','job':'p10demo2-job'}

@secure_account
@require_GET
def overview(request):
    projects=visible_projects(request.user).select_related('organization')
    runs=visible_runs(request.user).select_related('project','target')
    memberships=Membership.objects.none() if is_code(request.user) else Membership.objects.filter(user=request.user,active=True,organization__active=True).select_related('organization')
    stats={'projects':projects.count(),'requests':runs.exclude(operation='inventory').count(),
           'incomplete':runs.filter(state__in=['queued','claimed','starting','running','collecting','launch_uncertain','blocked']).count(),
           'approved_targets':visible_targets(request.user).filter(approved=True).count()}
    return render(request,'control/overview.html',{'projects':projects,'memberships':memberships,'recent_runs':runs[:8],'stats':stats,'page':'overview'})

@secure_account
@require_GET
def projects(request):return render(request,'control/projects.html',{'projects':visible_projects(request.user).select_related('organization'),'memberships':Membership.objects.none() if is_code(request.user) else Membership.objects.filter(user=request.user,active=True).select_related('organization'),'page':'projects'})

@secure_account
@require_GET
def target_list(request):return render(request,'control/target_list.html',{'targets':visible_targets(request.user).select_related('project'),'page':'targets'})

@secure_account
@require_GET
def run_history(request):
    runs=visible_runs(request.user).select_related('project','target','build')
    state=request.GET.get('state','')
    if state in {'queued','running','completed','launch_uncertain','rejected','blocked','cancelled'}:runs=runs.filter(state=state)
    service=request.GET.get('service','')
    if service in PROFILES:runs=runs.filter(profile=service)
    return render(request,'control/history.html',{'runs':runs[:100],'selected_state':state,'selected_service':service,'page':'runs','adapter_profiles':PROFILES})

@secure_account
@require_GET
def project(request,project_id):
    project,role=project_access(request.user,project_id)
    return render(request,'control/project.html',{'project':project,'role':role,'runs':visible_runs(request.user).filter(project=project)[:12],
        'targets':visible_targets(request.user).filter(project=project),'members':[] if is_code(request.user) else project.projectmembership_set.select_related('user'),
        'organization_members':Membership.objects.none() if is_code(request.user) else Membership.objects.filter(organization=project.organization,active=True,user__is_staff=True).select_related('user'),'page':'projects'})

@secure_account
@require_GET
def run_detail(request,run_id):
    run,role=authorized_run(request,run_id)
    cases=[];integrity_error=False
    if run.state in {'completed','blocked'} and run.operation!='inventory' and not run.purged_at:
        try:verify_inventory(run);cases=detail_cases(run)
        except (ValueError,OSError,PolicyError):integrity_error=True
    context={'run':run,'project':run.project,'role':role,'cases':cases,'integrity_error':integrity_error,
             'artifacts':Artifact.objects.filter(run=run).order_by('relative_path'),'analyses':visible_analyses(request.user).filter(run=run)[:5],'page':'runs'}
    return render(request,'control/run.html',context,status=409 if integrity_error else 200)

@secure_account
@require_GET
def compare(request):
    available=visible_runs(request.user).filter(state='completed',operation__in=['run','replay']).select_related('project')
    before=request.GET.get('before');after=request.GET.get('after');result=None;error=None;left=right=None
    if before and after:
        try:uuid.UUID(before);uuid.UUID(after)
        except ValueError:return render(request,'control/compare.html',{'runs':available[:100],'error':'before/after: expected valid run identifiers.','page':'compare'},status=400)
        left=get_object_or_404(available,pk=before);right=get_object_or_404(available,pk=after)
        if left.project_id!=right.project_id:error='Choose two runs from the same authorized project.'
        else:
            try:
                verify_inventory(left);verify_inventory(right);detail_cases(left);detail_cases(right)
                first=run_directory_fd(left);second=run_directory_fd(right)
                try:result=compare_executions(Path('/proc/self/fd')/str(first),Path('/proc/self/fd')/str(second))
                finally:os.close(first);os.close(second)
            except (ValueError,OSError,PolicyError):error='ERROR: evidence integrity or completeness prevents a comparison.'
    return render(request,'control/compare.html',{'runs':available[:100],'comparison':result,'before':left,'after':right,'error':error,'page':'compare'},status=409 if error else 200)

@require_GET
def demo(request,selection='before'):
    if selection=='partial':
        saved=json.loads((settings.REPO_ROOT/'docs/web/evidence/p3/recovery.json').read_text())
        case={'name':'timeout','result':saved['initial_summary']['cases'][0],'events':[],'sealed':False}
        return render(request,'control/demo.html',{'selection':selection,'case':case,'page':'demo','playback':True,'partial_snapshot':saved['initial_summary']})
    if selection not in PUBLIC_DEMOS:raise Http404
    base=settings.REPO_ROOT/'docs/evidence/phase10/executions'/PUBLIC_DEMOS[selection]
    bundle=inspect_bundle(base/'cases/timeout/bundle')
    events=[];first=None
    for index,line in enumerate(bundle.raw.splitlines()):
        event=json.loads(line)
        if event.get('kind')!='producer-event':continue
        ns=int(event['ns']);first=ns if first is None else first
        events.append({'index':index,'event':event['event'],'producer':event['producer'],'offset_ms':round((ns-first)/1000000,3),'data':event['data']})
    case={'name':'timeout','result':bundle.result.data,'events':events,'sealed':True,'plan':bundle.plan.data,'manifest':bundle.manifest.data,'target':json.loads(bundle.raw.splitlines()[0])}
    return render(request,'control/demo.html',{'selection':selection,'case':case,'page':'demo','playback':True})

@require_GET
def demo_file(request,selection,member):
    if selection not in PUBLIC_DEMOS or member not in {'observations.jsonl','bundle.json','result.json','plan.json','builds.json','status.json','profile.json','replay.json','target-manifest.json','notes.txt'}:raise Http404
    path=settings.REPO_ROOT/'docs/evidence/phase10/executions'/PUBLIC_DEMOS[selection]/'cases/timeout/bundle'
    inspect_bundle(path)
    response=FileResponse((path/member).open('rb'),as_attachment=True,filename=member,content_type='text/plain')
    response['Content-Security-Policy']="sandbox; default-src 'none'";return response

@require_GET
def public_page(request,section):
    if section not in {'how-it-works','docs','security','privacy','terms','contact'}:raise Http404
    return render(request,'control/public_page.html',{'section':section,'page':section})

@require_GET
def home(request):
    path=settings.REPO_ROOT/'docs/evidence/phase10/executions/p10demo2-broken/cases/timeout/bundle'
    bundle=inspect_bundle(path)
    return render(request,'control/home.html',{'recorded':bundle.result.data,'recorded_builds':bundle.plan.data['builds'],'page':'home'})

@secure_account
@require_GET
def report_file(request,run_id,member='report.html'):
    from pathlib import PurePosixPath
    run,role=authorized_run(request,run_id)
    permission(request.user,run.project_id,'download',target=run.target,run=run)
    parts=PurePosixPath(member)
    if parts.is_absolute() or '..' in parts.parts or '\\' in member or run.purged_at:raise Http404
    artifact=get_object_or_404(Artifact,run=run,relative_path=parts.as_posix())
    try:
        verify_inventory(run)
        detail_cases(run) # An intact report alone cannot vouch for damaged required raw evidence.
        stream=open_artifact(artifact)
    except (ValueError,OSError,PolicyError):return render(request,'control/message.html',{'title':'Evidence integrity error','message':'This artifact cannot be served because its identity or safe path no longer verifies.'},status=409)
    html=artifact.content_type=='text/html'
    response=FileResponse(stream,as_attachment=not html,filename=parts.name,content_type=artifact.content_type if html else 'text/plain')
    response['Content-Security-Policy']="sandbox allow-same-origin; default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'; form-action 'none'"
    response['X-Frame-Options']='SAMEORIGIN'
    audit(request.user,'evidence.viewed',run.project.organization,artifact.pk)
    return response
