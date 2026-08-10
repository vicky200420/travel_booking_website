from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Booking


@receiver(pre_save, sender=Booking)
def track_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Booking.objects.get(pk=instance.pk).status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def handle_status_change(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_old_status'):
        if instance._old_status != 'Cancelled' and instance.status == 'Cancelled':
            pass
