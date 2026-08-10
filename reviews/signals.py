from django.db import transaction
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


def _update_hotel_ratings(hotel_id):
    from hotels.models import Hotel

    from .models import Review
    agg = Review.objects.filter(
        hotel_id=hotel_id, is_approved=True
    ).aggregate(
        avg=Avg('rating'), cnt=Count('id')
    )
    Hotel.objects.filter(id=hotel_id).update(
        average_rating=round(agg['avg'] or 0, 1),
        total_reviews=agg['cnt'] or 0,
    )


def _update_package_ratings(package_id):
    from packages.models import TravelPackage

    from .models import Review
    agg = Review.objects.filter(
        package_id=package_id, is_approved=True
    ).aggregate(
        avg=Avg('rating'), cnt=Count('id')
    )
    TravelPackage.objects.filter(id=package_id).update(
        average_rating=round(agg['avg'] or 0, 1),
        total_reviews=agg['cnt'] or 0,
    )


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda: _sync_ratings(instance))


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    transaction.on_commit(lambda: _sync_ratings(instance))


def _sync_ratings(instance):
    if instance.hotel_id:
        _update_hotel_ratings(instance.hotel_id)
    if instance.package_id:
        _update_package_ratings(instance.package_id)
