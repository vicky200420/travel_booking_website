"""Notification & Communication — email service.

All transactional email logic lives here, isolated from the notification
service and view layer. Methods render the premium HTML templates under
``templates/notifications/emails/`` and send a multipart message (HTML +
plain-text fallback) through Django's email backend.

Delivery is intentionally fire-and-forget at the call site: callers enqueue
through :mod:`notifications.tasks` so the same code path works synchronously
in development and through Celery in production.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


class EmailService:
    """Templated, brand-consistent transactional email delivery."""

    TEMPLATE_MAP = {
        'welcome': 'notifications/emails/welcome.html',
        'booking_confirmation': 'notifications/emails/booking_confirmation.html',
        'booking_cancellation': 'notifications/emails/booking_cancellation.html',
        'payment_success': 'notifications/emails/payment_success.html',
        'payment_failed': 'notifications/emails/payment_failed.html',
        'travel_reminder': 'notifications/emails/travel_reminder.html',
        'refund': 'notifications/emails/refund.html',
    }

    # ------------------------------------------------------------------ core

    @staticmethod
    def send(key, recipient, subject, context, email_to_self=None):
        """Render ``key`` template and send an HTML + text email.

        Returns ``True`` on success, ``False`` when the backend is unset or an
        exception is swallowed (notifications must never break the request).
        """
        template = EmailService.TEMPLATE_MAP.get(key)
        if not template:
            logger.warning('Unknown email template key: %s', key)
            return False

        from .emails_context import build_email_context
        context = build_email_context(**context)

        recipients = [recipient]
        if email_to_self:
            recipients.append(settings.DEFAULT_FROM_EMAIL)

        try:
            html_body = render_to_string(template, context)
            text_body = EmailService._plain_text(html_body)
            message = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            message.attach_alternative(html_body, 'text/html')
            message.send(fail_silently=False)
            logger.info('Email "%s" sent to %s', key, recipient)
            return True
        except Exception as exc:  # pragma: no cover - backend dependent
            logger.error('Email "%s" to %s failed: %s', key, recipient, exc)
            return False

    @staticmethod
    def _plain_text(html_body):
        """Crude HTML -> text conversion for multipart fallback."""
        import re
        text = re.sub(r'<br\s*/?>', '\n', html_body)
        text = re.sub(r'</(p|div|tr|h[1-6]|li)>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()

    # ------------------------------------------------------- subject helpers

    @staticmethod
    def welcome_subject(user):
        return f'Welcome aboard, {user.first_name or user.username}!'

    @staticmethod
    def verification_subject():
        return 'Confirm your email address'

    @staticmethod
    def booking_confirmation_subject(booking):
        return f'Booking {booking.booking_id} confirmed — your trip is set!'

    @staticmethod
    def booking_cancellation_subject(booking):
        return f'Booking {booking.booking_id} has been cancelled'

    @staticmethod
    def payment_success_subject(payment):
        return f'Payment received — {payment.transaction_id}'

    @staticmethod
    def payment_failed_subject(payment):
        return f'Payment could not be completed — {payment.transaction_id}'

    @staticmethod
    def refund_subject(payment):
        return f'Refund processed — {payment.transaction_id}'

    @staticmethod
    def reminder_subject(booking, days_left):
        label = 'hours' if days_left < 1 else 'days'
        value = int(days_left * 24) if days_left < 1 else int(days_left)
        return f'Your trip is coming up! {value} {label} to go'

    # ----------------------------------------------------------- build links

    @staticmethod
    def booking_url(booking):
        return f"{settings.SITE_URL.rstrip('/')}{reverse('booking_detail', args=[booking.booking_id])}"

    @staticmethod
    def booking_pay_url(booking):
        return f"{settings.SITE_URL.rstrip('/')}{reverse('payment_checkout')}?booking={booking.booking_id}"

    @staticmethod
    def verify_email_url(user):
        from .utils import generate_verification_token
        token = generate_verification_token(user)
        return f"{settings.SITE_URL.rstrip('/')}{reverse('verify_email', args=[token])}"

    @staticmethod
    def absolute_url(path):
        return f"{settings.SITE_URL.rstrip('/')}/{path.lstrip('/')}"
