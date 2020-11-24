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


class TitleTask:

    def get(self):
        id = self.request.get('id')
        if id:
            url = Url.get_by_id(int(id))
            if url:
                try:
                    prefix = self.request.get('prefix', '')
                    name = str(prefix) + str(id)
                    taskqueue.add(name=name, queue_name='urlfetch', url='/tasks/title', params={'id': id})
                except taskqueue.TombstonedTaskError:
                    log.warning('TombstonedTaskError %s' % id)
                except taskqueue.TaskAlreadyExistsError:
                    log.warning('TaskAlreadyExistsError %s' % id)
            else:
                log.info('No URL')
        else:
            log.info('No id')

        redirect = self.request.get('redirect')
        if redirect:
            return self.redirect(redirect)

    def post(self):
        id = self.request.get('id')
        if id:
            url = Url.get_by_id(int(id))
            if url:
                # TODO: fetch title
                # try:
                req = urllib2.Request(url.url)
                # logging.debug('req %s' % (req))
                # req.add_header('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
                req.add_header('User-agent', 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')
                req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                req.add_header('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.3')
                req.add_header('Accept-Encoding', 'none')
                req.add_header('Accept-Language', 'en-US,en;q=0.8')
                req.add_header('Connection', 'keep-alive')

                res = urllib2.urlopen(req)
                # logging.debug('res %s' % (res))
                doc = res.read()
                # logging.debug('doc %s' % (doc))
                encoding = res.headers.getparam('charset')
                log.debug('encoding %s' % (encoding))
                try:
                    tree = etree.fromstring(doc, etree.HTMLParser(encoding=encoding))
                except LookupError:
                    tree = etree.fromstring(doc, etree.HTMLParser(encoding='utf-8'))
                title = tree.find(".//title").text
                log.debug('title %s' % (title))
                url.title = smart_text(re.sub(r'\s+', ' ', title).strip())
                url.put()

