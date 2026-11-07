from django.urls import include,path
from control import views
urlpatterns=[path('healthz/',views.health,name='health'),path('readyz/',views.readiness,name='readiness'),
 path('accounts/',include('allauth.urls')),path('',views.home,name='home'),path('app/',views.overview,name='overview'),
 path('app/organizations/new/',views.organization_create,name='organization_create'),
 path('app/organizations/<uuid:organization_id>/projects/new/',views.project_create,name='project_create'),
 path('app/projects/<uuid:project_id>/',views.project_detail,name='project'),
 path('api/projects/<uuid:project_id>/',views.project_api,name='project_api'),
 path('app/organizations/<uuid:organization_id>/team/',views.team,name='team'),
 path('app/organizations/<uuid:organization_id>/invitations/',views.invite,name='invite'),
 path('app/invitations/<str:token>/',views.accept_invitation,name='accept_invitation'),
 path('app/organizations/<uuid:organization_id>/members/<uuid:user_id>/',views.member_update,name='member_update'),
 path('app/projects/<uuid:project_id>/members/',views.project_member,name='project_member'),
 path('app/organizations/<uuid:organization_id>/audit/',views.audit_log,name='audit_log'),
 path('app/account/',views.account_settings,name='account_settings'),path('app/account/export/',views.account_export,name='account_export'),
 path('app/account/logout-all/',views.logout_all,name='logout_all'),path('app/account/delete/',views.account_delete,name='account_delete')]
from control import execution_views as execution
urlpatterns += [path('app/projects/<uuid:project_id>/targets/',execution.targets,name='targets'),
 path('app/projects/<uuid:project_id>/targets/request/',execution.target_request,name='target_request'),
 path('app/projects/<uuid:project_id>/targets/<uuid:target_id>/inventory/',execution.inventory,name='inventory'),
 path('app/projects/<uuid:project_id>/targets/<uuid:target_id>/builds/import/',execution.import_build,name='import_build'),
 path('app/projects/<uuid:project_id>/runs/new/',execution.new_run,name='new_run'),
 path('app/runs/<uuid:run_id>/',execution.run_detail,name='run_detail'),path('api/runs/<uuid:run_id>/',execution.run_status,name='run_status'),
 path('app/runs/<uuid:run_id>/cancel/',execution.cancel,name='cancel'),path('app/runs/<uuid:run_id>/replay/',execution.replay_run,name='replay_run')]
from control import dashboard
# Existing path names remain stable; route implementations now render verified detail.
urlpatterns=[p for p in urlpatterns if getattr(p,'name',None) not in {'home','overview','project','run_detail'}]
urlpatterns += [path('',dashboard.home,name='home'),path('app/',dashboard.overview,name='overview'),
 path('app/projects/',dashboard.projects,name='projects'),path('app/targets/',dashboard.target_list,name='target_list'),
 path('app/runs/',dashboard.run_history,name='run_history'),path('app/compare/',dashboard.compare,name='compare'),
 path('app/projects/<uuid:project_id>/',dashboard.project,name='project'),path('app/runs/<uuid:run_id>/',dashboard.run_detail,name='run_detail'),
 path('demo/',dashboard.demo,name='demo'),path('demo/<str:selection>/',dashboard.demo,name='demo_case'),
 path('demo/<str:selection>/evidence/<str:member>/',dashboard.demo_file,name='demo_file'),path('about/<str:section>/',dashboard.public_page,name='public_page')]
from django.conf import settings
if settings.ENVIRONMENT=='staging':
 from django.views.static import serve
 urlpatterns += [path('static/<path:path>',serve,{'document_root':settings.STATIC_ROOT})]
urlpatterns += [path('app/runs/<uuid:run_id>/report/<path:member>',dashboard.report_file,name='report_file')]
