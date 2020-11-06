from google.cloud import ndb


# Once this middleware is activated in Django settings, NDB calls inside Django
# views will be executed in context, with a separate context for each request.
def ndb_django_middleware(get_response):
    client = ndb.Client()

    def middleware(request):
        with client.context():
            return get_response(request)

    return middleware
