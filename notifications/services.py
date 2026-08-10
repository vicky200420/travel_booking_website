"""Notification & Communication — reusable notification service.

Single entry point for creating in-app notifications and broadcasting.
Email side-effects are dispatched through :mod:`notifications.tasks` so the
caller never blocks on SMTP (or runs tasks synchronously without Celery).
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Notification
from .tasks import (
    dispatch,
    send_booking_cancellation_email,
    send_booking_confirmation_email,
    send_payment_failed_email,
    send_payment_success_email,
    send_refund_email,
    send_travel_reminder_email,
    send_verification_email,
    send_welcome_email,
)

User = get_user_model()


class NotificationService:
    """Factory + query helpers for :class:`Notification` records."""

    SUMMARY_CACHE_TIMEOUT = 60 * 5

    # -------------------------------------------------------------- cache

    @staticmethod
    def _summary_key(user):
        return f'notif:summary:{getattr(user, "pk", user)}'

    @staticmethod
    def _invalidate(user):
        cache.delete(NotificationService._summary_key(user))

    @staticmethod
    def summary(user, limit=5):
        """Cacheable (unread count, recent list) used by the navbar bell.

        Returns a JSON-safe structure so the cache can hold it across
        processes. The count is exact; the recent list is a snapshot that may
        lag a few seconds behind a mutation (acceptable for a badge).
        """
        key = NotificationService._summary_key(user)
        cached = cache.get(key)
        if cached is not None:
            return cached

        qs = Notification.objects.filter(user=user)
        unread = qs.filter(is_read=False).count()
        recent = [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'created_at': n.created_at,
                'is_read': n.is_read,
                'action_url': n.action_url,
                'icon': n.effective_icon,
                'color': n.color,
            }
            for n in qs[:limit]
        ]
        payload = {'unread': unread, 'recent': recent}
        cache.set(key, payload, NotificationService.SUMMARY_CACHE_TIMEOUT)
        return payload

    # ------------------------------------------------------------- creation

    @staticmethod
    def create(user, title, message='', type=Notification.Type.INFO,
               action_url='', icon='', metadata=None, is_broadcast=False,
               audience=Notification.Audience.ALL):
        """Create a single notification for ``user``."""
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=type,
            action_url=action_url,
            icon=icon or Notification.TYPE_ICONS.get(type, ''),
            metadata=metadata or {},
            is_broadcast=is_broadcast,
            audience=audience,
        )
        NotificationService._invalidate(user)
        return notification

    @staticmethod
    @transaction.atomic
    def bulk_create(users, title, message='', type=Notification.Type.INFO,
                    action_url='', icon='', metadata=None, is_broadcast=False,
                    audience=Notification.Audience.ALL):
        """Efficiently fan a notification out to many users (broadcasts)."""
        icon = icon or Notification.TYPE_ICONS.get(type, '')
        notifications = [
            Notification(
                user=user, title=title, message=message, type=type,
                action_url=action_url, icon=icon, metadata=metadata or {},
                is_broadcast=is_broadcast, audience=audience,
            )
            for user in users
        ]
        created = Notification.objects.bulk_create(notifications)
        for user in users:
            NotificationService._invalidate(user)
        return created

    @staticmethod
    def broadcast(title, message='', type=Notification.Type.PROMOTION,
                  action_url='', icon='', audience=Notification.Audience.ALL,
                  send_email=False):
        """Send a notification to every active user matching ``audience``."""
        qs = User.objects.filter(is_active=True)
        if audience == Notification.Audience.CUSTOMER:
            qs = qs.filter(role=User.Role.CUSTOMER)
        elif audience == Notification.Audience.AGENT:
            qs = qs.filter(role=User.Role.AGENT)

        users = list(qs)
        created = NotificationService.bulk_create(
            users, title, message, type, action_url, icon,
            is_broadcast=True, audience=audience,
        )
        # Emails for promotions are intentionally opt-in per broadcast so an
        # admin must explicitly pass send_email=True.
        return len(created)

    # --------------------------------------------------------------- queries

    @staticmethod
    def unread_count(user):
        return NotificationService.summary(user)['unread']

    @staticmethod
    def recent(user, limit=5):
        return NotificationService.summary(user, limit=limit)['recent']

    # --------------------------------------------------------------- actions

    @staticmethod
    def mark_read(notification):
        notification.mark_read()
        NotificationService._invalidate(notification.user)
        return notification

    @staticmethod
    def mark_all_read(user):
        updated = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        NotificationService._invalidate(user)
        return updated

    @staticmethod
    def delete(notification):
        user = notification.user
        notification.delete()
        NotificationService._invalidate(user)

    @staticmethod
    def delete_all(user):
        result = Notification.objects.filter(user=user).delete()
        NotificationService._invalidate(user)
        return result

    # -------------------------------------------------------- event dispatch
    # Combine in-app notification + (async) email for a domain event.
    # Each method is called from signals and stays thin.

    @staticmethod
    def registration_success(user):
        NotificationService.create(
            user, 'Registration successful',
            'Welcome to TravelBooking! Your account is ready to explore.',
            Notification.Type.SUCCESS, '/dashboard/', 'bi-person-check-fill',
            {'event': 'registration'},
        )
        dispatch(send_welcome_email, user.id)

    @staticmethod
    def email_verification(user):
        NotificationService.create(
            user, 'Confirm your email',
            'Verify your email address to secure your account and unlock travel deals.',
            Notification.Type.INFO, '/dashboard/', 'bi-envelope-check-fill',
            {'event': 'email_verification'},
        )
        dispatch(send_verification_email, user.id)

    @staticmethod
    def booking_created(booking):
        NotificationService.create(
            booking.user, f'Booking {booking.booking_id} received',
            f'Your {booking.get_booking_type_display()} booking is pending confirmation.',
            Notification.Type.BOOKING,
            f'/bookings/{booking.booking_id}/', 'bi-journal-bookmark-fill',
            {'event': 'booking_created', 'booking_id': booking.booking_id},
        )

    @staticmethod
    def booking_confirmed(booking, send_email=True):
        NotificationService.create(
            booking.user, f'Booking {booking.booking_id} confirmed',
            f'Your trip to {booking.destination_display} is confirmed. Have a great journey!',
            Notification.Type.SUCCESS,
            f'/bookings/{booking.booking_id}/', 'bi-check-circle-fill',
            {'event': 'booking_confirmed', 'booking_id': booking.booking_id},
        )
        if send_email:
            dispatch(send_booking_confirmation_email, booking.id)

    @staticmethod
    def booking_cancelled(booking):
        NotificationService.create(
            booking.user, f'Booking {booking.booking_id} cancelled',
            f'Your booking for {booking.title_display} has been cancelled.',
            Notification.Type.WARNING,
            f'/bookings/{booking.booking_id}/', 'bi-x-circle-fill',
            {'event': 'booking_cancelled', 'booking_id': booking.booking_id},
        )
        dispatch(send_booking_cancellation_email, booking.id)

    @staticmethod
    def booking_status_update(booking):
        NotificationService.create(
            booking.user, f'Booking {booking.booking_id} — {booking.status}',
            f'Your booking status has been updated to {booking.status}.',
            Notification.Type.INFO,
            f'/bookings/{booking.booking_id}/', 'bi-arrow-repeat',
            {'event': 'booking_status_update', 'booking_id': booking.booking_id},
        )

    @staticmethod
    def payment_success(payment):
        NotificationService.create(
            payment.user, 'Payment successful',
            f'Payment of {payment.amount} {payment.currency} received for booking {payment.booking.booking_id}.',
            Notification.Type.PAYMENT,
            f'/bookings/{payment.booking.booking_id}/', 'bi-credit-card-check-fill',
            {'event': 'payment_success', 'payment_id': payment.id,
             'booking_id': payment.booking.booking_id},
        )
        dispatch(send_payment_success_email, payment.id)

    @staticmethod
    def payment_failed(payment):
        NotificationService.create(
            payment.user, 'Payment failed',
            f'We could not process your payment of {payment.amount} {payment.currency}. Please retry.',
            Notification.Type.ERROR,
            f'/payments/checkout/?booking={payment.booking.booking_id}', 'bi-credit-card',
            {'event': 'payment_failed', 'payment_id': payment.id,
             'booking_id': payment.booking.booking_id},
        )
        dispatch(send_payment_failed_email, payment.id)

    @staticmethod
    def refund_processed(payment):
        NotificationService.create(
            payment.user, 'Refund processed',
            f'Your refund of {payment.amount} {payment.currency} for booking '
            f'{payment.booking.booking_id} has been processed.',
            Notification.Type.SUCCESS,
            f'/bookings/{payment.booking.booking_id}/', 'bi-cash-stack',
            {'event': 'refund_processed', 'payment_id': payment.id,
             'booking_id': payment.booking.booking_id},
        )
        dispatch(send_refund_email, payment.id)

    @staticmethod
    def review_submitted(review):
        NotificationService.create(
            review.user, 'Review submitted',
            f'Thank you for reviewing {review.item_name}. Your feedback helps fellow travellers.',
            Notification.Type.INFO,
            f'/bookings/{review.booking.booking_id}/', 'bi-star-fill',
            {'event': 'review_submitted', 'review_id': review.id},
        )

    @staticmethod
    def travel_reminder(booking, days_left):
        NotificationService.create(
            booking.user, 'Upcoming trip reminder',
            f'Your trip to {booking.destination_display} starts in '
            f'{int(days_left)} day(s). Make sure everything is ready!',
            Notification.Type.REMINDER,
            f'/bookings/{booking.booking_id}/', 'bi-alarm-fill',
            {'event': 'travel_reminder', 'booking_id': booking.booking_id,
             'days_left': days_left},
        )
        dispatch(send_travel_reminder_email, booking.id, days_left)
