from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.TextChoices):
    ADVENTURE = 'Adventure', 'Adventure'
    FAMILY = 'Family', 'Family'
    HONEYMOON = 'Honeymoon', 'Honeymoon'
    LUXURY = 'Luxury', 'Luxury'
    SOLO = 'Solo', 'Solo'
    GROUP = 'Group', 'Group'
    WILDLIFE = 'Wildlife', 'Wildlife'
    BEACH = 'Beach', 'Beach'
    HILL_STATION = 'Hill Station', 'Hill Station'
    WELLNESS = 'Wellness', 'Wellness'


class DifficultyLevel(models.TextChoices):
    EASY = 'Easy', 'Easy'
    MODERATE = 'Moderate', 'Moderate'
    HARD = 'Hard', 'Hard'


class TravelPackage(models.Model):
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=350, unique=True, blank=True)
    cover_image = models.ImageField(upload_to='packages/', blank=True, null=True)
    destination = models.CharField(max_length=200, db_index=True)
    country = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, blank=True)
    duration_days = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    duration_nights = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    category = models.CharField(
        max_length=30, choices=Category.choices, db_index=True
    )
    description = models.TextField()
    itinerary = models.JSONField(default=list, blank=True)
    price = models.DecimalField(
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
    max_travelers = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], default=20
    )
    difficulty_level = models.CharField(
        max_length=20, choices=DifficultyLevel.choices,
        default=DifficultyLevel.EASY
    )
    best_travel_season = models.CharField(max_length=200, blank=True)
    inclusions = models.JSONField(default=list, blank=True)
    exclusions = models.JSONField(default=list, blank=True)
    highlights = models.JSONField(default=list, blank=True)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False, db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-average_rating', 'title']
        indexes = [
            models.Index(fields=['destination', 'country']),
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['active', 'featured']),
            models.Index(fields=['duration_days']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            self.slug = base
            idx = 1
            while TravelPackage.objects.filter(slug=self.slug).exists():
                self.slug = f"{base}-{idx}"
                idx += 1
        if self.discount_percentage > 0:
            self.discounted_price = self.price * (1 - self.discount_percentage / 100)
        else:
            self.discounted_price = self.price
        super().save(*args, **kwargs)

    def has_discount(self):
        return self.discount_percentage > 0

    def display_price(self):
        if self.has_discount():
            return self.discounted_price
        return self.price

    @property
    def duration_display(self):
        parts = []
        if self.duration_days:
            parts.append(f"{self.duration_days} Day{'s' if self.duration_days > 1 else ''}")
        if self.duration_nights:
            parts.append(f"{self.duration_nights} Night{'s' if self.duration_nights > 1 else ''}")
        return " / ".join(parts)

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
        return google_maps_place_url(*self.coordinates, name=self.destination) if self.has_coordinates else None

    @property
    def directions_url(self):
        from maps.utils import google_maps_directions_url
        return google_maps_directions_url(*self.coordinates) if self.has_coordinates else None

    def get_absolute_url(self):
        return f"/packages/{self.slug}/"


class PackageImage(models.Model):
    package = models.ForeignKey(TravelPackage, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='packages/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"{self.package.title} — {self.caption or 'Image'}"
