from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Hotel(models.Model):
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, unique=True, blank=True)
    image = models.ImageField(upload_to='hotels/', blank=True, null=True)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, db_index=True)
    address = models.TextField()
    description = models.TextField(blank=True)
    star_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=4
    )
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discounted_price = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False, default=0
    )
    total_rooms = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    available_rooms = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    check_in_time = models.TimeField(default='14:00')
    check_out_time = models.TimeField(default='11:00')

    wifi = models.BooleanField(default=False)
    pool = models.BooleanField(default=False)
    parking = models.BooleanField(default=False)
    spa = models.BooleanField(default=False)
    gym = models.BooleanField(default=False)
    restaurant = models.BooleanField(default=False)
    ac = models.BooleanField(default=False)
    breakfast = models.BooleanField(default=False)
    pet_friendly = models.BooleanField(default=False)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    featured = models.BooleanField(default=False, db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-average_rating', 'name']
        indexes = [
            models.Index(fields=['city', 'country']),
            models.Index(fields=['star_rating']),
            models.Index(fields=['price_per_night']),
            models.Index(fields=['active', 'featured']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.discount_percentage > 0:
            self.discounted_price = self.price_per_night * (1 - self.discount_percentage / 100)
        else:
            self.discounted_price = self.price_per_night
        super().save(*args, **kwargs)

    def has_discount(self):
        return self.discount_percentage > 0

    def amenities_list(self):
        amenities = []
        if self.wifi:
            amenities.append('WiFi')
        if self.pool:
            amenities.append('Pool')
        if self.parking:
            amenities.append('Parking')
        if self.spa:
            amenities.append('Spa')
        if self.gym:
            amenities.append('Gym')
        if self.restaurant:
            amenities.append('Restaurant')
        if self.ac:
            amenities.append('AC')
        if self.breakfast:
            amenities.append('Breakfast')
        if self.pet_friendly:
            amenities.append('Pet Friendly')
        return amenities

    def display_price(self):
        if self.has_discount():
            return self.discounted_price
        return self.price_per_night

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def coordinates(self):
        if not self.has_coordinates:
            return None
        return (float(self.latitude), float(self.longitude))

    @property
    def google_maps_url(self):
        from maps.utils import google_maps_place_url
        return google_maps_place_url(*self.coordinates, name=self.name) if self.has_coordinates else None

    @property
    def directions_url(self):
        from maps.utils import google_maps_directions_url
        return google_maps_directions_url(*self.coordinates) if self.has_coordinates else None

    def get_absolute_url(self):
        return f"/hotels/{self.slug}/"


class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='hotels/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"{self.hotel.name} — {self.caption or 'Image'}"
