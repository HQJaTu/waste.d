import os
import sys
import string
import datetime
from lxml import etree
import re
import operator
import logging
from django_cloud_tasks.decorators import task
from django.utils.encoding import smart_text
from django.http import HttpResponseRedirect
from google.cloud import ndb

from waste_d.models import Url, Channel, ChannelUrl, Post, Rate, Extra, News

log = logging.getLogger(__name__)


class PostTask:

    def post(self):
        if users.get_current_user():
            node.author = users.get_current_user()

        post_channel = self.request.get('post_channel', '')
        post_user = self.request.get('post_user', '')
        post_url = self.request.get('post_url', '')

        # Add http:// when needed
        if not post_url.startswith('http'):
            post_url = 'http://' + post_url

        log.debug('Post: C=%s U=%s P=%s' % (post_channel, post_user, post_url))

        # 1. tarkista onko olemassa jo ko. Url, lisää jos ei, muuten päivitä (udate, valid?): valid-juttu joo ehkä jos tarpeen, ei muuten
        url = Url.all().filter('url =', post_url).get()
        if not url:
            url = Url()
            url.url = post_url
            url.put()

            # Title
            name = ''.join(re.findall('[a-zA-Z0-9_-]', post_channel + '_' + post_url))[:500]
            try:
                taskqueue.add(name=name, queue_name='urlfetch', url='/tasks/title', params={'post_url': post_url})
            except taskqueue.TombstonedTaskError:
                log.warning('TombstonedError %s' % post_url)
            except taskqueue.TaskAlreadyExistsError:
                log.warning('TaskAlredyExists: %s' % post_url)

        # 2. tarkista onko olemassa jo ko. Channel, lisää jos ei
        channel = Channel.all().filter('name =', post_channel).get()
        if not channel:
            channel = Channel()
            channel.name = post_channel
            if post_channel.startswith('!'):
                channel.private = True
            channel.put()

        # 3. tarkista onko url jo olemassa channel-tasolla
        channelurl = ChannelUrl.all().filter('url =', url).filter('channel =', channel).get()
        if not channelurl:
            channelurl = ChannelUrl()
            channelurl.channel = channel
            channelurl.url = url
            # channelurl.user=post_user
            channelurl.put()
        else:
            log.info('OLDIE! %s %s' % (channelurl.channel.name, channelurl.url.url))

        # 4. Lisätään postaus
        post = Post()
        post.channelurl = channelurl
        post.user = post_user
        post.put()

        # 5. extrat
