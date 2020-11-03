from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^sandbox/',include('sandbox_urls')),
    (r'^url/',include('url_urls')),
    (r'^rage/',include('rage_urls')),
    (r'^topic/',include('topic_urls')),
    (r'^sign.*$', 'views.sign'),
    (r'^news/(?P<rss>.*).*$', 'views.news'),
    (r'^news.*$', 'views.news'),
    (r'^.*$', 'views.index'),

)
