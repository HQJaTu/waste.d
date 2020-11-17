from django.db import models
from django.db.models import F
from .fields import timestamp


class Counter(models.Model):
    name = models.CharField('counter_name', max_length=40, primary_key=True)
    count = models.IntegerField()
    idate = models.DateTimeField(auto_now_add=True, editable=False, null=False)
    ts = timestamp.TimestampField(auto_created=True, auto_now_add=True, null=False)

    @staticmethod
    def increment(name):
        obj = Counter.objects.filter(pk=name)
        if obj:
            obj.update(count=F('count') + 1)

        else:
            obj = Counter(name=name, count=1)
            obj.save()

        return obj.count
