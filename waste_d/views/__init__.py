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


from django.conf import settings
from django.urls import path, include, re_path
from django.db import connections
from django.db.utils import ProgrammingError
import logging
import re

from .views import *
from waste_d.urls.sandbox_urls import urlpatterns as sandbox_patterns
from waste_d.urls.url_urls import urlpatterns as url_patterns
from waste_d.urls.rage_urls import urlpatterns as rage_patterns
from waste_d.urls.topic_urls import urlpatterns as topic_patterns

log = logging.getLogger(__name__)

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


# Quick database check here
dbs = settings.DATABASES.keys()
for db in dbs:
    db_conn = connections[db]  # i.e. default
    try:
        c = db_conn.cursor()
        c.execute('select Db from mysql.db LIMIT 1')
        c.fetchone()
        log.info("Database '%s' connection ok." % db)  # This case is for djongo decoding sql ok
    except ProgrammingError as e:
        match = re.search("^Table '.+' doesn't exist", e.args[1])
        if match:
            log.info("Database '%s' connection ok." % db)  # This is ok, db is present
        else:
            log.error("ERROR: Database '%s' looks to be down. Exception: %s" % (db, e))
            raise  # Another type of op error
    except Exception as e:  # djongo sql decode error
        log.error("ERROR: Database '%s' looks to be down. Exception: %s" % (db, e))
        raise
