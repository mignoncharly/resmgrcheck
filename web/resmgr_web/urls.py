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
