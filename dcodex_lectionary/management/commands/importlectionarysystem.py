from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from dcodex_lectionary import models

class Command(BaseCommand):
    help = 'Imports a lectionary system from CSV.'

    def add_arguments(self, parser):
        parser.add_argument('system', type=str, help="The name of the lectionary system to import.")
        parser.add_argument('csv', type=str, help="A CSV file with columns corresponding to 'period', 'week', 'day', 'passage', 'parallels' (optional).")
        parser.add_argument('--flush', action='store_true', help="Removes the lections on this system before importing.")

    def handle(self, *args, **options):
        system, _ = models.LectionarySystem.objects.update_or_create( name=options['system'] )
        if options['flush']:
            system.lections.all().delete()

        system.import_csv( options['csv'] )
