import datetime

# XXX ToDo: google.appengine
#from google.appengine.ext.webapp import template
from django.http import HttpResponse
from django.shortcuts import render
#from google.appengine.api import taskqueue, users, memcache
import json
import logging

from waste_d.models.ndb.topic_models import Topic
from waste_d.models.ndb.models import News


def index(request):
    topics = Topic.query().order(-Topic.date)

    template_values = {
        'topics': topics,
    }
    return render(request, 'topic.html', template_values)


def post(request):
    # today=datetime.date.today()
    topic = None
    nick = None
    channel = None
    date = None

    retval = {}
    if request.method == "POST":
        logging.debug('raw_post_data %s' % (request.raw_post_data))
        try:
            data = json.loads(request.raw_post_data)
            logging.debug('data %s' % (data))
            topic = data.get('topic')
            channel = data.get('channel')
            nick = data.get('nick')
            date = datetime.datetime.strptime(data.get('date'), '%Y%m%d%H%M')
            logging.debug('date: %s, nick: %s, channel, %s, topic: %s' % (date, nick, channel, topic))
        except Exception as e:
            logging.warning('TOPIC/POST: Somewhere near %s' % (e))
            retval = {'id': 0, 'topic': e}
        else:
            try:
                t = Topic(channel=channel, nick=nick, topic=topic, date=date)
                t.put()
            except Exception as e:
                logging.warning('TOPIC/POST/NEW: Somewhere near %s' % (e))
                retval = {'id': 0, 'topic': e}
            else:
                retval = {'id': t.key.id(), 'topic': topic}
                # TODO private channel?
                # News(content='Topic: %s @ %s' % (topic,channel),link='/topic/').put()
                News(content='Topic', link_text='%s @ %s' % (topic, channel), link='/topic/').put()

    logging.debug('Return: %s' % (retval))

    return HttpResponse(json.dumps(retval), content_type="application/json")
