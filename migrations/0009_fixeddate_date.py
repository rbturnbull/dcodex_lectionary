# Generated by Django 2.2.2 on 2020-01-06 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcodex_lectionary', '0008_auto_20200106_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='fixeddate',
            name='date',
            field=models.DateField(default=None, null=True),
        ),
    ]
