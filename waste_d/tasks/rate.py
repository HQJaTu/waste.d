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


class RateTask:

    def post(self):
        post_channel = self.request.get('post_channel', '')
        post_user = self.request.get('post_user', '')
        post_url = self.request.get('post_url', '')
        type = self.request.get('type', '')

        url = Url.all().filter('url =', post_url).get()
        channel = Channel.all().filter('name =', post_channel).get()
        channelurl = ChannelUrl.all().filter('channel =', channel).filter('url =', url).get()
        if channelurl:
            rate = Rate()
            rate.channelurl = channelurl
            rate.user = post_user
            rate.type = type
            rate.put()
        else:
            log.warning('ChannelUrl not found: %s %s' % (post_channel, post_url))
