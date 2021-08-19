from django.core.management.base import BaseCommand, CommandError
from dcodex_lectionary import models

class Command(BaseCommand):
    help = 'Creates an Apostolos e lectionary system.'

    def handle(self, *args, **options):
        models.LectionarySystem.create_apostolos_e()
