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

QUEUE_DOCUMENT = 'document-d'


class DocumentTask:

    def get(self):
        doc_id = self.request.get('doc_id', '')
        if doc_id:
            try:
                prefix = self.request.get('prefix', '')
                name = str(prefix) + str(doc_id)
                taskqueue.add(name=name, queue_name='document', url='/tasks/update_document', params={'doc_id': doc_id})
            except taskqueue.TombstonedTaskError:
                log.warning('TombstonedTaskError %s' % (name))
            except taskqueue.TaskAlreadyExistsError:
                log.warning('TaskAlreadyExistsError %s' % (name))

        else:
            doc_ids = []
            url_keys = Url.query().order(Url.document_date).fetch(100, keys_only=True)

            for key in url_keys:
                doc_id = key.id()
                try:
                    prefix = self.request.get('prefix', '')
                    name = str(prefix) + str(doc_id)
                    taskqueue.add(name=str(doc_id), queue_name='document', url='/tasks/update_document',
                                  params={'doc_id': str(doc_id)})
                except taskqueue.TombstonedTaskError:
                    log.warning('TombstonedTaskError %s' % (str(name)))
                except taskqueue.TaskAlreadyExistsError:
                    log.warning('TaskAlreadyExistsError %s' % (str(name)))

    @classmethod
    @task(queue=QUEUE_DOCUMENT)
    def post(request, payload):
        doc_id = payload['doc_id']
        if not doc_id:
            log.error('No id')

            return

        # Document ID needs to be int
        doc_id = int(doc_id)

        # logging.debug('doc_id: %s' % (doc_id))
        urlinstance = Url.get_by_id(doc_id)

        if not urlinstance:
            log.debug('No urlinstance for doc_id: %s' % (doc_id))

        # If not valid url, delete from index
        if urlinstance.valid < 0:
            doc_index = search.Index(name='url')
            log.info('Delete invalid (%s) url (ID %s) from document index \'url\' (%s)' % (
                str(urlinstance.valid), doc_id, doc_index))
            doc_index.delete(doc_id)
        else:
            url = urlinstance.url
            title = urlinstance.title
            # logging.debug('url: %s, title: %s' % (url, title))

            channels = []
            channel = None
            users = []
            user = None
            date = datetime.datetime.fromtimestamp(0)

            comments = []
            comment = None
            tags = []
            tag = None

            rate = 0

            channelurlquery = ChannelUrl.query(ChannelUrl.url == urlinstance.key)
            for channelurlinstance in channelurlquery:
                channelinstance = channelurlinstance.channel.get()
                if channelinstance.name not in channels:
                    channels.append(channelinstance.name)
                    # logging.info('Adding channel %s' % (channelinstance.name))

                postquery = Post.query(Post.channelurl == channelurlinstance.key)
                for postinstance in postquery:
                    if postinstance.user not in users:
                        users.append(postinstance.user)
                    if date:
                        if date < postinstance.date:
                            date = postinstance.date
                    else:
                        date = postinstance.date

                extraquery = Extra.query(Extra.channelurl == channelurlinstance.key)
                for extrainstance in extraquery:
                    if extrainstance.tag:
                        if extrainstance.tag not in tags:
                            tags.append(extrainstance.tag)
                            # logging.info('Adding tag %s' % (extrainstance.tag))
                    if extrainstance.comment:
                        if extrainstance.comment not in comments:
                            comments.append(extrainstance.comment)
                            # logging.info('Adding comment %s' % (extrainstance.comment))

                ratequery = Rate.query(Rate.channelurl == channelurlinstance.key)
                for rateinstance in ratequery:
                    rate += rateinstance.value
                # logging.debug('rate %s' % (rate))

            if not date:
                date = datetime.datetime.fromtimestamp(0)
            # lists to strings
            channel = ' '.join(channels)
            user = ' '.join(users)
            tag = ' '.join(tags)
            if not tag:
                tag = None
            comment = ' '.join(comments)
            if not comment:
                comment = None

            log.debug('doc; channel=%s, user=%s, url=%s, date=%s, title=%s, comment=%s, tag=%s, rate=%s' % (
                channel, user, url, date, title, comment, tag, rate))
            return
            try:
                doc = search.Document(doc_id=str(doc_id), fields=[
                    search.TextField(name='channel', value=channel),
                    search.TextField(name='user', value=user),
                    search.TextField(name='url', value=url),
                    search.DateField(name='date', value=date),
                    search.TextField(name='title', value=title),
                    search.TextField(name='comment', value=comment, language='fi'),
                    search.TextField(name='tag', value=tag, language='fi'),
                    search.NumberField(name='rate', value=rate)
                ], language='en')
            except Exception as e:
                log.error('doc_id: %s, error %s' % (str(doc_id), e))
                doc = None

            try:
                if doc:
                    search.Index(name='url').put(doc)
                    urlinstance.document_date = datetime.datetime.now()
                    urlinstance.put()
                else:
                    log.error('Doc missing.')
            except search.Error:
                log.error('Create Document failed.')
