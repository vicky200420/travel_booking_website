"""Payments — model signals.

Kept as a safety net only: the authoritative confirmation path lives in
:mod:`payments.services`. This receiver guarantees that a booking can never
remain ``Pending`` once its payment is recorded as ``Success`` — regardless of
how the status change happened (verified flow, webhook, admin action, test).
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Payment

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Payment)
def _track_payment_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Payment.objects.only('status').get(pk=instance.pk)
            instance._old_status = previous.status
        except Payment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Payment)
def _confirm_booking_on_success(sender, instance, created, **kwargs):
    """Idempotently confirm the booking once a payment succeeds.

    The email/notification side-effects are handled by the notifications app
    signals; this receiver only reconciles the booking state.
    """
    if created:
        return

    old = getattr(instance, '_old_status', None)
    if instance.status != Payment.Status.SUCCESS:
        return
    if old == Payment.Status.SUCCESS:
        return

    booking = instance.booking

    def _confirm():
        if booking.status != 'Pending':
            return
        from bookings.services import BookingService
        try:
            BookingService.confirm_booking(booking)
        except Exception:
            logger.exception('Safety-net booking confirmation failed for %s',
                             booking.booking_id)

    transaction.on_commit(_confirm)