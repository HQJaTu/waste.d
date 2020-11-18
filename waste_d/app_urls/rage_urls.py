from django.urls import path, include, re_path
from waste_d.views import rage_views

urlpatterns = [
    re_path(r'post/$', rage_views.post),
    re_path(r'(?P<rageid>.*)/$', rage_views.index),
    re_path(r'', rage_views.index),
]
