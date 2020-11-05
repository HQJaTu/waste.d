"""waste_d URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include, re_path

from .app_views import *
from .app_urls.sandbox_urls import urlpatterns as sandbox_patterns
from .app_urls.url_urls import urlpatterns as url_patterns
from .app_urls.rage_urls import urlpatterns as rage_patterns
from .app_urls.topic_urls import urlpatterns as topic_patterns

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
