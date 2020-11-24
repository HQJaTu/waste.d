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


class MaintenanceTask:

    @task(queue='default')
    def post(self):
        type = self.request.get('type', '')
        if type == 'stats':
            pass
        elif type == 'cleanup':
            last_year = datetime.datetime.now() - datetime.timedelta(days=365)
            last_quarter = datetime.datetime.now() - datetime.timedelta(days=92)
            last_month = datetime.datetime.now() - datetime.timedelta(days=31)
            # Old news
            old_news = News.query(News.date < last_quarter).order(News.date).fetch(500, keys_only=True)
            # logging.info('Cleaning up old news %s' % News.query().order(News.date).count(100,keys_only=True))
            ndb.delete_multi(old_news)


        elif type == 'tag_cloud':
            channel_urls = []
            tags = {}
            extras = Extra.query(Extra.tag != None)
            for extra in extras:
                if extra.channelurl not in channel_urls:
                    channel_urls.append(extra.channelurl)
                    tag = extra.tag
                    if tag in tags:
                        tags[tag] += 1
                    else:
                        tags[tag] = 1
            tags_sorted = sorted(tags.iteritems(), key=operator.itemgetter(1), reverse=True)
            memcache.set("tag_cloud", tags_sorted)
            log.debug('Tags: %s' % (tags_sorted))
        elif type == 'fix':
            test_channel = '#kanava'
            channel = Channel.query(Channel.name == test_channel).get()
            channelurls = ChannelUrl.query(ChannelUrl.channel == channel.key).fetch(50)
            for channelurl in channelurls:
                url = channelurl.url.get()
                log.debug('Channel: %s, channelurl: %s (id %s)' % (test_channel, url, channelurl))

                posts = Post.query(Post.channelurl == channelurl.key)
                for post in posts:
                    log.debug(' * posted by %s' % (post.user))
                    post.key.delete()

                rates = Rate.query(Rate.channelurl == channelurl.key)
                for rate in rates:
                    log.debug(' *  rate %s' % (rate))
                    rate.key.delete()

                extras = Extra.query(Extra.channelurl == channelurl.key)
                for extra in extras:
                    log.debug(' *  extra %s, by %s' % (extra, extra.user))
                    extra.key.delete()

                channelurl.key.delete()

    def get(self):
        type = self.request.get('type')
        log.debug('Maintenance task, %s' % (type))
        if type == 'stats':
            taskqueue.add(queue_name='default', url='/tasks/maintenance', params={'type': 'stats'})
        elif type == 'tag_cloud':
            taskqueue.add(queue_name='default', url='/tasks/maintenance', params={'type': 'tag_cloud'})
        elif type == 'fix':
            taskqueue.add(queue_name='default', url='/tasks/maintenance', params={'type': 'fix'})
        elif type == 'cleanup':
            taskqueue.add(queue_name='maintenance', url='/tasks/maintenance', params={'type': 'cleanup'})
        elif type == 'url_test_clean':
            channel = self.request.get('channel')
            nick = self.request.get('nick')
            log.debug('url_test_clean, channel: %s, nick: %s' % (channel, nick))
