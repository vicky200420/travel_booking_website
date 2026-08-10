from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Booking(models.Model):
    class BookingType(models.TextChoices):
        FLIGHT = 'Flight', 'Flight'
        HOTEL = 'Hotel', 'Hotel'
        PACKAGE = 'Package', 'Package'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CANCELLED = 'Cancelled', 'Cancelled'
        COMPLETED = 'Completed', 'Completed'
        REFUNDED = 'Refunded', 'Refunded'

    class PaymentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        FAILED = 'Failed', 'Failed'
        REFUNDED = 'Refunded', 'Refunded'

    booking_id = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='bookings'
    )
    booking_type = models.CharField(
        max_length=10, choices=BookingType.choices, db_index=True
    )

    flight = models.ForeignKey(
        'flights.Flight', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    hotel = models.ForeignKey(
        'hotels.Hotel', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    package = models.ForeignKey(
        'packages.TravelPackage', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    booking_date = models.DateTimeField(auto_now_add=True)
    travel_start_date = models.DateField()
    travel_end_date = models.DateField()

    adults = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    children = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    infants = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    total_travelers = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30)
    special_requests = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING, db_index=True
    )

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    taxes = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    service_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking_type']),
            models.Index(fields=['travel_start_date']),
        ]

    def __str__(self):
        return self.booking_id

    @property
    def related_item(self):
        if self.booking_type == 'Flight':
            return self.flight
        if self.booking_type == 'Hotel':
            return self.hotel
        if self.booking_type == 'Package':
            return self.package
        return None

    @property
    def destination_display(self):
        item = self.related_item
        if not item:
            return 'N/A'
        if self.booking_type == 'Flight':
            return f'{item.departure_city} → {item.destination_city}'
        if self.booking_type == 'Hotel':
            return f'{item.city}, {item.country}'
        if self.booking_type == 'Package':
            return f'{item.destination}, {item.country}'
        return 'N/A'

    @property
    def title_display(self):
        item = self.related_item
        if not item:
            return 'Deleted'
        if self.booking_type == 'Flight':
            return f'{item.airline_name} {item.flight_number}'
        if self.booking_type == 'Hotel':
            return item.name
        if self.booking_type == 'Package':
            return item.title
        return 'N/A'

    @property
    def can_cancel(self):
        if self.status in ['Cancelled', 'Refunded', 'Completed']:
            return False
        return self.travel_start_date > timezone.now().date()

    @property
    def status_color(self):
        colors = {
            'Pending': 'warning',
            'Confirmed': 'success',
            'Cancelled': 'danger',
            'Completed': 'info',
            'Refunded': 'secondary',
        }
        return colors.get(self.status, 'dark')

    @property
    def payment_color(self):
        colors = {
            'Pending': 'warning',
            'Paid': 'success',
            'Failed': 'danger',
            'Refunded': 'info',
        }
        return colors.get(self.payment_status, 'dark')
