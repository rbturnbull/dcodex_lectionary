# Generated by Django 2.2.2 on 2019-09-19 12:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dcodex_lectionary', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lectionaryverse',
            name='unique_string',
        ),
    ]
