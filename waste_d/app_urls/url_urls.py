from django.urls import path, include, re_path
from waste_d.app_views import url_views
from .urlapi_urls import urlpatterns as urlapi_patterns

urlpatterns = [
    re_path(r'api/', include(urlapi_patterns)),
    re_path(r'tag/(?P<tag>.*)/$', url_views.tag),
    re_path(r'view_m/(?P<urlid>.*)/$', url_views.view_master),
    re_path(r'view/(?P<urlid>.*)/$', url_views.view),

    re_path(r'channel/(?P<channel_filter>.*)/(?P<date>.*)/(?P<cursor>.*)$', url_views.index),
    re_path(r'channel/(?P<channel_filter>.*)/(?P<date>.*)/$', url_views.index),
    re_path(r'channel/(?P<channel_filter>.*)/(?P<cursor>.*)$', url_views.index),
    re_path(r'channel/(?P<channel_filter>.*)/$', url_views.view),

    re_path(r'(?P<date>.*)/(?P<cursor>.*)$', url_views.index),
    re_path(r'(?P<date>.*)/$', url_views.index),
    re_path(r'(?P<cursor>.*)$', url_views.index),
    re_path(r'', url_views.index),
]
