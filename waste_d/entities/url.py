import datetime
import string
import logging
import re
import requests
from http import HTTPStatus
from lxml import etree
from django.utils.encoding import smart_text
from waste_d.models.ndb.url_models import Url, Channel, ChannelUrl, Post, Extra
from waste_d.models import Counter, News
from django_cloud_tasks import remote_task, batch_execute
from waste_d.tasks.document import QUEUE_DOCUMENT


class UrlLogic:
    today = datetime.date.today()
    now = datetime.datetime.now()

    user_agent = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    request_timeout = 5.0

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

    def __init__(self, url, channel, user, date, line):
        self.url = url
        self.channel = channel
        self.user = user
        self.date = date
        self.line = line

        # Sanity
        if not self.url.startswith('http://') and not self.url.startswith('https://'):
            logging.error('Url/API/Post: Channel=%s User=%s Url=%s' % (channel, user, url))
            raise ValueError("Bad url: %s" % self.url)

    def get(self):
        orig_url = self.url

        today = datetime.date.today()

        # Originally all URLs were fetched.
        # Not fetching an existing URL.

        # Get url from DB:
        #  a) already exists
        #  b) ChannelCheck
        # 1. tarkista onko olemassa jo ko. Url, lisää jos ei, muuten päivitä (udate, valid?): valid-juttu joo ehkä jos tarpeen, ei muuten
        urlquery = Url.query(Url.url == self.url)
        urlinstance = urlquery.get()
        if not urlinstance:
            urlinstance = Url(url=self.url)
            urlinstance.put()
            # logging.debug('New url %s' % (url))
        else:
            logging.info('Old url %s' % (self.url))

        # 2. tarkista onko olemassa jo ko. Channel, lisää jos ei
        channelquery = Channel.query(Channel.name == self.channel)
        channelinstance = channelquery.get()
        if not channelinstance:
            if self.channel.startswith('#'):
                private = False
            else:
                private = True
            channelinstance = Channel(name=self.channel, private=private)
            channelinstance.put()
            logging.info('New channel %s' % self.channel)

        # 3. tarkista onko url jo olemassa channel-tasolla
        channelurlquery = ChannelUrl.query(ChannelUrl.url == urlinstance.key,
                                           ChannelUrl.channel == channelinstance.key)
        channelurlinstance = channelurlquery.get()
        if not channelurlinstance:
            counter_name = UrlLogic._get_counter_name_for_now()
            count_obj = Counter(name=counter_name)
            count = count_obj.increment(counter_name)
            key_name = counter_name + str(count)
            # logging.debug('key_name %s' % (key_name))

            channelurlinstance = ChannelUrl(id=key_name, channel=channelinstance.key, url=urlinstance.key)
            channelurlinstance.put()
            # logging.debug('New channelurl %s/%s' % (channel,url))
        else:
            # logging.info('OLDIE! %s %s' % (channelurlinstance.channel.name,channelurlinstance.url.url))
            logging.info('Old channelurl %s %s' % (self.channel, self.url))
            old_url = True
            old_post = Post.query(Post.channelurl == channelurlinstance.key).order(Post.date).get()
            try:
                old_date = old_post.date.strftime("%d.%m.%y %H:%M")
            except Exception:
                try:
                    old_date = old_post.idate.strftime("%d.%m.%y %H:%M")
                except Exception:
                    old_date = ''
            old_user = old_post.user

        # 4. Lisätään postaus (tarkistetaan ettei ole jo)
        postquery = Post.query(Post.channelurl == channelurlinstance.key,
                               Post.user == self.user, Post.date == self.date)
        postinstance = postquery.get()
        if postinstance:
            logging.info('Old post; channel: %s, url: %s, user: %s' % (self.channel, self.url, self.user))
        else:
            postinstance = Post(channelurl=channelurlinstance.key, user=self.user, date=self.date)
            postinstance.put()

            # 5. extract
            # Comment
            if orig_url != self.line:
                comment = self.line.replace(orig_url, '<url>')
                # logging.debug('Line: %s, url: %s, comment: %s' % (line,orig_url,comment))

                # TODO:
                # <url>/
                # Tyhjät kommentit: ''
                if comment not in ['<url>/', '']:
                    Extra(user=self.user, comment=comment, channelurl=channelurlinstance.key).put()
                else:
                    comment = None

        # Go do some HTTP-requesting
        url_title = self._get_url(urlinstance)

        # Update News
        if channelinstance.private == False and self.date.date() >= today:
            try:
                news = News(content='Link')
                news.link = self.url
                news.link_text = url_title or self.url
                news.put()
                # logging.debug('News updated')
            except Exception:
                logging.warning('News update failed')
        else:
            logging.info('News not updated, private channel/old url')

        if not url_title:
            url_title = ''.join(self.url.split('/')[-1:])
        # logging.debug('Title: %s' % (url_title))

        # Create Document (Cloud Search API)
        doc_id = urlinstance.key.id()
        """
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
        """

        if not urlinstance.document_date:
            # NDB has no date for this document, let's process it!
            document_task = remote_task(queue=QUEUE_DOCUMENT, handler='waste_d.tasks.document.post',
                                        http_service_account=True)
            task_args = {
                'doc_id': doc_id
            }

            try:
                #document_task(payload=task_args).execute()
                payload_1 = document_task(payload=task_args)

                # Execute in batch:
                batch_execute([payload_1])
            except Exception as e:
                logging.critical('Something weird happened. Exception: %s' % e)

        """
        # Update document (Cloud Search API)
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
            except Exception:
                logging.critical('Something weird happened, again?')
        """

        return channelinstance

    @staticmethod
    def _get_counter_name_for_now():
        now = datetime.datetime.now()
        l = list(string.ascii_uppercase)
        l.append('Z')

        # Key:
        # 1st char: A = 2010
        # 2nd char: A = 1st week of the year
        # Example:
        counter_name = chr(now.isocalendar()[0] - 2010 + 65) + l[int((now.isocalendar()[1] - 1) / 2)]

        return counter_name

    def _get_url(self, urlinstance):
        headers = {
            'User-Agent': self.user_agent
        }

        # Go for URL!
        try:
            response = requests.get(self.url, headers=headers, timeout=self.request_timeout)
        except (requests.exceptions.Timeout, requests.exceptions.TooManyRedirects):
            # Maybe set up for a retry, or continue in a retry loop
            # or
            # Tell the user their URL was bad and try a different one
            # Request timed out or failed.
            urlinstance.status = str(599)
            urlinstance.last_check = datetime.datetime.now()
            urlinstance.valid = urlinstance.valid - 1
            urlinstance.put()
            logging.warning('URL "%s" failed (no HTTP-status).' % self.url)

            return
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            raise SystemExit(e)

        # Harvest result
        urlinstance.status = str(response.status_code)
        urlinstance.last_check = datetime.datetime.now()

        if response.status_code == HTTPStatus.OK:
            urlinstance.valid = 2
            tree = etree.fromstring(response.text, etree.HTMLParser(encoding=response.encoding))
            title = tree.find(".//title").text
            url_title = smart_text(re.sub(r'\s+', ' ', title).strip())
            urlinstance.title = url_title
        else:
            if urlinstance.valid > -5:
                urlinstance.valid = urlinstance.valid - 1
            else:
                logging.info('Broken url: %s' % self.url)
            url_title = None

        urlinstance.put()
        logging.debug('URL "%s" saved (HTTP/%d).' % (self.url, response.status_code))

        return url_title
