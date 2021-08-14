from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from dcodex_lectionary import models

class Command(BaseCommand):
    help = 'Does necessary maintenance on lectionary systems. Needed if the lections are changed.'

    def handle(self, *args, **options):
        models.LectionarySystem.maintenance_all_systems()
