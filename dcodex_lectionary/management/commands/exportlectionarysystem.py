from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from dcodex_lectionary import models

class Command(BaseCommand):
    help = 'Exports a lectionary system to CSV.'

    def add_arguments(self, parser):
        parser.add_argument('system', type=str, help="The name of the lectionary system to export.")
        parser.add_argument('csv', type=str, help="A path to output CSV file.")

    def handle(self, *args, **options):
        system = models.LectionarySystem.objects.filter( name=options['system'] ).first()
        system.export_csv( options['csv'] )
