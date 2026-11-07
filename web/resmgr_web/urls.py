from django.urls import include, path
from control import views
urlpatterns = [path('healthz/',views.health,name='health'),path('readyz/',views.readiness,name='readiness'),
               path('accounts/',include('allauth.urls')),path('',views.home,name='home')]
