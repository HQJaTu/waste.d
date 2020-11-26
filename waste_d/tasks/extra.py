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


class ExtraTask:

    @task(queue='default')
    def post(self):
        post_channel = self.request.get('post_channel', '')
        post_user = self.request.get('post_user', '')
        post_url = self.request.get('post_url', '')
        post_extra = self.request.get('extra', '')

        # Related/tag
        if post_extra.startwith('#'):
            # TODO: check
            if post_extra[1:].isdigit():
                type = 'related'
            else:
                type = 'tag'
        else:
            type = 'comment'

        url = Url.all().filter('url =', post_url).get()
        channel = Channel.all().filter('name =', post_channel).get()
        channelurl = ChannelUrl.all().filter('channel =', channel).filter('url =', url).get()

        if channelurl:
            extra = Extra()
            extra.channelurl = channelurl
            extra.user = post_user
            setattr(extra, type, post_extra)
            extra.put()
        else:
            log.warning('ChannelUrl not found: %s %s' % (post_channel, post_url))
