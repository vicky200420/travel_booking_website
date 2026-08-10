"""Notification & Communication — data model."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """A single in-app / email-eligible notification for a user."""

    class Type(models.TextChoices):
        SUCCESS = 'success', 'Success'
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        BOOKING = 'booking', 'Booking'
        PAYMENT = 'payment', 'Payment'
        PROMOTION = 'promotion', 'Promotion'
        REMINDER = 'reminder', 'Reminder'

    class Audience(models.TextChoices):
        ALL = 'all', 'All Users'
        CUSTOMER = 'customer', 'Customers'
        AGENT = 'agent', 'Agents'

    # Shared style tokens for the front-end (type -> icon/colour).
    TYPE_ICONS = {
        Type.SUCCESS: 'bi-check-circle-fill',
        Type.INFO: 'bi-info-circle-fill',
        Type.WARNING: 'bi-exclamation-triangle-fill',
        Type.ERROR: 'bi-x-circle-fill',
        Type.BOOKING: 'bi-journal-bookmark-fill',
        Type.PAYMENT: 'bi-credit-card-fill',
        Type.PROMOTION: 'bi-megaphone-fill',
        Type.REMINDER: 'bi-alarm-fill',
    }

    TYPE_COLORS = {
        Type.SUCCESS: '#22C55E',
        Type.INFO: '#3B82F6',
        Type.WARNING: '#F59E0B',
        Type.ERROR: '#EF4444',
        Type.BOOKING: '#8B5CF6',
        Type.PAYMENT: '#06B6D4',
        Type.PROMOTION: '#EC4899',
        Type.REMINDER: '#F97316',
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    type = models.CharField(
        max_length=20, choices=Type.choices,
        default=Type.INFO, db_index=True
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    action_url = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    is_broadcast = models.BooleanField(default=False, db_index=True)
    audience = models.CharField(
        max_length=20, choices=Audience.choices,
        default=Audience.ALL
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.user.username} — {self.title[:60]}'

    # ------------------------------------------------------------ helpers

    @property
    def effective_icon(self):
        return self.icon or self.TYPE_ICONS.get(self.type, self.TYPE_ICONS[self.Type.INFO])

    @property
    def color(self):
        return self.TYPE_COLORS.get(self.type, '#64748B')

    def mark_read(self):
        """Mark this notification as read (idempotent)."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
