from django.urls import include,path
from django.conf import settings
from allauth.account import views as account
from control.security import administrator
from control import views,dashboard,execution_views as execution,evidence,retention_views,ai_views,access_views,runner_views
urlpatterns=[
 path('runner/v1/<str:operation>/',runner_views.machine,name='runner_machine'),
 path('app/projects/<uuid:project_id>/runners/enroll/',runner_views.issue,name='runner_issue'),
 path('app/projects/<uuid:project_id>/runners/<uuid:target_id>/',runner_views.detail,name='runner_detail'),
 path('app/projects/<uuid:project_id>/runners/<uuid:target_id>/approve/',runner_views.approval,name='runner_approve'),
 path('app/projects/<uuid:project_id>/runners/<uuid:target_id>/revoke/',runner_views.revocation,name='runner_revoke'),
 path('healthz/',views.health,name='health'),path('readyz/',views.readiness,name='readiness'),
 path('administrator/login/',account.LoginView.as_view(template_name='control/administrator_login.html'),name='account_login'),
 path('administrator/reauthenticate/',account.ReauthenticateView.as_view(),name='account_reauthenticate'),
 path('administrator/password/change/',administrator(account.PasswordChangeView.as_view(template_name='control/administrator_password.html')),name='account_change_password'),
 path('administrator/2fa/',include('allauth.mfa.urls')),
 path('administrator/sessions/',views.administrator_sessions,name='usersessions_list'),
 path('access/',access_views.developer_access,name='developer_access'),path('sign-out/',access_views.sign_out,name='account_logout'),
 path('app/session/',access_views.session_settings,name='account_settings'),
 path('administrator/settings/',views.account_settings,name='administrator_settings'),path('administrator/logout-all/',views.logout_all,name='logout_all'),
 path('',dashboard.home,name='home'),path('app/',dashboard.overview,name='overview'),
 path('app/projects/',dashboard.projects,name='projects'),path('app/targets/',dashboard.target_list,name='target_list'),
 path('app/runs/',dashboard.run_history,name='run_history'),path('app/compare/',dashboard.compare,name='compare'),
 path('app/organizations/new/',views.organization_create,name='organization_create'),
 path('app/organizations/<uuid:organization_id>/projects/new/',views.project_create,name='project_create'),
 path('app/projects/<uuid:project_id>/',dashboard.project,name='project'),path('api/projects/<uuid:project_id>/',views.project_api,name='project_api'),
 path('app/organizations/<uuid:organization_id>/team/',views.team,name='team'),
 path('app/organizations/<uuid:organization_id>/members/<uuid:user_id>/',views.member_update,name='member_update'),
 path('app/projects/<uuid:project_id>/members/',views.project_member,name='project_member'),
 path('app/organizations/<uuid:organization_id>/audit/',views.audit_log,name='audit_log'),
 path('administrator/organizations/<uuid:organization_id>/codes/',access_views.codes,name='access_codes'),
 path('administrator/codes/<uuid:code_id>/',access_views.code_detail,name='code_detail'),
 path('administrator/codes/<uuid:code_id>/revoke/',access_views.revoke,name='code_revoke'),
 path('administrator/access-sessions/<uuid:session_id>/revoke/',access_views.revoke_session,name='access_session_revoke'),
 path('app/projects/<uuid:project_id>/targets/',execution.targets,name='targets'),
 path('app/projects/<uuid:project_id>/targets/request/',execution.target_request,name='target_request'),
 path('app/projects/<uuid:project_id>/targets/<uuid:target_id>/inventory/',execution.inventory,name='inventory'),
 path('app/projects/<uuid:project_id>/targets/<uuid:target_id>/builds/import/',execution.import_build,name='import_build'),
 path('app/projects/<uuid:project_id>/runs/new/',execution.new_run,name='new_run'),
 path('app/runs/<uuid:run_id>/',dashboard.run_detail,name='run_detail'),path('api/runs/<uuid:run_id>/',execution.run_status,name='run_status'),
 path('app/runs/<uuid:run_id>/cancel/',execution.cancel,name='cancel'),path('app/runs/<uuid:run_id>/replay/',execution.replay_run,name='replay_run'),
 path('app/runs/<uuid:run_id>/report/<path:member>',dashboard.report_file,name='report_file'),
 path('app/runs/<uuid:run_id>/evidence.zip',evidence.download,name='evidence_download'),
 path('app/organizations/<uuid:organization_id>/retention/',retention_views.settings_page,name='retention'),path('app/runs/<uuid:run_id>/retention-hold/',retention_views.hold,name='retention_hold'),
 path('app/projects/<uuid:project_id>/ai/settings/',ai_views.settings_page,name='ai_settings'),
 path('app/projects/<uuid:project_id>/ai/source/',ai_views.upload_source,name='upload_source'),path('app/source/<uuid:source_id>/',ai_views.source_detail,name='source_detail'),
 path('app/runs/<uuid:run_id>/ai/',ai_views.request_analysis,name='ai_request'),path('app/analysis/<uuid:analysis_id>/',ai_views.detail,name='ai_detail'),
 path('app/analysis/<uuid:analysis_id>/cancel/',ai_views.cancel_analysis,name='ai_cancel'),
 path('demo/',dashboard.demo,name='demo'),path('demo/<str:selection>/',dashboard.demo,name='demo_case'),
 path('demo/<str:selection>/evidence/<str:member>/',dashboard.demo_file,name='demo_file'),path('about/<str:section>/',dashboard.public_page,name='public_page')]
if settings.ENVIRONMENT=='staging':
 from django.views.static import serve
 urlpatterns += [path('static/<path:path>',serve,{'document_root':settings.STATIC_ROOT})]
