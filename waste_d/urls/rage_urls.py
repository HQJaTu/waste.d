from django.urls import path, include, re_path
from waste_d.views.rage_views import *

urlpatterns = [
    re_path(r'post/$', post),
    re_path(r'(?P<rageid>.*)/$', index),
    re_path(r'', index),
]
