from google.cloud import ndb
from .url_models import Url, ChannelUrl, Extra


class Greeting(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author = ndb.UserProperty()
    content = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class News(ndb.Model):
    content = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)
    link_text = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

    def __unicode__(self):
        if self.link:
            if self.link_text:
                return '%s: <a target="_blank" href="%s">%s</a>' % (self.content, self.link, self.link_text)
            else:
                text = ''
                comments = []
                url = Url.query(Url.url == self.link).get(keys_only=True)
                channel_url = ChannelUrl.query(ChannelUrl.url == url).get(keys_only=True)
                extra = Extra.query(Extra.channelurl == channel_url).get(keys_only=False)
                if extra and extra.comment:
                    text = extra.comment
                if not text:
                    text = ''.join(self.link.split('/')[-1:])
                return '%s: <a target="_blank" href="%s">%s</a>' % (self.content, self.link, text)
        return self.content

    def __str__(self):
        return unicode(self).encode('utf-8')
