import datetime
import logging
import re
import json
import string
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from django.views.decorators.cache import never_cache
from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser
from waste_d.models.ndb.url_models import Url, Channel, ChannelUrl, Rate, Extra
from waste_d.entities.url import UrlLogic
from waste_d.bq_models import Links
from waste_d.authentication import token_authentication

logger = logging.getLogger(__name__)


class API(APIView):
    authentication_classes = [token_authentication.WastedTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Make sure GCP BQ-client is alive for later access.
        links = Links()
        links.get_dataset()

    @never_cache
    @parser_classes((JSONParser,))
    def post(self, request):

        url = None
        url_title = None
        platform = None
        chat = None
        channel = None
        user = None
        line = None
        date = None

        comment = None
        tags = None

        old_url = False
        old_user = None
        old_date = None

        # Some parts are stored in API-key
        platform = request.auth.platform
        chat = request.auth.chat

        try:
            url = request.data.get('url')
            channel = request.data.get('channel').lower()
            user = request.data.get('user')
            line = request.data.get('line')
            date = datetime.datetime.strptime(request.data.get('date'), '%Y%m%d%H%M')
            logging.debug('date: %s, user: %s, channel: %s, url: %s, line: %s' % (date, user, channel, url, line))
        except Exception as e:
            logging.warning('Error %s' % e)

        if not url:
            retval = json.dumps({'id': 0, 'title': ''})

            return HttpResponse(retval, content_type="application/json")

        urllogic = UrlLogic(url, platform, chat, channel, user, date, line)
        channelurlinstance = urllogic.get()

        # Finally: return status and/or title (+something)
        logging.info('Returning id: %s, title: %s, old: %s' % (channelurlinstance.key.id(), url_title, old_url))
        retval = json.dumps(
            {'id': channelurlinstance.key.id(), 'title': url_title, 'old': old_url, 'old_user': old_user,
             'old_date': old_date})

        return HttpResponse(retval, content_type="application/json")

    def info(self, request):
        today = datetime.date.today()
        now = datetime.datetime.now()

        l = list(string.ascii_uppercase)
        l.append('Z')

        DEFAULT_COUNTER_NAME = chr(now.isocalendar()[0] - 2010 + 65) + l[(now.isocalendar()[1] - 1) / 2]

        id = None
        url = None
        if request.method == "POST":
            try:
                data = json.loads(request.raw_post_data)

                id = str(data.get('id', '')).upper()
                url = data.get('url', '')
                logging.debug('id: %s/url: %s' % (id, url))
            except Exception as e:
                logging.warning('Error %s' % e)
        try:
            id = int(id)
            if id < 1000:
                id = DEFAULT_COUNTER_NAME + str(id)
                # logging.debug('%s' % id)
        except Exception:
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

            retval = json.dumps(
                {'id': channelurl.key.id(), 'url': url, 'title': url_title, 'rate': rate, 'extra': extra,
                 'posts': posts})
        else:
            retval = json.dumps({'id': 0})
        return HttpResponse(retval, content_type="application/json")

    def find(self, request):
        idx = ''
        channel = '*'
        content = ''
        retval = []
        limit = 5
        offset = 0

        if request.method == "POST":
            try:
                data = json.loads(request.raw_post_data)

                channel = data.get('channel', '*').lower()
                content = data.get('content', '')
                idx = data.get('index', 'url')
                try:
                    limit = int(data.get('limit', 5))
                except Exception:
                    limit = 5
                try:
                    offset = int(data.get('offset', 0))
                except Exception:
                    offset = 0
                logging.debug('channel: %s, content: %s' % (channel, content))
            except Exception as e:
                logging.warning('Error %s' % (e))
        # if not content:
        #  retval=json.dumps([{'id':0,'title': ''}])
        #  return HttpResponse(retval, content_type="application/json")

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
        retvaljson = json.dumps(retval)
        return HttpResponse(retvaljson, content_type="application/json")

    def rate(self, request):
        id = 0
        user = None
        value = 0

        if request.method == "POST":
            try:
                data = json.loads(request.raw_post_data)

                id = data.get('id').upper()
                user = data.get('user')
                value = int(data.get('value', 0))
                logging.debug('user: %s, id: %s, value: %s' % (user, id, value))

            except Exception as e:
                logging.warning('Error %s' % (e))

        try:
            id = int(id)
        except Exception:
            pass
        channelurl = ChannelUrl.get_by_id(id)
        if not channelurl:
            retval = json.dumps({'id': 0, 'rate': ''})
            return HttpResponse(retval, content_type="application/json")
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

            retval = json.dumps({'id': id, 'rate': channelurl.rating()})
            return HttpResponse(retval, content_type="application/json")

    def extra(self, request):
        id = '0'
        user = None
        type = None
        value = None
        new_doc = None

        if request.method == "POST":
            try:
                data = json.loads(request.raw_post_data)

                id = data.get('id').upper()
                user = data.get('user')
                type = data.get('type')
                value = data.get('value')
                logging.debug('user: %s, id: %s, type: %s, value: %s' % (user, id, type, value))

            except Exception as e:
                logging.warning('Error %s' % (e))

        try:
            id = int(id)
        except Exception:
            pass
        channelurl = ChannelUrl.get_by_id(id)
        if not channelurl:
            retval = json.dumps({'id': 0, 'extra': ''})
            return HttpResponse(retval, content_type="application/json")
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

            retval = json.dumps({'id': id, type: value})

            return HttpResponse(retval, content_type="application/json")
