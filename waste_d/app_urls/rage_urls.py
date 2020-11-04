from django.urls import path, include, re_path

urlpatterns = ['',
               (r'post/$', 'rage_views.post'),
               (r'(?P<rageid>.*)/$', 'rage_views.index'),
               (r'', 'rage_views.index'),
               ]
