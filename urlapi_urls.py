
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'post/$','urlapi_views.post'),
    (r'info/$','urlapi_views.info'),
    (r'find/$','urlapi_views.find'),
    (r'rate/$','urlapi_views.rate'),
    (r'extra/$','urlapi_views.extra'),
    (r'','urlapi_views.index'),
)
