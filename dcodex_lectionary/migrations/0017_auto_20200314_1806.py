# Generated by Django 2.2.2 on 2020-03-14 07:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dcodex_lectionary', '0016_auto_20200314_1804'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lectionaryverse',
            name='bible_verse',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='dcodex_bible.BibleVerse'),
        ),
    ]
