from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'post/$', 'rage_views.post'),
                       (r'(?P<rageid>.*)/$', 'rage_views.index'),
                       (r'', 'rage_views.index'),
                       )
