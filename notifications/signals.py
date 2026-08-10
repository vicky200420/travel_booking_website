"""Notification & Communication — automatic event signals.

Receivers turn domain events into in-app notifications (+ emails). Each
receiver stays thin and delegates to :class:`NotificationService`; side effects
are deferred with ``transaction.on_commit`` so nothing is persisted if the
surrounding transaction rolls back.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .services import NotificationService

User = get_user_model()


# ---------------------------------------------------------------- accounts

@receiver(pre_save, sender=User)
def _track_user_state(sender, instance, **kwargs):
    instance._notif_was_created = instance.pk is None


@receiver(post_save, sender=User)
def on_user_registered(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: NotificationService.registration_success(instance))
    transaction.on_commit(lambda: NotificationService.email_verification(instance))


# ---------------------------------------------------------------- bookings

@receiver(pre_save, sender='bookings.Booking')
def _track_booking_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            from bookings.models import Booking
            instance._notif_old_status = Booking.objects.get(pk=instance.pk).status
        except Booking.DoesNotExist:
            instance._notif_old_status = None
    else:
        instance._notif_old_status = None


@receiver(post_save, sender='bookings.Booking')
def on_booking_event(sender, instance, created, **kwargs):
    from bookings.models import Booking

    if created:
        transaction.on_commit(lambda b=instance: NotificationService.booking_created(b))
        return

    old = getattr(instance, '_notif_old_status', None)
    new = instance.status
    if old == new:
        return

    if old != Booking.Status.CANCELLED and new == Booking.Status.CANCELLED:
        transaction.on_commit(lambda b=instance: NotificationService.booking_cancelled(b))
    elif old != Booking.Status.CONFIRMED and new == Booking.Status.CONFIRMED:
        confirmed_by_payment = getattr(instance, '_confirmed_by_payment', False)
        transaction.on_commit(
            lambda b=instance, e=confirmed_by_payment: NotificationService.booking_confirmed(b, send_email=not e)
        )
    else:
        transaction.on_commit(lambda b=instance: NotificationService.booking_status_update(b))


# ---------------------------------------------------------------- payments

@receiver(pre_save, sender='payments.Payment')
def _track_payment_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            from payments.models import Payment
            instance._notif_old_status = Payment.objects.get(pk=instance.pk).status
        except Payment.DoesNotExist:
            instance._notif_old_status = None
    else:
        instance._notif_old_status = None


@receiver(post_save, sender='payments.Payment')
def on_payment_event(sender, instance, created, **kwargs):
    from payments.models import Payment

    if created:
        return

    old = getattr(instance, '_notif_old_status', None)
    new = instance.status
    if old == new:
        return

    if new == Payment.Status.SUCCESS:
        transaction.on_commit(lambda p=instance: NotificationService.payment_success(p))
    elif new == Payment.Status.FAILED:
        transaction.on_commit(lambda p=instance: NotificationService.payment_failed(p))
    elif new == Payment.Status.REFUNDED:
        transaction.on_commit(lambda p=instance: NotificationService.refund_processed(p))


# ---------------------------------------------------------------- reviews

@receiver(post_save, sender='reviews.Review')
def on_review_submitted(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda r=instance: NotificationService.review_submitted(r))
