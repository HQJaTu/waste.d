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


class ValidTask:

    def get(self):
        id = self.request.get('id')
        if id:
            url = Url.get_by_id(int(id))
            if url:
                try:
                    prefix = self.request.get('prefix', '')
                    name = str(prefix) + str(id)
                    taskqueue.add(name=name, queue_name='urlfetch', url='/tasks/valid', params={'id': id})
                except taskqueue.TombstonedTaskError:
                    log.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    log.warning('TaskAlreadyExistsError %s' % name)
        else:
            # Routine check
            url_keys = Url.query().order(Url.last_check, Url.status).fetch(50, keys_only=True)

            for key in url_keys:
                id = key.id()
                try:
                    prefix = self.request.get('prefix', '')
                    name = str(prefix) + str(id) + '_rc'
                    taskqueue.add(name=name, queue_name='urlfetch', url='/tasks/valid', params={'id': id})
                except taskqueue.TombstonedTaskError:
                    log.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    log.warning('TaskAlreadyExistsError %s' % name)

            # Fix <missing> fields: document_date, last_check (valid)
            url_keys = Url.query(Url.status == None).order(Url.idate).fetch(50, keys_only=True)

            for key in url_keys:
                id = key.id()
                try:
                    prefix = self.request.get('prefix', '')
                    name = str(prefix) + str(id) + '_fix'
                    taskqueue.add(name=name + '_dd', queue_name='document', url='/tasks/update_document',
                                  params={'doc_id': id})
                    taskqueue.add(name=name + '_lc', queue_name='urlfetch', url='/tasks/valid', params={'id': id})
                except taskqueue.TombstonedTaskError:
                    log.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    log.warning('TaskAlreadyExistsError %s' % name)

        redirect = self.request.get('redirect')
        if redirect:
            return self.redirect(redirect)

    def post(self):
        id = self.request.get('id')
        if id:
            url = Url.get_by_id(int(id))
            if url:
                result = None
                try:
                    result = urlfetch.fetch(url.url, allow_truncated=True)
                except urlfetch.DownloadError:
                    url.status = 'DE'
                    log.info('DownloadError, url: %s' % (url.url))
                except urlfetch.ResponseTooLargeError:
                    url.status = 'RTL'
                    log.info('ResponseTooLargeError, url: %s' % (url.url))
                except urlfetch.InvalidURLError:
                    url.status = 'IUE'
                    log.info('InvalidURLError, url: %s' % (url.url))
                except Exception:
                    url.status = 'UE'
                    log.error('"Unexpected error: %s, url: %s' % (sys.exc_info()[0], url.url))
                if result:
                    if result.content_was_truncated:
                        log.debug('truncated')
                    if result.status_code:
                        url.status = str(result.status_code)
                if result and result.status_code and result.status_code == 200:
                    url.valid = 2
                else:
                    if url.valid > -5:
                        url.valid = url.valid - 1
                    else:
                        log.info('Broken url: %s' % (url.url))
                url.last_check = datetime.datetime.now()
                url.put()
