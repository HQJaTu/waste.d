from django.urls import path, include, re_path

urlpatterns = ['',
               (r'api/', include('urlapi_urls')),
               (r'tag/(?P<tag>.*)/$', 'url_views.tag'),
               (r'view_m/(?P<urlid>.*)/$', 'url_views.view_master'),
               (r'view/(?P<urlid>.*)/$', 'url_views.view'),

               (r'channel/(?P<channel_filter>.*)/(?P<date>.*)/(?P<cursor>.*)$', 'url_views.index'),
               (r'channel/(?P<channel_filter>.*)/(?P<date>.*)/$', 'url_views.index'),
               (r'channel/(?P<channel_filter>.*)/(?P<cursor>.*)$', 'url_views.index'),
               (r'channel/(?P<channel_filter>.*)/$', 'url_views.view'),

               (r'(?P<date>.*)/(?P<cursor>.*)$', 'url_views.index'),
               (r'(?P<date>.*)/$', 'url_views.index'),
               (r'(?P<cursor>.*)$', 'url_views.index'),
               (r'', 'url_views.index'),
               ]
