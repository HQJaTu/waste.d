from django.urls import path, include, re_path

from waste_d.views import *
from . import sandbox_urls
from . import rage_urls
from . import topic_urls
from . import url_urls
# Not exported:
#from . import urlapi_urls

urlpatterns = [
    # As generated in template:
    #path('admin/', admin.site.urls),
    path('', views.index),
    re_path(r'sandbox/', include(sandbox_patterns)),
    re_path(r'^url/', include(url_patterns)),
    re_path(r'^rage/', include(rage_patterns)),
    re_path(r'^topic/', include(topic_patterns)),
    re_path(r'^sign.*$', views.sign),
    re_path(r'^news/(?P<rss>.*).*$', views.news),
    re_path(r'^news.*$', views.news),
    re_path(r'^.*$', views.index),
]