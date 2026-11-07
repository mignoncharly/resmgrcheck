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
