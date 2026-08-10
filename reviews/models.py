from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reviews'
    )
    booking = models.OneToOneField(
        'bookings.Booking', on_delete=models.CASCADE,
        related_name='reviews'
    )
    hotel = models.ForeignKey(
        'hotels.Hotel', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviews'
    )
    package = models.ForeignKey(
        'packages.TravelPackage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    review_text = models.TextField()
    helpful_count = models.PositiveIntegerField(default=0)
    is_verified_booking = models.BooleanField(default=True, editable=False)
    is_approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hotel', 'is_approved']),
            models.Index(fields=['package', 'is_approved']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.rating}/5 — {self.title[:50]}'

    @property
    def content_type(self):
        if self.hotel_id:
            return 'Hotel'
        if self.package_id:
            return 'Package'
        return 'Unknown'

    @property
    def content_object(self):
        return self.hotel or self.package

    @property
    def item_name(self):
        obj = self.content_object
        if hasattr(obj, 'title'):
            return obj.title
        if hasattr(obj, 'name'):
            return obj.name
        return 'Deleted'

    def helpful_users(self):
        return self.helpful_votes.values_list('user_id', flat=True)


class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='reviews/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Image for review {self.review.id}'


class HelpfulVote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='helpful_votes'
    )
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE,
        related_name='helpful_votes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'review']

    def __str__(self):
        return f'{self.user.username} → review {self.review.id}'
