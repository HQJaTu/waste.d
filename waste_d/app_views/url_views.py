import cgi
import os, sys
import datetime
import re

from google.appengine.ext.webapp import template
from django.http import HttpResponseRedirect
from django.shortcuts import render
import logging
from google.appengine.api import taskqueue, users, memcache
from google.appengine.datastore.datastore_query import Cursor

from url_models import Url, Channel, ChannelUrl, Post, Rate, Extra


def index(request, date=None, cursor=None, rss=None, channel_filter=None):
    data = []
    today = datetime.date.today()

    # logging.debug('data %s' % (str(data)))
    tag_cloud = memcache.get('tag_cloud')
    if not tag_cloud:
        taskqueue.add(queue_name='default', url='/tasks/maintenance', params={'type': 'tag_cloud'})

    if not date:
        date = today
    else:
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
    next_date = date - datetime.timedelta(days=-1)
    prev_date = date - datetime.timedelta(days=1)

    # postqry=Post.query(Post.date>=datetime.datetime.combine(date, datetime.time()),Post.date<datetime.datetime.combine(next_date, datetime.time())).order(-Post.date)
    postqry = Post.query(Post.date < datetime.datetime.combine(next_date, datetime.time())).order(-Post.date)
    if cursor:
        cursor = Cursor(urlsafe=cursor)
        posts, next_cursor, more = postqry.fetch_page(10, start_cursor=cursor)
    else:
        posts, next_cursor, more = postqry.fetch_page(20)

    # urls=Url.query().order(-Url.idate).fetch(10)
    for post in posts:  # TODO pagination
        # logging.debug('Post %s' % (post))

        channelurl = post.channelurl.get()
        # logging.debug('ChannelUrl %s' % (channelurl))

        channel = channelurl.channel.get()
        # logging.debug('Channel %s' % (channel))

        url = channelurl.url.get()
        # logging.debug('Url %s' % (url))

        # logging.debug('URL/post: channel=%s, user=%s, url=%s' % (channel.name, post.user, url.url))
        # logging.debug('Private channel? %s (%s)' % (channel,channel.private))
        if not channel_filter or channel_filter.lower() == channel.name[1:].lower():
            if channel.private == False:
                extras = Extra.query(Extra.channelurl == post.channelurl)
                rates = Rate.query(Rate.channelurl == post.channelurl)
                data.append({'channelurl': channelurl, 'channel': channel, 'post': post, 'url': url, 'extras': extras,
                             'rates': rates})

        '''
        channelurls = post.channelurl
        logging.debug('CU: %s: %s' % (post.key.id(),channelurls))
        data[post.key.id()]={}
        #for channelurl in channelurls:
        data[post.key.id()]['channelurls']=channelurls
        '''

    template_values = {
        'data': data,
        'tag_cloud': tag_cloud,
        'next': next_cursor,
        'date': date,
        'next_date': next_date,
        'prev_date': prev_date,
        'more': more,
        'channel': channel_filter,
    }
    if cursor:
        return render('urls2.html', template_values)

    return render('urls.html', template_values)


def view(request, urlid):
    data = []
    logging.debug('View ChannelUrl %s' % (urlid))
    try:
        urlid = int(urlid)
    except:
        pass
    channelurl = ChannelUrl.get_by_id(urlid)
    if channelurl:
        channel = channelurl.channel.get()
        url = channelurl.url.get()

        if channel.private == False:
            extras = Extra.query(Extra.channelurl == channelurl.key)
            rates = Rate.query(Rate.channelurl == channelurl.key)
            rating = channelurl.rating()
            # data.append({'channel':channel,'post':post,'url':url,'extras': extras})
            data = {'channel': channel, 'post': post, 'url': url, 'extras': extras, 'rates': rates, 'rating': rating}

    template_values = {
        'data': data,
    }
    return render('url.html', template_values)


def view_master(request, urlid):
    data = []
    logging.debug('View (Master)Url %s' % (urlid))
    try:
        urlid = int(urlid)
    except:
        pass

    url = Url.get_by_id(urlid)
    if url:
        channelurls = ChannelUrl.query(ChannelUrl.url == url.key)
        for channelurl in channelurls:
            channel = channelurl.channel.get()
            if channel.private == False:
                extras = Extra.query(Extra.channelurl == channelurl.key)
                rates = Rate.query(Rate.channelurl == channelurl.key)
                rating = channelurl.rating()
                # data.append({'channel':channel,'post':post,'url':url,'extras': extras})
                data.append({'channel': channel, 'channelurl': channelurl, 'post': post, 'url': url, 'extras': extras,
                             'rates': rates, 'rating': rating})

    template_values = {
        'data': data,
        'user': users.get_current_user(),
    }

    return render('masterurl.html', template_values)


def tag(request, tag):
    extras = Extra.query(Extra.tag == tag)
    # logging.debug('Tag %s' % (tag))
    data = []
    urls = []
    for extra in extras:
        channelurl = extra.channelurl.get()
        channel = channelurl.channel.get()
        posts = Post.query(Post.channelurl == channelurl.key)
        for post in posts:
            url = channelurl.url.get()
            # logging.debug('Url %s' % (url.url))
            # data.append({'url':url})
            if channel.private == False:
                extras = Extra.query(Extra.channelurl == post.channelurl, Extra.tag != tag)
                rates = Rate.query(Rate.channelurl == post.channelurl)
                d_dict = {'date': post.date, 'channelurl': channelurl, 'channel': channel, 'post': post, 'url': url,
                          'extras': extras, 'rates': rates}
                if url not in urls:
                    data.append(d_dict)
                    urls.append(url)

    data.sort(key=lambda item: item['date'], reverse=True)
    template_values = {
        'data': data,
        'selected_tag': tag,
        'tag_cloud': memcache.get('tag_cloud'),
    }

    return render('tags.html', template_values)


def test(request, a=None, b=None, c=None):
    template_values = {
        'a': a,
        'b': b,
        'c': c,
    }

    return render('test.html', template_values)


def post(request, post_url, post_channel=None, post_user=None):
    if not post_user:
        post_user = 'Anonymous'
    if not post_channel:
        post_channel = '!' + post_user
    logging.debug('post: C=%s U=%s P=%s' % (post_channel, post_user, post_url))
    name = ''.join(re.findall('[a-zA-Z0-9_-]', post_channel + '_' + post_user + '_' + post_url))[:500]
    try:
        taskqueue.add(name=name, queue_name='default', url='/tasks/post',
                      params={'post_channel': post_channel, 'post_user': post_user, 'post_url': post_url})
    except taskqueue.TombstonedTaskError:
        logging.warning('Duplicate task name %s' % name)

    return HttpResponseRedirect('/url/')


def rate(request, post_channel, post_user, type, post_url):
    logging.debug('rate: C=%s U=%s T=%s P=%s' % (post_channel, post_user, type, post_url))
    types = ['up', 'down', 'wtf', 'nsfw']
    if type in types:
        name = ''.join(re.findall('[a-zA-Z0-9_-]', post_channel + '_' + post_user + '_' + type + '_' + post_url))[:500]
        try:
            taskqueue.add(name=name, queue_name='default', url='/tasks/rate',
                          params={'channel': post_channel, 'post_user': post_user, 'type': type, 'post_url': post_url})
        except taskqueue.TombstonedTaskError:
            logging.warning('Duplicate task name %s' % name)

    else:
        logging.warning('Wrong type (%s)! %s %s %s' % (type, post_channel, post_user, post_url))
    return HttpResponseRedirect('/url/')


def extra(request, post_channel, post_user, extra, post_url):
    logging.debug('rate: C=%s U=%s E=%s P=%s' % (post_channel, post_user, extra, post_url))
    name = ''.join(re.findall('[a-zA-Z0-9_-]', post_channel + '_' + post_user + '_' + extra + '_' + post_url))[:500]
    try:
        taskqueue.add(name=name, queue_name='default', url='/tasks/extra',
                      params={'channel': post_channel, 'post_user': post_user, 'extra': extra, 'post_url': post_url})
    except taskqueue.TombstonedTaskError:
        logging.warning('Duplicate task name %s' % name)
    return HttpResponseRedirect('/url/')
