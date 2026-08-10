from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Flight(models.Model):
    class FlightType(models.TextChoices):
        ONE_WAY = 'one_way', 'One Way'
        ROUND_TRIP = 'round_trip', 'Round Trip'

    class CabinClass(models.TextChoices):
        ECONOMY = 'economy', 'Economy'
        PREMIUM_ECONOMY = 'premium_economy', 'Premium Economy'
        BUSINESS = 'business', 'Business'
        FIRST = 'first', 'First'

    class FlightStatus(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        DELAYED = 'delayed', 'Delayed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    airline_name = models.CharField(max_length=200)
    airline_logo = models.ImageField(upload_to='airlines/', blank=True, null=True)
    flight_number = models.CharField(max_length=20, unique=True, db_index=True)
    departure_airport = models.CharField(max_length=200)
    arrival_airport = models.CharField(max_length=200)
    departure_city = models.CharField(max_length=100, db_index=True)
    destination_city = models.CharField(max_length=100, db_index=True)
    departure_date = models.DateField(db_index=True)
    departure_time = models.TimeField()
    arrival_date = models.DateField()
    arrival_time = models.TimeField()
    flight_duration = models.DurationField()
    flight_type = models.CharField(max_length=20, choices=FlightType.choices, default=FlightType.ONE_WAY)
    cabin_class = models.CharField(max_length=20, choices=CabinClass.choices, default=CabinClass.ECONOMY)
    total_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    available_seats = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    baggage_allowance = models.CharField(max_length=200, blank=True)
    refundable = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=FlightStatus.choices, default=FlightStatus.SCHEDULED, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-departure_date', 'departure_time']
        indexes = [
            models.Index(fields=['departure_city', 'destination_city']),
            models.Index(fields=['departure_date', 'status']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.airline_name} {self.flight_number} — {self.departure_city} → {self.destination_city}"

    def save(self, *args, **kwargs):
        if self.discount_percentage > 0:
            self.discounted_price = self.price * (1 - self.discount_percentage / 100)
        else:
            self.discounted_price = self.price
        super().save(*args, **kwargs)

    def has_discount(self):
        return self.discount_percentage > 0
