from django.core.management.base import BaseCommand, CommandError
from dcodex_lectionary import models

class Command(BaseCommand):
    help = 'Creates an esk lectionary system for the Epistles.'

    def handle(self, *args, **options):
        models.LectionarySystem.create_epistles_esk()
