from django.urls import path, include, re_path
from waste_d.app_views import urlapi_views

urlpatterns = [
    re_path(r'post/$', urlapi_views.post),
    re_path(r'info/$', urlapi_views.info),
    re_path(r'find/$', urlapi_views.find),
    re_path(r'rate/$', urlapi_views.rate),
    re_path(r'extra/$', urlapi_views.extra),
    #re_path(r'', urlapi_views.index),
]
