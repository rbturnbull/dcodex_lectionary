# Generated by Django 2.2.2 on 2019-09-19 12:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dcodex', '0001_initial'),
        ('dcodex_bible', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DayOfYear',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.IntegerField(choices=[(0, 'Sunday'), (1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday')])),
                ('period', models.CharField(choices=[('E', 'Easter'), ('P', 'Pentecost'), ('F', 'Feast of the Cross'), ('L', 'Lent'), ('G', 'Great Week')], max_length=1)),
                ('week', models.CharField(max_length=15)),
                ('weekday_number', models.CharField(max_length=32)),
                ('earliest_date', models.CharField(max_length=15)),
                ('latest_date', models.CharField(max_length=15)),
            ],
            options={
                'verbose_name_plural': 'Days of year',
            },
        ),
        migrations.CreateModel(
            name='Lection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='LectionarySystem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='LectionInSystem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_on_day', models.IntegerField(default=0)),
                ('day_of_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dcodex_lectionary.DayOfYear')),
                ('lection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dcodex_lectionary.Lection')),
                ('system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dcodex_lectionary.LectionarySystem')),
            ],
            options={
                'ordering': ['day_of_year', 'order_on_day'],
            },
        ),
        migrations.CreateModel(
            name='LectionaryVerse',
            fields=[
                ('verse_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcodex.Verse')),
                ('unique_string', models.CharField(default='', max_length=20)),
                ('bible_verse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dcodex_bible.BibleVerse')),
            ],
            options={
                'abstract': False,
                'base_manager_name': 'objects',
            },
            bases=('dcodex.verse',),
        ),
        migrations.AddField(
            model_name='lectionarysystem',
            name='lections',
            field=models.ManyToManyField(through='dcodex_lectionary.LectionInSystem', to='dcodex_lectionary.Lection'),
        ),
        migrations.CreateModel(
            name='Lectionary',
            fields=[
                ('manuscript_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcodex.Manuscript')),
                ('system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dcodex_lectionary.LectionarySystem')),
            ],
            options={
                'verbose_name_plural': 'Lectionaries',
            },
            bases=('dcodex.manuscript',),
        ),
        migrations.AddField(
            model_name='lection',
            name='verses',
            field=models.ManyToManyField(to='dcodex_lectionary.LectionaryVerse'),
        ),
    ]
