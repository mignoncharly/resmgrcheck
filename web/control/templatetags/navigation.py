"""One permission-aware navigation model for desktop, mobile and breadcrumbs."""
from urllib.parse import urlencode
from django import template
from django.http import Http404
from django.urls import reverse
from resmgrcheck.registrations import PROFILES
from control.security import verified,is_code,project_access,organization_member,visible_runs,visible_analyses,visible_sources
register=template.Library()

PROJECT_ROUTES={'project','targets','target_request','inventory','import_build','new_run','project_member','runner_issue','runner_detail','runner_approve','runner_revoke','runner_approve_build','ai_settings','upload_source','source_detail'}
RUN_ROUTES={'run_detail','run_status','replay_run','cancel','report_file','evidence_download','ai_request','ai_detail','ai_cancel','retention_hold'}
TARGET_ROUTES={'targets','target_request','inventory','import_build','runner_issue','runner_detail','runner_approve','runner_revoke','runner_approve_build'}
ORG_ROUTES={'team','member_update','audit_log','retention','access_codes','code_detail','code_revoke','access_session_revoke','project_create'}
LABELS={'project':'Project overview','targets':'Targets & builds','target_request':'Request target','inventory':'Target inventory','import_build':'Import build','new_run':'New run','project_member':'Project permissions','runner_issue':'Runner enrollment','runner_detail':'Customer runner','runner_approve':'Runner approval','runner_revoke':'Runner revocation','runner_approve_build':'Build approval','ai_settings':'Project AI settings','upload_source':'Source review','source_detail':'Source excerpt','run_detail':'Test results','replay_run':'Replay run','ai_request':'Request analysis','ai_detail':'Analysis','team':'Team & permissions','audit_log':'Audit log','retention':'Evidence retention','access_codes':'Access codes','code_detail':'Access code','project_create':'Create project','organization_create':'Create organization','administrator_settings':'Administrator security','usersessions_list':'Browser sessions','account_change_password':'Change password','account_reauthenticate':'Confirm password','logout_all':'Revoke sessions','account_settings':'Access session','overview':'Dashboard','projects':'Projects','target_list':'Targets','run_history':'Test runs','compare':'Compare evidence','demo':'Recorded evidence','demo_case':'Recorded evidence','public_page':'Documentation'}

@register.simple_tag(takes_context=True)
def app_navigation(context):
    request=context['request'];user=request.user
    if not verified(user):return {'sections':[],'crumbs':[],'backs':[]}
    match=request.resolver_match;route=(match.url_name or '') if match else '';kw=match.kwargs if match else {}
    admin=not is_code(user)
    active='targets' if route in TARGET_ROUTES else 'projects' if route in PROJECT_ROUTES or route=='project_create' else 'runs' if route in RUN_ROUTES or route=='run_history' else 'targets' if route=='target_list' else 'compare' if route=='compare' else 'security' if route in ORG_ROUTES or route.startswith(('account_','mfa_')) or route in {'administrator_settings','usersessions_list','logout_all','organization_create'} else 'demo' if route in {'demo','demo_case'} else 'docs' if route=='public_page' else 'overview'
    def item(label,name,args=(),key=None,group='workspace',query=None):
        url=reverse(name,args=args)
        if query:url+='?'+urlencode(query)
        return {'label':label,'url':url,'key':key,'symbol':{'overview':'▦','projects':'◇','targets':'⌘','runs':'↗','compare':'⇄','demo':'▷','docs':'≡','security':'⚙'}.get(key,''),'group':group,'active':key==active}
    sections=[item(label,name,key=key) for label,name,key in [('Overview','overview','overview'),('Projects','projects','projects'),('Targets','target_list','targets'),('Test runs','run_history','runs'),('Compare','compare','compare')]]
    sections += [item('Recorded evidence','demo',key='demo',group='resources'),item('Documentation','public_page',['docs'],key='docs',group='resources'),item('Account & security','administrator_settings' if admin else 'account_settings',key='security',group='resources')]
    crumbs=[item('Dashboard','overview')];backs=[];project=None;run=None
    analysis=context.get('analysis')
    if analysis is None and kw.get('analysis_id'):analysis=visible_analyses(user).filter(pk=kw['analysis_id']).select_related('run__project').first()
    candidate=context.get('run') or context.get('original') or getattr(analysis,'run',None)
    if route=='compare' and context.get('before') and context.get('after') and context['before'].project_id==context['after'].project_id:candidate=context['before']
    if candidate is not None and visible_runs(user).filter(pk=candidate.pk).exists():run=candidate
    elif kw.get('run_id'):run=visible_runs(user).filter(pk=kw['run_id']).select_related('project').first()
    source=context.get('source')
    if source is None and kw.get('source_id'):
        from control.models import SourceSubmission
        row=SourceSubmission.objects.filter(pk=kw['source_id']).only('project_id').first()
        if row:
            try:source=visible_sources(user,row.project_id).filter(pk=row.pk).select_related('project').first()
            except Http404:pass
    candidate_project=context.get('project') or getattr(source,'project',None)
    identifier=getattr(candidate_project,'pk',None) or getattr(run,'project_id',None) or kw.get('project_id')
    if identifier:
        try:project,_=project_access(user,identifier)
        except Http404:pass
    if project:
        crumbs.append(item('Projects','projects'));crumbs.append(item(project.name,'project',[project.pk]))
        backs=[item('Back to Projects','projects')]
        if route!='project':backs.insert(0,item('Back to '+project.name,'project',[project.pk]))
        if route in {'runner_detail','runner_issue','runner_approve','runner_revoke','runner_approve_build','import_build','inventory','target_request'}:
            crumbs.append(item('Targets & builds','targets',[project.pk]));backs.insert(0,item('Back to project targets','targets',[project.pk]))
        if route in TARGET_ROUTES:backs.append(item('Back to all targets','target_list'))
        if route=='compare':backs.insert(0,item('Back to Compare','compare'))
        if run and route!='compare':
            query={'project':str(project.pk)}
            state=request.GET.get('history_state');service=request.GET.get('history_service')
            if state in {'queued','running','completed','launch_uncertain','rejected','blocked','cancelled'}:query['state']=state
            if service in PROFILES:query['service']=service
            backs.insert(0,item('Back to project runs','run_history',query=query))
            if route!='run_detail':crumbs.append(item('Test results','run_detail',[run.pk]));backs.insert(0,item('Back to test results','run_detail',[run.pk]))
    elif route in ORG_ROUTES:
        organization=context.get('organization') or getattr(context.get('code'),'organization',None)
        identifier=getattr(organization,'pk',None) or kw.get('organization_id')
        if identifier and admin:
            try:
                member=organization_member(user,identifier,'admin')
                crumbs.append(item('Account & security','administrator_settings'))
                crumbs.append({'label':member.organization.name})
                # Team is a real authorized organization-level parent.
                if route!='team':crumbs.append(item('Team & permissions','team',[identifier]))
                backs=[item('Back to team & permissions','team',[identifier])] if route!='team' else [item('Back to Projects','projects')]
                if route=='code_detail':crumbs.append(item('Access codes','access_codes',[identifier]));backs.insert(0,item('Back to access codes','access_codes',[identifier]))
            except Http404:pass
    elif active=='security' and route not in {'administrator_settings','account_settings'}:
        crumbs.append(item('Account & security','administrator_settings' if admin else 'account_settings'))
        backs=[item('Back to account & security','administrator_settings' if admin else 'account_settings')]
    elif route not in {'overview','projects','target_list','run_history','compare','administrator_settings','account_settings'}:
        parent=next((s for s in sections if s['key']==active),sections[0]);backs=[{'label':'Back to '+parent['label'],'url':parent['url']}]
    leaf=LABELS.get(route,context.get('title') or route.replace('_',' ').capitalize() or 'Page')
    if route=='project' and project:crumbs[-1].pop('url',None)
    elif route=='overview':crumbs=[{'label':'Dashboard'}]
    else:crumbs.append({'label':leaf})
    return {'sections':sections,'crumbs':crumbs,'backs':backs}
