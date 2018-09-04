#coding:utf-8
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
# Create your models here.

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

class Event(models.Model):
    title = models.CharField(max_length=50, null=False, unique=True)
    limit = models.IntegerField(default=200)
    #定义一个元组
    choice = ((0, '未开始'),(1, '进行中'),(2, '已结束'))
    status = models.IntegerField(choices=choice, default=0)
    address = models.CharField(max_length=50, null=False)
    time = models.DateTimeField(null=False)

    def __unicode__(self):
        return self.title

class Guest(models.Model):
    name = models.CharField(max_length=10, null=False)
    phone_number = models.CharField(max_length=11, null=False, unique=True)
    e_mail = models.CharField(max_length=30)
    #嘉宾和会议，多对多关系
    event = models.ManyToManyField(Event)

    def __unicode__(self):
        return self.name