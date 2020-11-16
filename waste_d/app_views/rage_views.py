import cgi
import os, sys
import datetime
import re
import json
import random

# XXX ToDo: google.appengine
#from google.appengine.ext.webapp import template
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import google.cloud.logging
#from google.appengine.api import taskqueue, users, memcache

from waste_d.models.rage_models import Rage, Panel
from waste_d.models.models import News


def index(request, rageid=0):
    rages = Rage.query().order(-Rage.idate)

    # Rage NOT selected, show the first one (if available)
    if not rageid:
        ragequery = rages.get()
        if ragequery:
            rage = ragequery.key
            rageid = rage.id()
            title = ragequery.title
            date = ragequery.date
        else:
            rage = None
            title = 'Main page'
    # Show selected Rage
    else:
        ragequery = Rage.get_by_id(int(rageid))
        if not ragequery:
            ragequery = rages.get()
        rage = ragequery.key
        title = ragequery.title
        date = ragequery.date

    # Show comic/panels
    if rage:
        panels = Panel.query(Panel.rage == rage).order(Panel.count)
    else:
        panels = []

    if ragequery:
        channel = ragequery.channel
    else:
        channel = 'Rage'

    template_values = {
        'rages': rages,
        'panels': panels,
        'title': title,
        'channel': channel,
        'date': date,
        'active': int(rageid),
    }
    return render('rage.html', template_values)


def post(request):
    today = datetime.date.today()
    retval = {}

    error = 10

    channel = None
    title = None
    lines = []

    for key in request.POST:
        error = 0
        data = json.loads(key)
        logging.debug('Data: %s' % (str(data)))

        # Parse and check data
        if 'channel' in data:
            channel = data['channel']
        else:
            error += 1
        if 'title' in data:
            title = data['title']
        else:
            title = today
        if 'date' in data:
            date = datetime.datetime.strptime(data['date'], '%y%m%d%H%M%S')
        else:
            date = today
        if 'lines' in data:
            lines = data['lines']
        else:
            error += 2

    if not error:
        prevnick = ''
        rage = Rage(channel=channel, title=title, date=date)
        rage.put()
        i = 1
        for line in lines:
            # logging.debug('Line: %s, nick: %s, msg: %s' % (line,line['nick'],line['msg']))
            nick = line['nick']

            # HTML safe
            msg = cgi.escape(line['msg'])

            if msg.endswith(':)'):
                faces = ['smile', 'happy', 'hehehe']
            elif msg.endswith(':('):
                faces = ['unhappy', 'herp']
            elif msg.endswith(';)'):
                faces = ['pfftch']
            elif msg.endswith(':D'):
                faces = ['epicwin', 'grin']
            elif msg.endswith('!'):
                faces = ['loool']
            elif msg.endswith('.'):
                faces = ['monocole']
            else:
                faces = ['beh', 'dude-come-on', 'epicwin', 'french', 'grin', 'happy', 'hehehe', 'herp', 'horror',
                         'loool', 'monocole', 'pfftch', 'rage', 'redeyes', 'smile', 'suspicious', 'unhappy', 'wait',
                         'concentrated', 'kittehsmile']
            face = faces[random.randint(0, (len(faces)) - 1)]
            # logging.debug('Face: %s' % (face))

            if nick != prevnick:
                panel = Panel(rage=rage.key, count=i, nick=nick, face=face, msg=msg)
                panel.put()
                i += 1
            else:
                panel.face = face
                panel.msg = panel.msg + '<br /><b>&nbsp;&nbsp;&nbsp;|</b><br />' + msg
                panel.put()

            prevnick = nick
        retval = {'id': rage.key.id(), 'title': title}
        News(content='<a href="/rage/%s/">%s</a>' % (rage.key.id(), title)).put()
    else:
        retval = {'id': 0, 'title': 'error: %s' % (error)}

    logging.debug('Return: %s' % (retval))

    return HttpResponse(json.dumps(retval), content_type="application/json")
