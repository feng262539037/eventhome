# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20180419_1155'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, b'\xe6\x9c\xaa\xe5\xbc\x80\xe5\xa7\x8b'), (1, b'\xe8\xbf\x9b\xe8\xa1\x8c\xe4\xb8\xad'), (2, b'\xe5\xb7\xb2\xe7\xbb\x93\xe6\x9d\x9f')]),
        ),
    ]
