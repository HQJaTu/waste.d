from django.urls import path, include, re_path
from waste_d.views import topic_views

urlpatterns = [
    re_path(r'post/$', topic_views.post),
    # re_path(r'(?P<topicid>.*)/$', topic_views.index),
    re_path(r'', topic_views.index),
]
