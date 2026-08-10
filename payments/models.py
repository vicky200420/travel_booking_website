import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    class Gateway(models.TextChoices):
        RAZORPAY = 'razorpay', 'Razorpay'
        STRIPE = 'stripe', 'Stripe'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        SUCCESS = 'Success', 'Success'
        FAILED = 'Failed', 'Failed'
        REFUNDED = 'Refunded', 'Refunded'

    booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.CASCADE,
        related_name='payments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='payments'
    )
    transaction_id = models.CharField(
        max_length=100, unique=True, blank=True
    )
    order_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    payment_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='Gateway-issued payment ID (e.g. Razorpay pay_xxx).'
    )
    refund_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='Gateway-issued refund ID after a refund is processed.'
    )
    gateway = models.CharField(
        max_length=20, choices=Gateway.choices,
        default=Gateway.RAZORPAY, db_index=True
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='INR')
    payment_method = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True
    )
    gateway_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['order_id']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.transaction_id or "Pending"} — {self.status}'

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f'TXN{uuid.uuid4().hex[:12].upper()}'
        # NULL (not '') is required so multiple pending payments can coexist
        # under the unique constraints on order_id / payment_id / refund_id.
        if not self.order_id:
            self.order_id = None
        if not self.payment_id:
            self.payment_id = None
        if not self.refund_id:
            self.refund_id = None
        super().save(*args, **kwargs)

    @property
    def is_success(self):
        return self.status == self.Status.SUCCESS

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def status_color(self):
        colors = {
            'Pending': 'warning',
            'Success': 'success',
            'Failed': 'danger',
            'Refunded': 'info',
        }
        return colors.get(self.status, 'dark')
