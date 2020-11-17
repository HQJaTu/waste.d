from google.cloud import ndb


class Topic(ndb.Model):
    date = ndb.DateTimeProperty()
    channel = ndb.StringProperty()
    nick = ndb.StringProperty()
    topic = ndb.StringProperty()

    # System stuff
    idate = ndb.DateTimeProperty(auto_now_add=True)
    udate = ndb.DateTimeProperty(auto_now=True)

    def __str__(self):
        if not self.topic:
            return ''
        else:
            return self.topic
