from django.urls import path, include, re_path
from waste_d.app_views import urlapi_views

urlpatterns = [
    re_path(r'post/$', urlapi_views.API.as_view()),
    re_path(r'info/$', urlapi_views.API.as_view()),
    re_path(r'find/$', urlapi_views.API.as_view()),
    re_path(r'rate/$', urlapi_views.API.as_view()),
    re_path(r'extra/$', urlapi_views.API.as_view()),
]
