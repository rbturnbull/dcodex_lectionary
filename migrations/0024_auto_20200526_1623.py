# Generated by Django 2.2.2 on 2020-05-26 06:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dcodex_lectionary', '0023_auto_20200526_1559'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lectionaryversemembership',
            old_name='cummulative_mass_from_lection_start',
            new_name='cumulative_mass_from_lection_start',
        ),
    ]
