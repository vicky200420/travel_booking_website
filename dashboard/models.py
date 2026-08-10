"""Dashboard — data models.

Personal travel hub: wishlist items (generic to hotels / flights / packages)
and per-user preferences that the dashboard settings page manages.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class WishlistItem(models.Model):
    """A saved hotel / flight / package for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_user_wishlist_item',
            )
        ]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.content_object or self.content_type}'

    @property
    def content_type_label(self):
        if self.content_type.model == 'travelpackage':
            return 'Package'
        if self.content_type.model == 'flight':
            return 'Flight'
        if self.content_type.model == 'hotel':
            return 'Hotel'
        return self.content_type.model.title()

    @property
    def title(self):
        obj = self.content_object
        if not obj:
            return 'Removed item'
        return getattr(obj, 'title', None) or getattr(obj, 'name', '')

    @property
    def detail_url(self):
        obj = self.content_object
        if not obj:
            return None
        if self.content_type.model == 'flight':
            return f'/flights/{obj.id}/'
        return obj.get_absolute_url()

    @property
    def cover_image(self):
        obj = self.content_object
        if not obj:
            return None
        return getattr(obj, 'cover_image', None) or getattr(obj, 'image', None)

    @property
    def price_display(self):
        obj = self.content_object
        if not obj:
            return None
        return getattr(obj, 'display_price', lambda: None)()

    @property
    def location_display(self):
        obj = self.content_object
        if not obj:
            return ''
        if self.content_type.model == 'hotel':
            return f'{getattr(obj, "city", "")}, {getattr(obj, "country", "")}'
        if self.content_type.model == 'travelpackage':
            return f'{getattr(obj, "destination", "")}, {getattr(obj, "country", "")}'
        if self.content_type.model == 'flight':
            return f'{getattr(obj, "departure_city", "")} → {getattr(obj, "destination_city", "")}'
        return ''


class UserProfile(models.Model):
    """One-to-one preferences/profile extras for the dashboard settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='dashboard_profile'
    )

    travel_preferences = models.JSONField(default=dict, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    DEFAULT_TRAVEL_PREFS = {
        'budget_range': 'mid',
        'seat_preference': '',
        'meal_preference': '',
        'hotel_amenities': [],
        'airline_preferences': '',
        'frequent_flyer': '',
        'special_needs': '',
    }

    DEFAULT_NOTIF_PREFS = {
        'email_notifications': True,
        'push_notifications': True,
        'booking_updates': True,
        'payment_alerts': True,
        'trip_reminders': True,
        'promotions': False,
    }

    def __str__(self):
        return f'Profile for {self.user.username}'

    def ensure_defaults(self):
        merged = {**self.DEFAULT_TRAVEL_PREFS, **self.travel_preferences}
        self.travel_preferences = {
            k: v for k, v in merged.items() if k in self.DEFAULT_TRAVEL_PREFS
        }
        merged_n = {**self.DEFAULT_NOTIF_PREFS, **self.notification_preferences}
        self.notification_preferences = {
            k: v for k, v in merged_n.items() if k in self.DEFAULT_NOTIF_PREFS
        }
        return self
