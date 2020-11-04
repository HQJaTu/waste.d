# -*- coding: utf-8 -*-
import cgi
import os
import datetime
import logging
import re
import random
import urllib2
from lxml import etree
import re
from django.utils.encoding import smart_unicode
from django.utils import simplejson
from google.appengine.api import search
import string
import counter

DEFAULT_COUNTER_NAME = 'XXX'

from google.appengine.ext import ndb
from google.appengine.api import users, urlfetch, images, memcache, mail, taskqueue
from google.appengine.ext.webapp import template
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from url_models import Url, Channel, ChannelUrl, Post, Rate, Extra
from models import News


def post(request):
    today = datetime.date.today()
    now = datetime.datetime.now()

    url = None
    url_title = None
    channel = None
    user = None
    line = None
    date = None

    comment = None
    tags = None

    old_url = False
    old_user = None
    old_date = None

    if request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data)

            url = data.get('url')
            channel = data.get('channel').lower()
            user = data.get('user')
            line = data.get('line')
            date = datetime.datetime.strptime(data.get('date'), '%Y%m%d%H%M')
            logging.debug('date: %s, user: %s, channel: %s, url: %s, line: %s' % (date, user, channel, url, line))
        except Exception as e:
            logging.warning('Error %s' % (e))
    if not url:
        retval = simplejson.dumps({'id': 0, 'title': ''})
        return HttpResponse(retval, mimetype="application/json")

    orig_url = url
    # Add http:// when needed
    if not url.lower().startswith('http'):
        url = 'http://' + url
    # logging.info('Url/API/Post: Channel=%s User=%s Url=%s' % (channel,user,url))

    # Fetch url (async):
    #  a) check statuscode LATER
    #  b) get title LATER
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(rpc, url, allow_truncated=True)

    # Get url from DB:
    #  a) already exists
    #  b) ChannelCheck
    # 1. tarkista onko olemassa jo ko. Url, lisää jos ei, muuten päivitä (udate, valid?): valid-juttu joo ehkä jos tarpeen, ei muuten
    urlquery = Url.query(Url.url == url)
    urlinstance = urlquery.get()
    if not urlinstance:
        urlinstance = Url(url=url)
        urlinstance.put()
        # logging.debug('New url %s' % (url))
    else:
        logging.info('Old url %s' % (url))

    # 2. tarkista onko olemassa jo ko. Channel, lisää jos ei
    channelquery = Channel.query(Channel.name == channel)
    channelinstance = channelquery.get()
    if not channelinstance:
        if channel.startswith('#'):
            private = False
        else:
            private = True
        channelinstance = Channel(name=channel, private=private)
        channelinstance.put()
        logging.info('New channel %s' % (channel))

    # 3. tarkista onko url jo olemassa channel-tasolla
    channelurlquery = ChannelUrl.query(ChannelUrl.url == urlinstance.key, ChannelUrl.channel == channelinstance.key)
    channelurlinstance = channelurlquery.get()
    if not channelurlinstance:
        l = list(string.ascii_uppercase)
        l.append('Z')

        DEFAULT_COUNTER_NAME = chr(now.isocalendar()[0] - 2010 + 65) + l[(now.isocalendar()[1] - 1) / 2]
        # logging.debug('DEFAULT_COUNTER_NAME: %s' % (DEFAULT_COUNTER_NAME))

        counter.increment(DEFAULT_COUNTER_NAME)
        key_name = DEFAULT_COUNTER_NAME + str(counter.get_count(DEFAULT_COUNTER_NAME))
        # logging.debug('key_name %s' % (key_name))

        channelurlinstance = ChannelUrl(id=key_name, channel=channelinstance.key, url=urlinstance.key)
        channelurlinstance.put()
        # logging.debug('New channelurl %s/%s' % (channel,url))
    else:
        # logging.info('OLDIE! %s %s' % (channelurlinstance.channel.name,channelurlinstance.url.url))
        logging.info('Old channelurl %s %s' % (channel, url))
        old_url = True
        old_post = Post.query(Post.channelurl == channelurlinstance.key).order(Post.date).get()
        try:
            old_date = old_post.date.strftime("%d.%m.%y %H:%M")
        except:
            try:
                old_date = old_post.idate.strftime("%d.%m.%y %H:%M")
            except:
                old_date = ''
        old_user = old_post.user

    # 4. Lisätään postaus (tarkistetaan ettei ole jo)
    postquery = Post.query(Post.channelurl == channelurlinstance.key, Post.user == user, Post.date == date)
    postinstance = postquery.get()
    if postinstance:
        logging.info('Old post; channel: %s, url: %s, user: %s' % (channel, url, user))
    else:
        postinstance = Post(channelurl=channelurlinstance.key, user=user, date=date)
        postinstance.put()

        # 5. extrat
        # Comment
        if orig_url != line:
            comment = line.replace(orig_url, '<url>')
            # logging.debug('Line: %s, url: %s, comment: %s' % (line,orig_url,comment))

            # TODO:
            # <url>/
            # Tyhjät kommentit: ''
            if comment not in ['<url>/', '']:
                Extra(user=user, comment=comment, channelurl=channelurlinstance.key).put()
            else:
                comment = None

    # Resolve async calls
    # Urlfetch
    try:
        result = rpc.get_result()
        if result and result.content_was_truncated:
            logging.debug('Truncated')
            tags = 'truncated'
            Extra(user='Tarantino', tag=tags, channelurl=channelurlinstance.key).put()
        if result and result.status_code:
            urlinstance.status = str(result.status_code)
            urlinstance.last_check = datetime.datetime.now()
        if result.status_code == 200:
            urlinstance.valid = 2
            try:
                # Fetch title
                req = urllib2.Request(url)
                # logging.debug('req %s' % (req))
                req.add_header('User-agent', 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')
                res = urllib2.urlopen(req)
                # logging.debug('res %s' % (res))
                doc = res.read()
                # logging.debug('doc %s' % (doc))
                encoding = res.headers.getparam('charset')
                # logging.debug('encoding %s' % (encoding))
                tree = etree.fromstring(doc, etree.HTMLParser(encoding=encoding))
                title = tree.find(".//title").text
                url_title = smart_unicode(re.sub(r'\s+', ' ', title).strip())
            except:
                logging.warning('Title not fetched %s' % (url))
            else:
                # logging.debug('Url: %s, title %s' % (url,title))
                urlinstance.title = url_title
            # except:
            #  logging.debug('TitleTask: title not fetched %s' % (url))
            # urlinstance.title = url

        else:
            if urlinstance.valid > -5:
                urlinstance.valid = urlinstance.valid - 1
            else:
                logging.info('Broken url: %s' % (url))
        urlinstance.put()
        # logging.debug('URL %s saved (status code %s).' % (url,str(result.status_code)))
    except (urlfetch.DownloadError, urlfetch.DeadlineExceededError, urlfetch.InternalTransientError):
        # Request timed out or failed.
        # ...
        urlinstance.valid = urlinstance.valid - 1
        urlinstance.put()
        logging.warning('Urlfetch \'%s\' failed.' % (url))

    # Update News
    if channelinstance.private == False and date.date() >= today:
        try:
            news = News(content='Link')
            news.link = url
            news.link_text = url_title or url
            news.put()
            # logging.debug('News updated')
        except:
            logging.warning('News update failed')
    else:
        logging.info('News not updated, private channel/old url')

    if not url_title:
        url_title = ''.join(url.split('/')[-1:])
    # logging.debug('Title: %s' % (url_title))

    # Create Document (FullTextSearch)
    doc_id = str(urlinstance.key.id())
    try:
        doc = search.Document(doc_id=doc_id, fields=[
            search.TextField(name='channel', value=channel),
            search.TextField(name='user', value=user),
            search.TextField(name='url', value=url),
            search.DateField(name='date', value=date),
            search.TextField(name='title', value=url_title),
            search.TextField(name='comment', value=comment, language='fi'),
            search.TextField(name='tag', value=tags, language='fi'),
            search.NumberField(name='rate', value=0)
        ], language='en')
    except Exception as e:
        logging.error('Error %s' % (e))
    # logging.debug('Document fields updated')

    if urlinstance.document_date:
        try:
            taskqueue.add(name=doc_id + '_post', queue_name='document', url='/tasks/update_document',
                          params={'doc_id': doc_id})
        except taskqueue.TombstonedTaskError:
            logging.warning('TombstonedTaskError %s_post' % (doc_id))
        except taskqueue.TaskAlreadyExistsError:
            logging.warning('TaskAlreadyExistsError %s_post' % (doc_id))
        except:
            logging.critical('Something weird happened')

    try:
        search.Index(name='url').put(doc)
        urlinstance.document_date = datetime.datetime.now()
        urlinstance.put()
    except search.Error:
        logging.warning('Create Document failed.')
        try:
            taskqueue.add(name=doc_id + '_retry', queue_name='document', url='/tasks/update_document',
                          params={'doc_id': doc_id})
        except taskqueue.TombstonedTaskError:
            logging.warning('TombstonedTaskError %s_retry' % (doc_id))
        except taskqueue.TaskAlreadyExistsError:
            logging.warning('TaskAlreadyExistsError %s_retry' % (doc_id))
        except:
            logging.critical('Something weird happened, again?')

    # Finally: return status and/or title (+something)
    logging.info('Returning id: %s, title: %s, old: %s' % (channelurlinstance.key.id(), url_title, old_url))
    retval = simplejson.dumps(
        {'id': channelurlinstance.key.id(), 'title': url_title, 'old': old_url, 'old_user': old_user,
         'old_date': old_date})
    return HttpResponse(retval, mimetype="application/json")


def info(request):
    today = datetime.date.today()
    now = datetime.datetime.now()

    l = list(string.ascii_uppercase)
    l.append('Z')

    DEFAULT_COUNTER_NAME = chr(now.isocalendar()[0] - 2010 + 65) + l[(now.isocalendar()[1] - 1) / 2]

    id = None
    url = None
    if request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data)

            id = str(data.get('id', '')).upper()
            url = data.get('url', '')
            logging.debug('id: %s/url: %s' % (id, url))
        except Exception as e:
            logging.warning('Error %s' % (e))
    try:
        id = int(id)
        if id < 1000:
            id = DEFAULT_COUNTER_NAME + str(id)
            # logging.debug('%s' % id)
    except:
        pattern1 = r'^[A-Z]{1}$'
        pattern2 = r'^[A-Z]{2}$'
        if re.match(pattern1, id):
            id = DEFAULT_COUNTER_NAME[0] + str(id)
            # logging.debug('%s' % id)
            id = id + str(counter.get_count(id))
            # logging.debug('%s' % id)
        elif re.match(pattern2, id):
            id = id + str(counter.get_count(id))
    channelurl = ChannelUrl.get_by_id(id)
    if channelurl:
        url = channelurl.url.get().url
        url_title = channelurl.url.get().title
        rate = channelurl.rating()
        extra = channelurl.extras(plain='True')
        posts = channelurl.posts()
        channel = channelurl.channel.get().name

        retval = simplejson.dumps(
            {'id': channelurl.key.id(), 'url': url, 'title': url_title, 'rate': rate, 'extra': extra, 'posts': posts})
    else:
        retval = simplejson.dumps({'id': 0})
    return HttpResponse(retval, mimetype="application/json")


def find(request):
    idx = ''
    channel = '*'
    content = ''
    retval = []
    limit = 5
    offset = 0

    if request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data)

            channel = data.get('channel', '*').lower()
            content = data.get('content', '')
            idx = data.get('index', 'url')
            try:
                limit = int(data.get('limit', 5))
            except:
                limit = 5
            try:
                offset = int(data.get('offset', 0))
            except:
                offset = 0
            logging.debug('channel: %s, content: %s' % (channel, content))
        except Exception as e:
            logging.warning('Error %s' % (e))
    # if not content:
    #  retval=simplejson.dumps([{'id':0,'title': ''}])
    #  return HttpResponse(retval, mimetype="application/json")

    try:
        # Set query options
        # date_desc = search.SortExpression(
        #  expression='_score',
        #  direction=search.SortExpression.DESCENDING,
        #  default_value='')

        # Sort up to 1000 matching results by subject in descending order
        # sort = search.SortOptions(expressions=[date_desc], limit=10)

        options = search.QueryOptions(
            limit=limit,  # the number of results to return
            offset=offset,
            # cursor=cursor,
            # sort_options=sort,
            # returned_fields=['author', 'subject', 'summary'],
            # snippeted_fields=['content']
        )

        if channel and channel != '*':
            content = 'channel:' + channel + ' ' + content

        query = search.Query(query_string=content, options=options)
        index = search.Index(name=idx)

        results = index.search(query)
        for scored_document in results:
            # process scored_document
            doc_id = scored_document.doc_id
            doc_url = None
            doc_user = None
            doc_channel = None
            doc_date = None

            for field in scored_document.fields:
                if field.name == 'url':
                    doc_url = field.value
                if field.name == 'user':
                    doc_user = field.value
                if field.name == 'channel':
                    doc_channel = field.value
                if field.name == 'date':
                    doc_date = field.value

            # logging.debug('Search result: %s' % (scored_document))

            urlinstance = Url.get_by_id(int(doc_id))
            if channel == '*':
                channelurlquery = ChannelUrl.query(ChannelUrl.url == urlinstance.key)
            else:
                channelinstance = Channel.query(Channel.name == channel).get()
                channelurlquery = ChannelUrl.query(ChannelUrl.url == urlinstance.key,
                                                   ChannelUrl.channel == channelinstance.key)

            channelurls = channelurlquery.fetch(3)

            for channelurl in channelurls:
                retval.append({'id': channelurl.key.id(), 'url': urlinstance.url, 'posts': channelurl.posts()})

    except search.Error:
        logging.exception('Search failed')

    # logging.debug('retval %s' % (retval))
    retvaljson = simplejson.dumps(retval)
    return HttpResponse(retvaljson, mimetype="application/json")


def rate(request):
    id = 0
    user = None
    value = 0

    if request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data)

            id = data.get('id').upper()
            user = data.get('user')
            value = int(data.get('value', 0))
            logging.debug('user: %s, id: %s, value: %s' % (user, id, value))

        except Exception as e:
            logging.warning('Error %s' % (e))

    try:
        id = int(id)
    except:
        pass
    channelurl = ChannelUrl.get_by_id(id)
    if not channelurl:
        retval = simplejson.dumps({'id': 0, 'rate': ''})
        return HttpResponse(retval, mimetype="application/json")
    else:
        rate = Rate(user=user, value=value, channelurl=channelurl.key)
        rate.put()

        # Update Document (FullTextSearch)
        url = channelurl.url.get()
        doc_id = str(url.key.id())
        try:
            doc = search.Index(name='url').get(doc_id)
            if not doc:
                logging.warning('Document not found.')
                try:
                    taskqueue.add(name=str(doc_id) + '_update', queue_name='document', url='/tasks/update_document',
                                  params={'doc_id': doc_id})
                except taskqueue.TombstonedTaskError:
                    logging.warning('TombstonedTaskError %s_update' % (str(doc_id)))
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s_update' % (str(doc_id)))
            else:
                new_fields = []
                for field in doc.fields:
                    if field.name == 'rate':
                        new_value = float(field.value) + float(value)
                        logging.debug('Updating rate: %s + %s = %s' % (field.value, value, new_value))
                        new_fields.append(search.NumberField(name='rate', value=new_value))
                    elif field.name == 'date':
                        new_fields.append(search.DateField(name=field.name, value=field.value))
                    else:
                        new_fields.append(search.TextField(name=field.name, value=field.value))
            new_doc = search.Document(doc_id=doc_id, fields=new_fields, language='en')

        except Exception as e:
            logging.warning('Error %s' % (e))

        try:
            search.Index(name='url').put(new_doc)
        except search.Error:
            logging.exception('Create/Update Document failed.')

        retval = simplejson.dumps({'id': id, 'rate': channelurl.rating()})
        return HttpResponse(retval, mimetype="application/json")


def extra(request):
    id = '0'
    user = None
    type = None
    value = None
    new_doc = None

    if request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data)

            id = data.get('id').upper()
            user = data.get('user')
            type = data.get('type')
            value = data.get('value')
            logging.debug('user: %s, id: %s, type: %s, value: %s' % (user, id, type, value))

        except Exception as e:
            logging.warning('Error %s' % (e))

    try:
        id = int(id)
    except:
        pass
    channelurl = ChannelUrl.get_by_id(id)
    if not channelurl:
        retval = simplejson.dumps({'id': 0, 'extra': ''})
        return HttpResponse(retval, mimetype="application/json")
    else:
        if type == 'comment':
            Extra(user=user, comment=value, channelurl=channelurl.key).put()
        if type == 'tag':
            Extra(user=user, tag=value, channelurl=channelurl.key).put()
        if type == 'related':
            Extra(user=user, related=value, channelurl=channelurl.key).put()

        # Update Document (FullTextSearch)
        url = channelurl.url.get()
        doc_id = str(url.key.id())
        try:
            doc = search.Index(name='url').get(doc_id)
            if not doc:
                logging.warning('Document not found.')
                try:
                    taskqueue.add(name=str(doc_id) + '_extra', queue_name='document', url='/tasks/update_document',
                                  params={'doc_id': doc_id})
                except taskqueue.TombstonedTaskError:
                    logging.warning('TombstonedTaskError %s_extra' % (str(doc_id)))
                except taskqueue.TaskAlreadyExistsError:
                    logging.warning('TaskAlreadyExistsError %s_extra' % (str(doc_id)))
            else:
                new_fields = []
                for field in doc.fields:
                    if type == 'tag' and field.name == 'tag':
                        if field.value:
                            new_value = field.value + ' ' + value
                        else:
                            new_value = value
                        logging.debug('Updating tags: %s + %s = %s' % (field.value, value, new_value))
                        new_fields.append(search.TextField(name=field.name, value=new_value))
                    if type == 'comment' and field.name == 'comment':
                        if field.value:
                            new_value = field.value + ' ' + value
                        else:
                            new_value = value
                        logging.debug('Updating comments: %s + %s = %s' % (field.value, value, new_value))
                        new_fields.append(search.TextField(name=field.name, value=new_value))
                    elif field.name == 'rate':
                        new_fields.append(search.NumberField(name=field.name, value=field.value))
                    elif field.name == 'date':
                        new_fields.append(search.DateField(name=field.name, value=field.value))
                    else:
                        new_fields.append(search.TextField(name=field.name, value=field.value))
                new_doc = search.Document(doc_id=doc_id, fields=new_fields, language='en')

        except Exception as e:
            logging.warning('Error %s' % (e))

        try:
            if new_doc:
                search.Index(name='url').put(new_doc)
            else:
                logging.warning('New document (new_doc) missing?')
        except search.Error:
            logging.exception('Create/Update Document failed.')

        retval = simplejson.dumps({'id': id, type: value})
        return HttpResponse(retval, mimetype="application/json")
