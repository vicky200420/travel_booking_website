from django import template
from django.db.models import Count

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.inclusion_tag('reviews/components/reviews_section.html', takes_context=True)
def render_reviews(context, obj, obj_type):
    from bookings.models import Booking
    from reviews.models import Review
    request = context['request']

    reviews = Review.objects.filter(
        **{obj_type: obj, 'is_approved': True}
    ).select_related('user').prefetch_related('images').order_by('-created_at')

    stats = {}
    for i in range(1, 6):
        stats[i] = 0
    for r in reviews.values('rating').annotate(count=Count('id')):
        stats[r['rating']] = r['count']

    can_review = False
    existing_review_id = None
    review_booking_id = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(
            user=request.user,
            **{obj_type: obj}
        ).first()
        if user_review:
            existing_review_id = user_review.id
        else:
            booking_filter = {obj_type: obj, 'user': request.user, 'status': 'Completed'}
            completed_booking = Booking.objects.filter(**booking_filter).first()
            if completed_booking:
                can_review = True
                review_booking_id = completed_booking.booking_id

    reviews_count = reviews.count()
    reviews = list(reviews[:5])
    helpful_review_ids = _helpful_review_ids(request, reviews)

    return {
        'item': obj,
        'item_type': obj_type,
        'reviews': reviews,
        'reviews_json_url': f'/reviews/{obj_type}/{obj.id}/',
        'total_reviews': reviews_count,
        'avg_rating': obj.average_rating,
        'stats': stats,
        'user': request.user,
        'can_review': can_review,
        'existing_review_id': existing_review_id,
        'review_booking_id': review_booking_id,
        'helpful_review_ids': helpful_review_ids,
    }


def _helpful_review_ids(request, reviews):
    """Set of review ids the current user voted 'helpful' on (0 queries when empty)."""
    if not request.user.is_authenticated or not reviews:
        return set()
    from reviews.models import HelpfulVote
    return set(
        HelpfulVote.objects.filter(
            user=request.user,
            review_id__in=[r.id for r in reviews],
        ).values_list('review_id', flat=True)
    )
