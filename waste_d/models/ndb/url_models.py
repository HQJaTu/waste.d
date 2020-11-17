from google.cloud import ndb
from urllib.parse import urlparse


class Url(ndb.Model):
    url = ndb.StringProperty()
    title = ndb.StringProperty()

    # Valid url: >=1
    valid = ndb.IntegerProperty(default=1)
    status = ndb.StringProperty()
    last_check = ndb.DateTimeProperty(auto_now_add=True)

    # FullTextSearch related stuff
    document_date = ndb.DateTimeProperty()

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def parse(self):
        return urlparse(self.url)

    def loc_title(self):
        loc = urlparse(self.url).scheme + '//' + urlparse(self.url).netloc
        if self.title:
            return loc + ' - ' + self.title
        else:
            new_title = ''.join(self.url.split('/')[-1:])
            if len(new_title) > 40:
                return loc + ' - ' + new_title[:20] + '...' + new_title[len(new_title) - 10:]
            else:
                return loc + ' - ' + new_title

    def short(self):
        if self.title:
            return self.title
        else:
            new_title = ''.join(self.url.split('/')[-1:])
            if len(new_title) > 40:
                return new_title[:20] + '...' + new_title[len(new_title) - 10:]
            else:
                return new_title

    def __str__(self):
        if self.title:
            return self.title
        else:
            return ''.join(self.url.split('/')[-1:])


class Channel(ndb.Model):
    name = ndb.StringProperty()
    private = ndb.BooleanProperty(default=False)

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def __str__(self):
        return self.name


class ChannelUrl(ndb.Model):
    # Reference to Channel & Url
    channel = ndb.KeyProperty(kind=Channel)
    url = ndb.KeyProperty(kind=Url)

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def rating(self):
        value = 0
        rates = Rate.query(Rate.channelurl == self.key)
        for rate in rates:
            value = value + rate.value
        return value

    def extras(self, plain=False):
        xtra = ''
        extras = Extra.query(Extra.channelurl == self.key)
        for extra in extras:
            if extra.comment:
                xtra = xtra + ' ' + extra.comment
            if extra.tag:
                if plain:
                    xtra = xtra + extra.tag
                elif extra.tag == 'WTF':
                    xtra = xtra + ' <span class="label label-danger">' + extra.tag + '</span>'
                elif extra.tag == 'NSFW':
                    xtra = xtra + ' <span class="label label-warning">' + extra.tag + '</span>'
                else:
                    xtra = xtra + ' <span class="label label-primary">' + extra.tag + '</span>'
            if extra.related:
                if plain:
                    xtra = xtra + extra.related
                else:
                    xtra = xtra + ' <span class="label label-info">' + extra.related + '</span>'
        return xtra.strip()

    def posts(self):
        chl = self.channel.get()
        msg = ''
        msgs = []
        posts = Post.query(Post.channelurl == self.key)
        for post in posts:
            msgs.append('%s/%s @ %s' % (post.user, chl.name, post.date))
        return ', '.join(msgs)

    def __str__(self):
        return str(self.key.id())


class Post(ndb.Model):
    user = ndb.StringProperty()
    date = ndb.DateTimeProperty()

    # Reference to ChannelUrl
    channelurl = ndb.KeyProperty(kind=ChannelUrl)

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def __str__(self):
        return str(self.key.id())


class Rate(ndb.Model):
    user = ndb.StringProperty()
    value = ndb.IntegerProperty()

    # Reference to ChannelUrl
    channelurl = ndb.KeyProperty(kind=ChannelUrl)

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def __str__(self):
        return '%s %+d' % (self.user, self.value)


class Extra(ndb.Model):
    user = ndb.StringProperty()
    related = ndb.StringProperty()
    tag = ndb.StringProperty()
    comment = ndb.StringProperty()

    # Reference to Post
    channelurl = ndb.KeyProperty(kind=ChannelUrl)

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def __str__(self):
        retval = ''
        if self.comment:
            retval += ' ' + self.comment
        if self.tag:
            retval += ' <a href="/url/tag/' + self.tag + '/"><span class="label '
            if self.tag == 'WTF':
                retval += 'label-danger'
            elif self.tag == 'NSFW':
                retval += 'label-warning'
            else:
                retval += 'label-primary'
            retval += '">' + self.tag + '</span></a>'
        if self.related:
            retval += ' <a href="/url/view/' + self.related + '/"><span class="label label-info">' + self.related + '</span></a>'
        return retval.strip()
