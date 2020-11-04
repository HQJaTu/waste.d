import datetime
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

from google.appengine.api import users
from google.appengine.ext import ndb
from models import Greeting, News

# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.
DEFAULT_GUESTBOOK_NAME = 'default_guestbook'


def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)


def index(request):
    if users.get_current_user():
        url = users.create_logout_url("/")
        url_linktext = 'Logout'
        username = users.get_current_user()
    else:
        url = users.create_login_url("/")
        url_linktext = 'Login'
        username = ''

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
        ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
    greetings = greetings_query.fetch(10)

    news = News.query().order(-News.date).fetch(5)

    template_values = {
        'url': url,
        'url_linktext': url_linktext,
        'username': username,
        'greetings': greetings,
        'guestbook_name': guestbook_name,
        'news': news,
    }
    return render_to_response('index.html', template_values)


def sign(request):
    # We set the same parent key on the 'Greeting' to ensure each greeting
    # is in the same entity group. Queries across the single entity group
    # will be consistent. However, the write rate to a single entity group
    # should be limited to ~1/second.
    guestbook_name = request.GET.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)

    greeting = Greeting(parent=guestbook_key(guestbook_name))

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
        return render_to_response('news_rss.html', template_values, mimetype="application/xml")
    else:
        return render_to_response('news.html', template_values)
