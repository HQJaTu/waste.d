from django.db import models


class Counter(models.Model):
    name = models.CharField('counter_name', max_length=40, primary_key=True)
    count = models.IntegerField()
