
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'post/$','topic_views.post'),
    #(r'(?P<topicid>.*)/$','topic_views.index'),
    (r'','topic_views.index'),
)
