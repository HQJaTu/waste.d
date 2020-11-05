# waste.d
Google Appengine UrlLogger etc. service

## Local development

### Run
```bash
./manage.py runserver
```

Server is at http://127.0.0.1:8000/

### List of all known URLs
Run:
```bash
./manage.py show_urls
```

Output:
```bash
/                       waste_d.app_views.views.index
/.*                     waste_d.app_views.views.index
/news.*                 waste_d.app_views.views.news
/news/<rss>.*           waste_d.app_views.views.news
/rage/                  waste_d.app_views.rage_views.index
/rage/<rageid>/         waste_d.app_views.rage_views.index
/rage/post/             waste_d.app_views.rage_views.post
/sign.*                 waste_d.app_views.views.sign
/topic/                 waste_d.app_views.topic_views.index
/topic/post/            waste_d.app_views.topic_views.post
/url/                   waste_d.app_views.url_views.index
/url/<cursor>           waste_d.app_views.url_views.index
/url/<date>/            waste_d.app_views.url_views.index
/url/<date>/<cursor>    waste_d.app_views.url_views.index
/url/api/extra/         waste_d.app_views.urlapi_views.extra
/url/api/find/          waste_d.app_views.urlapi_views.find
/url/api/info/          waste_d.app_views.urlapi_views.info
/url/api/post/          waste_d.app_views.urlapi_views.post
/url/api/rate/          waste_d.app_views.urlapi_views.rate
/url/channel/<channel_filter>/                  waste_d.app_views.url_views.view
/url/channel/<channel_filter>/<cursor>          waste_d.app_views.url_views.index
/url/channel/<channel_filter>/<date>/           waste_d.app_views.url_views.index
/url/channel/<channel_filter>/<date>/<cursor>   waste_d.app_views.url_views.index
/url/tag/<tag>/         waste_d.app_views.url_views.tag
/url/view/<urlid>/      waste_d.app_views.url_views.view
/url/view_m/<urlid>/    waste_d.app_views.url_views.view_master
```
