import os
from django.http import HttpResponseRedirect
from django.shortcuts import render
import google.cloud.logging
import google.auth.transport.requests
import google.oauth2.id_token
from google.cloud import ndb
from waste_d.models.ndb.models import Greeting, News
from waste_d.models.ndb.url_models import Url, ChannelUrl, Extra

HTTP_REQUEST = google.auth.transport.requests.Request()

# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.
DEFAULT_GUESTBOOK_NAME = 'default_guestbook'


def index(request):
    if 'Authorization' in request.headers:
        id_token = request.headers['Authorization'].split(' ').pop()
        claims = google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST, audience=os.environ.get('GOOGLE_CLOUD_PROJECT'))
    else:
        claims = None

    if not claims:
        # url = users.create_login_url("/")
        url_linktext = 'Login'
        username = ''
    else:
        # url = users.create_logout_url("/")
        url_linktext = 'Logout'
        username = claims.get('email', 'Unknown')

    # if 'guestbook_name' in request.GET:
    guestbook_name = request.GET.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)
    # else:
    #  guestbook_name=DEFAULT_GUESTBOOK_NAME

    # Ancestor Queries, as shown here, are strongly consistent with the High
    # Replication Datastore. Queries that span entity groups are eventually
    # consistent. If we omitted the ancestor from this query there would be
    # a slight chance that Greeting that had just been written would not
    # show up in a query.
    greetings_query = Greeting.query(
        ancestor=_guestbook_key(guestbook_name)
    ).order(-Greeting.date)
    greetings = greetings_query.fetch(10)

    last_5_news_db = News.query().order(-News.date).fetch(5)
    last_5_news = []
    for piece_of_news in last_5_news_db:
        news = _format_news(piece_of_news)
        last_5_news.append(news)

    template_values = {
        'url': '',
        'url_linktext': url_linktext,
        'username': username,
        'greetings': greetings,
        'guestbook_name': guestbook_name,
        'news': last_5_news,
    }

    return render(request, 'index.html', template_values)


def _format_news(news_db):
    content = news_db.content
    link = news_db.link
    if news_db.link_text:
        link_text = news_db.link_text
    else:
        link_text = None
        url = Url.query(Url.url == news_db.link).get(keys_only=True)
        channel_url = ChannelUrl.query(ChannelUrl.url == url).get(keys_only=True)
        extra = Extra.query(Extra.channelurl == channel_url).get(keys_only=False)
        if extra and extra.comment:
            link_text = extra.comment
        if not link_text:
            link_text = ''.join(news_db.link.split('/')[-1:])

    news = '%s: <a target="_blank" href="%s">%s</a>' % (content, link, link_text)

    return news


def _guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)


def sign(request):
    # We set the same parent key on the 'Greeting' to ensure each greeting
    # is in the same entity group. Queries across the single entity group
    # will be consistent. However, the write rate to a single entity group
    # should be limited to ~1/second.
    guestbook_name = request.GET.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)

    greeting = Greeting(parent=_guestbook_key(guestbook_name))

    if users.get_current_user():
        greeting.author = users.get_current_user()

    greeting.content = request.POST.get('content')
    greeting.put()

    # query_params = {'guestbook_name': guestbook_name}
    # self.redirect('/?' + urllib.urlencode(query_params))
    return HttpResponseRedirect('/')


def news(request, rss=None):
    news = News.query().order(-News.date).fetch(25)

    template_values = {
        'news': news,
    }
    if rss:
        return render('news_rss.html', template_values, content_type="application/xml")
    else:
        return render('news.html', template_values)
