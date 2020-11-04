from django.urls import path, include, re_path

urlpatterns = ['',
               (r'post/$', 'topic_views.post'),
               # (r'(?P<topicid>.*)/$','topic_views.index'),
               (r'', 'topic_views.index'),
               ]
