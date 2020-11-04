# -*- coding: utf-8 -*-
import os
import sys
import string
import logging
import datetime
import urllib2
from lxml import etree
import re
import operator

from django.utils.encoding import smart_unicode
from django.http import HttpResponseRedirect
from google.appengine.ext import ndb

from google.appengine.api import urlfetch, taskqueue, memcache, mail
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users, search
from url_models import Url, Channel, ChannelUrl, Post, Rate, Extra
from models import News


class MaintenanceTask(webapp.RequestHandler):
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
            logging.debug('Tags: %s' % (tags_sorted))
        elif type == 'fix':
            test_channel = '#kanava'
            channel = Channel.query(Channel.name == test_channel).get()
            channelurls = ChannelUrl.query(ChannelUrl.channel == channel.key).fetch(50)
            for channelurl in channelurls:
                url = channelurl.url.get()
                logging.debug('Channel: %s, channelurl: %s (id %s)' % (test_channel, url, channelurl))

                posts = Post.query(Post.channelurl == channelurl.key)
                for post in posts:
                    logging.debug(' * posted by %s' % (post.user))
                    post.key.delete()

                rates = Rate.query(Rate.channelurl == channelurl.key)
                for rate in rates:
                    logging.debug(' *  rate %s' % (rate))
                    rate.key.delete()

                extras = Extra.query(Extra.channelurl == channelurl.key)
                for extra in extras:
                    logging.debug(' *  extra %s, by %s' % (extra, extra.user))
                    extra.key.delete()

                channelurl.key.delete()

    def get(self):
        type = self.request.get('type')
        logging.debug('Maintenance task, %s' % (type))
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
            logging.debug('url_test_clean, channel: %s, nick: %s' % (channel, nick))


class PostTask(webapp.RequestHandler):
    # def get(self):
    #  taskqueue.add(name='',queue_name='',url='', params={})

    def post(self):
        if users.get_current_user():
            node.author = users.get_current_user()

        post_channel = self.request.get('post_channel', '')
        post_user = self.request.get('post_user', '')
        post_url = self.request.get('post_url', '')

        # Add http:// when needed
        if not post_url.startswith('http'):
            post_url = 'http://' + post_url

        logging.debug('Post: C=%s U=%s P=%s' % (post_channel, post_user, post_url))

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
                logging.warning('TombstonedError %s' % post_url)
            except taskqueue.TaskAlreadyExistsError:
                logging.warning('TaskAlredyExists: %s' % post_url)

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
            logging.info('OLDIE! %s %s' % (channelurl.channel.name, channelurl.url.url))

        # 4. Lisätään postaus
        post = Post()
        post.channelurl = channelurl
        post.user = post_user
        post.put()

        # 5. extrat


class RateTask(webapp.RequestHandler):
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
            logging.warning('ChannelUrl not found: %s %s' % (post_channel, post_url))


class ExtraTask(webapp.RequestHandler):
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
            logging.warning('ChannelUrl not found: %s %s' % (post_channel, post_url))


class TitleTask(webapp.RequestHandler):
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
                    logging.warning('TombstonedTaskError %s' % id)
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s' % id)
            else:
                logging.info('No URL')
        else:
            logging.info('No id')

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
                logging.debug('encoding %s' % (encoding))
                try:
                    tree = etree.fromstring(doc, etree.HTMLParser(encoding=encoding))
                except LookupError:
                    tree = etree.fromstring(doc, etree.HTMLParser(encoding='utf-8'))
                title = tree.find(".//title").text
                logging.debug('title %s' % (title))
                url.title = smart_unicode(re.sub(r'\s+', ' ', title).strip())
                # except:
                #  logging.debug('TitleTask: title not fetched %s' % (post_url))
                # url.title = post_url
                url.put()
                # name=''.join(re.findall('[a-zA-Z0-9_-]',post_url))[:500]


class ValidTask(webapp.RequestHandler):
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
                    logging.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s' % name)
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
                    logging.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s' % name)

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
                    logging.warning('TombstonedTaskError %s' % name)
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s' % name)

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
                    logging.info('DownloadError, url: %s' % (url.url))
                except urlfetch.ResponseTooLargeError:
                    url.status = 'RTL'
                    logging.info('ResponseTooLargeError, url: %s' % (url.url))
                except urlfetch.InvalidURLError:
                    url.status = 'IUE'
                    logging.info('InvalidURLError, url: %s' % (url.url))
                except:
                    url.status = 'UE'
                    logging.error('"Unexpected error: %s, url: %s' % (sys.exc_info()[0], url.url))
                if result:
                    if result.content_was_truncated:
                        logging.debug('truncated')
                    if result.status_code:
                        url.status = str(result.status_code)
                if result and result.status_code and result.status_code == 200:
                    url.valid = 2
                else:
                    if url.valid > -5:
                        url.valid = url.valid - 1
                    else:
                        logging.info('Broken url: %s' % (url.url))
                url.last_check = datetime.datetime.now()
                url.put()


class DocumentTask(webapp.RequestHandler):
    def get(self):
        doc_id = self.request.get('doc_id', '')
        if doc_id:
            try:
                prefix = self.request.get('prefix', '')
                name = str(prefix) + str(doc_id)
                taskqueue.add(name=name, queue_name='document', url='/tasks/update_document', params={'doc_id': doc_id})
            except taskqueue.TombstonedTaskError:
                logging.warning('TombstonedTaskError %s' % (name))
            except taskqueue.TaskAlreadyExistsError:
                logging.warning('TaskAlreadyExistsError %s' % (name))

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
                    logging.warning('TombstonedTaskError %s' % (str(name)))
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s' % (str(name)))

    def post(self):
        doc_id = self.request.get('doc_id', '')
        if doc_id:
            # logging.debug('doc_id: %s' % (doc_id))
            urlinstance = Url.get_by_id(int(doc_id))

            if urlinstance:
                # If not valid url, delete from index
                if urlinstance.valid < 0:
                    doc_index = search.Index(name='url')
                    logging.info('Delete invalid (%s) url (ID %s) from document index \'url\' (%s)' % (
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

                    logging.debug('doc; channel=%s, user=%s, url=%s, date=%s, title=%s, comment=%s, tag=%s, rate=%s' % (
                    channel, user, url, date, title, comment, tag, rate))
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
                    except Exception, e:
                        logging.error('doc_id: %s, error %s' % (str(doc_id), e))
                        doc = None

                    try:
                        if doc:
                            search.Index(name='url').put(doc)
                            urlinstance.document_date = datetime.datetime.now()
                            urlinstance.put()
                        else:
                            logging.error('Doc missing.')
                    except search.Error:
                        logging.error('Create Document failed.')
            else:
                logging.debug('No urlinstance for doc_id: %s' % (doc_id))
        else:
            logging.debug('No id')


application = webapp.WSGIApplication([
    ('/tasks/maintenance', MaintenanceTask),
    ('/tasks/post', PostTask),
    ('/tasks/rate', RateTask),
    ('/tasks/extra', ExtraTask),
    ('/tasks/title', TitleTask),
    ('/tasks/valid', ValidTask),
    ('/tasks/update_document', DocumentTask),
],
    debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
