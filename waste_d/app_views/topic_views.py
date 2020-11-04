import cgi
import os, sys
import datetime
import re
import random

from google.appengine.ext.webapp import template
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import logging
from google.appengine.api import taskqueue, users, memcache
from django.utils.encoding import smart_unicode
from django.utils import simplejson

from topic_models import Topic
from models import News


def index(request):
    topics = Topic.query().order(-Topic.date)

    template_values = {
        'topics': topics,
    }
    return render('topic.html', template_values)


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
            data = simplejson.loads(request.raw_post_data)
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
    return HttpResponse(simplejson.dumps(retval), mimetype="application/json")
