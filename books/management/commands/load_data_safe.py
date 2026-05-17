"""Naloži fixture brez post_save signalov (reši UNIQUE conflict pri Profile)."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save


class Command(BaseCommand):
    help = 'Naloži fixture z onemogočenimi post_save signali.'

    def add_arguments(self, parser):
        parser.add_argument('fixture', nargs='+', type=str)

    def handle(self, *args, **options):
        old_receivers = post_save.receivers[:]
        post_save.receivers = []

        try:
            for fixture in options['fixture']:
                self.stdout.write(f'Nalagam: {fixture} ...')
                call_command('loaddata', fixture, verbosity=1)
        finally:
            post_save.receivers = old_receivers

        self.stdout.write(self.style.SUCCESS('Uvoz končan.'))
