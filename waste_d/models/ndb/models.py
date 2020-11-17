from google.cloud import ndb


class Greeting(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author = ndb.UserProperty()
    content = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class News(ndb.Model):
    # Note:
    # A StringProperty must be indexed. Previously setting ``indexed=False`` was allowed,
    # but this usage is no longer supported.
    content = ndb.StringProperty(indexed=True)
    link = ndb.StringProperty(indexed=True)
    link_text = ndb.StringProperty(indexed=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
