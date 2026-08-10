"""Notification & Communication — async task wrappers.

The app is prepared for Celery: every side-effectful operation (email
delivery, reminder generation) is exposed as a :func:`celery.shared_task`.
When Celery is not installed or not configured the fallback decorator runs the
function synchronously, so development works out of the box.

Callers should route work through :func:`dispatch`, which enqueues with
``.delay()`` under Celery and falls back to a direct call otherwise.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - environment dependent
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover
    CELERY_AVAILABLE = False

    def shared_task(*args, **kwargs):
        def decorate(func):
            return func
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorate


def dispatch(func, *args, **kwargs):
    """Run ``func`` immediately or enqueue it depending on Celery presence."""
    if CELERY_AVAILABLE:
        func.delay(*args, **kwargs)
    else:
        func(*args, **kwargs)


# ---------------------------------------------------------------------------
# Low-level email delivery
# ---------------------------------------------------------------------------

@shared_task
def send_email(key, recipient, subject, context):
    from .emails import EmailService
    return EmailService.send(key, recipient, subject, context)


# ---------------------------------------------------------------------------
# Transactional event emails (re-fetch models by id — JSON-serializable args)
# ---------------------------------------------------------------------------

@shared_task
def send_welcome_email(user_id):
    from django.contrib.auth import get_user_model

    from .emails import EmailService
    from .utils import booking_context  # noqa: F401 (kept for symmetry)

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return False
    context = {
        'user_first_name': user.first_name or user.username,
        'user_email': user.email,
        'message': (
            f'Thanks for joining {settings.SITE_NAME}! '
            'Your account is ready — let’s start planning your next getaway.'
        ),
        'primary_action': {'label': 'Explore Destinations', 'url': EmailService.absolute_url('/packages/')},
    }
    return EmailService.send('welcome', user.email, EmailService.welcome_subject(user), context)


@shared_task
def send_verification_email(user_id):
    from django.contrib.auth import get_user_model

    from .emails import EmailService
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return False
    context = {
        'user_first_name': user.first_name or user.username,
        'user_email': user.email,
        'message': (
            'Please confirm this email address so we can keep you updated about '
            'your bookings and exclusive travel deals.'
        ),
        'primary_action': {'label': 'Verify Email Address', 'url': EmailService.verify_email_url(user)},
    }
    return EmailService.send('welcome', user.email, EmailService.verification_subject(), context)


@shared_task
def send_booking_confirmation_email(booking_id):
    from bookings.models import Booking

    from .emails import EmailService
    from .utils import booking_context

    booking = Booking.objects.select_related('flight').filter(id=booking_id).first()
    if not booking:
        return False
    ctx = booking_context(booking)
    ctx.update(
        user_first_name=booking.user.first_name or booking.user.username,
        user_email=booking.user.email,
        message='Great news — your travel plans are locked in and confirmed.',
        primary_action={'label': 'View Booking', 'url': EmailService.booking_url(booking)},
    )
    return EmailService.send(
        'booking_confirmation', booking.user.email,
        EmailService.booking_confirmation_subject(booking), ctx,
    )


@shared_task
def send_booking_cancellation_email(booking_id):
    from bookings.models import Booking

    from .emails import EmailService
    from .utils import booking_context

    booking = Booking.objects.select_related('flight').filter(id=booking_id).first()
    if not booking:
        return False
    ctx = booking_context(booking)
    ctx.update(
        user_first_name=booking.user.first_name or booking.user.username,
        user_email=booking.user.email,
        message='Your booking has been cancelled. Refunds, if applicable, are processed within 5–7 business days.',
        primary_action={'label': 'Browse More Trips', 'url': EmailService.absolute_url('/packages/')},
    )
    return EmailService.send(
        'booking_cancellation', booking.user.email,
        EmailService.booking_cancellation_subject(booking), ctx,
    )


@shared_task
def send_payment_success_email(payment_id):
    from payments.models import Payment

    from .emails import EmailService
    from .utils import payment_context

    payment = Payment.objects.select_related('booking__flight').filter(id=payment_id).first()
    if not payment:
        return False
    ctx = payment_context(payment)
    ctx.update(
        user_first_name=payment.user.first_name or payment.user.username,
        user_email=payment.user.email,
        message='Thank you! Your payment was received successfully.',
        primary_action={'label': 'View Booking', 'url': EmailService.booking_url(payment.booking)},
    )
    ctx['details_blocks'] = [
        {
            'title': 'Payment Summary',
            'icon': 'bi-credit-card',
            'rows': [
                {'label': 'Transaction ID', 'value': payment.transaction_id},
                {'label': 'Gateway', 'value': payment.get_gateway_display()},
                {'label': 'Method', 'value': payment.payment_method or 'Online'},
                {'label': 'Amount', 'value': ctx['amount']},
                {'label': 'Date', 'value': f'{payment.paid_at:%b %d, %Y %H:%M}'},
            ],
        },
        {
            'title': 'Trip Summary',
            'icon': 'bi-suitcase-lg',
            'rows': [
                {'label': 'Booking', 'value': payment.booking.booking_id},
                {'label': 'Destination', 'value': payment.booking.destination_display},
                {'label': 'Travel Dates', 'value': f'{payment.booking.travel_start_date:%b %d, %Y} — {payment.booking.travel_end_date:%b %d, %Y}'},
                {'label': 'Travelers', 'value': payment.booking.total_travelers},
            ],
        },
    ]
    return EmailService.send(
        'payment_success', payment.user.email,
        EmailService.payment_success_subject(payment), ctx,
    )


@shared_task
def send_payment_failed_email(payment_id):
    from payments.models import Payment

    from .emails import EmailService
    from .utils import payment_context

    payment = Payment.objects.select_related('booking').filter(id=payment_id).first()
    if not payment:
        return False
    ctx = payment_context(payment)
    ctx.update(
        user_first_name=payment.user.first_name or payment.user.username,
        user_email=payment.user.email,
        message='We couldn’t complete your payment. Your booking is still pending — please retry.',
        primary_action={'label': 'Retry Payment', 'url': EmailService.booking_pay_url(payment.booking)},
    )
    return EmailService.send(
        'payment_failed', payment.user.email,
        EmailService.payment_failed_subject(payment), ctx,
    )


@shared_task
def send_refund_email(payment_id):
    from payments.models import Payment

    from .emails import EmailService
    from .utils import payment_context

    payment = Payment.objects.select_related('booking').filter(id=payment_id).first()
    if not payment:
        return False
    ctx = payment_context(payment)
    ctx.update(
        user_first_name=payment.user.first_name or payment.user.username,
        user_email=payment.user.email,
        message=(
            f'A refund of {ctx["amount"]} for booking {payment.booking.booking_id} '
            'has been processed to your original payment method.'
        ),
        primary_action={'label': 'View Booking', 'url': EmailService.booking_url(payment.booking)},
    )
    return EmailService.send(
        'refund', payment.user.email,
        EmailService.refund_subject(payment), ctx,
    )


@shared_task
def send_travel_reminder_email(booking_id, days_left):
    from bookings.models import Booking

    from .emails import EmailService
    from .utils import booking_context

    booking = Booking.objects.select_related('flight').filter(id=booking_id).first()
    if not booking:
        return False
    ctx = booking_context(booking)
    ctx.update(
        user_first_name=booking.user.first_name or booking.user.username,
        user_email=booking.user.email,
        message=(
            'Your trip is almost here! Review your itinerary and make sure '
            'everything is ready for departure.'
        ),
        primary_action={'label': 'View Itinerary', 'url': EmailService.booking_url(booking)},
    )
    return EmailService.send(
        'travel_reminder', booking.user.email,
        EmailService.reminder_subject(booking, days_left), ctx,
    )


@shared_task
def prepare_travel_reminders():
    """Celery-beat entry point for the daily reminder sweep."""
    from .reminders import TravelReminderService
    return TravelReminderService.prepare_reminders()
