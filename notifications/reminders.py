"""Notification & Communication — scheduled travel reminders.

Reminders are generated for confirmed upcoming bookings at fixed checkpoints
(7 days, 3 days, 24 hours before departure). Deduplication is guaranteed via a
unique metadata key, so the scheduler is idempotent and safe to run daily.

Runs stand-alone via ``manage.py send_travel_reminders`` or from a cron / beat
schedule (``notifications.tasks.prepare_travel_reminders`` is the Celery entry).
"""
from datetime import timedelta

from django.utils import timezone

from .models import Notification
from .services import NotificationService

# Checkpoints expressed as "days before travel start". 24h -> 0 (same day).
REMINDER_WINDOWS = (7, 3, 0)


class TravelReminderService:

    @staticmethod
    def prepare_reminders(now=None):
        """Create + email reminders due at each window. Returns created count."""
        from bookings.models import Booking

        now = now or timezone.localtime(timezone.now())
        today = now.date()

        created = 0
        for days_left in REMINDER_WINDOWS:
            target = today + timedelta(days=days_left)
            bookings = Booking.objects.filter(
                status=Booking.Status.CONFIRMED,
                travel_start_date=target,
            ).select_related('user')

            for booking in bookings:
                already_sent = Notification.objects.filter(
                    user=booking.user,
                    metadata__event='travel_reminder',
                    metadata__booking_id=booking.booking_id,
                    metadata__days_left=days_left,
                ).exists()
                if already_sent:
                    continue

                NotificationService.travel_reminder(booking, days_left)
                created += 1

        return created
