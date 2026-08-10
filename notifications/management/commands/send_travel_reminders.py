"""Send scheduled travel reminders for upcoming trips.

Usage:
    python manage.py send_travel_reminders
"""
from django.core.management.base import BaseCommand

from notifications.reminders import TravelReminderService


class Command(BaseCommand):
    help = 'Generate travel-reminder notifications and emails for upcoming trips.'

    def handle(self, *args, **options):
        created = TravelReminderService.prepare_reminders()
        self.stdout.write(self.style.SUCCESS(f'{created} travel reminder(s) generated.'))
