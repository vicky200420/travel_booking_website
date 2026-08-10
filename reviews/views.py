from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView, View

from bookings.models import Booking
from hotels.models import Hotel
from packages.models import TravelPackage

from .forms import ReviewForm
from .models import HelpfulVote, Review, ReviewImage


def _helpful_review_ids(request, reviews):
    """Set of review ids the current user voted 'helpful' on (0 queries when empty)."""
    if not request.user.is_authenticated or not reviews:
        return set()
    return set(
        HelpfulVote.objects.filter(
            user=request.user,
            review_id__in=[r.id for r in reviews],
        ).values_list('review_id', flat=True)
    )


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        booking_id = request.GET.get('booking')
        if not booking_id:
            messages.error(request, 'No booking specified.')
            return redirect('my_bookings')

        self.booking = get_object_or_404(
            Booking, booking_id=booking_id, user=request.user
        )

        if self.booking.status != 'Completed':
            messages.error(request, 'You can only review completed bookings.')
            return redirect('booking_detail', booking_id=booking_id)

        if Review.objects.filter(booking=self.booking).exists():
            messages.info(request, 'You have already reviewed this booking.')
            return redirect('booking_detail', booking_id=booking_id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.booking
        context['product'] = self.booking.related_item
        context['booking_type'] = self.booking.booking_type
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.booking = self.booking
        form.instance.is_verified_booking = True

        item = self.booking.related_item
        if self.booking.booking_type == 'Hotel':
            form.instance.hotel = item
        elif self.booking.booking_type == 'Package':
            form.instance.package = item

        response = super().form_valid(form)

        for img in self.request.FILES.getlist('images'):
            ReviewImage.objects.create(review=self.object, image=img)

        messages.success(self.request, 'Your review has been submitted!')
        return response

    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'booking_id': self.booking.booking_id})


class ReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/review_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.object.booking
        context['product'] = self.object.content_object
        context['booking_type'] = self.object.booking.booking_type
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.images.all().delete()
        for img in self.request.FILES.getlist('images'):
            ReviewImage.objects.create(review=self.object, image=img)
        messages.success(self.request, 'Your review has been updated!')
        return response

    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'booking_id': self.object.booking.booking_id})


class ReviewDeleteView(LoginRequiredMixin, DeleteView):
    model = Review
    pk_url_kwarg = 'pk'
    template_name = 'reviews/review_confirm_delete.html'

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user)

    def get_success_url(self):
        messages.success(self.request, 'Your review has been deleted.')
        return reverse_lazy('my_reviews')


class MyReviewsView(LoginRequiredMixin, ListView):
    model = Review
    template_name = 'reviews/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 10

    def get_queryset(self):
        return Review.objects.filter(
            user=self.request.user
        ).select_related('hotel', 'package', 'booking').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_reviews'] = self.get_queryset().count()
        context['helpful_review_ids'] = _helpful_review_ids(self.request, context['reviews'])
        return context


class HotelReviewsView(TemplateView):
    template_name = 'reviews/hotel_reviews_partial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = get_object_or_404(Hotel, id=self.kwargs['hotel_id'])
        reviews = Review.objects.filter(
            hotel=hotel, is_approved=True
        ).select_related('user').prefetch_related('images').order_by('-created_at')

        rating_stats = reviews.values('rating').annotate(
            count=Count('id')
        ).order_by('-rating')

        stats_dict = {i: 0 for i in range(1, 6)}
        for s in rating_stats:
            stats_dict[s['rating']] = s['count']

        context['hotel'] = hotel
        context['reviews'] = reviews
        context['stats'] = stats_dict
        context['total_reviews'] = reviews.count()
        context['helpful_review_ids'] = _helpful_review_ids(self.request, reviews)
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string('reviews/components/review_card.html', context, self.request)
            return JsonResponse({
                'html': html,
                'total': context['total_reviews'],
                'avg': float(context['hotel'].average_rating),
            })
        return super().render_to_response(context, **response_kwargs)


class PackageReviewsView(TemplateView):
    template_name = 'reviews/package_reviews_partial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        package = get_object_or_404(TravelPackage, id=self.kwargs['package_id'])
        reviews = Review.objects.filter(
            package=package, is_approved=True
        ).select_related('user').prefetch_related('images').order_by('-created_at')

        rating_stats = reviews.values('rating').annotate(
            count=Count('id')
        ).order_by('-rating')

        stats_dict = {i: 0 for i in range(1, 6)}
        for s in rating_stats:
            stats_dict[s['rating']] = s['count']

        context['package'] = package
        context['reviews'] = reviews
        context['stats'] = stats_dict
        context['total_reviews'] = reviews.count()
        context['helpful_review_ids'] = _helpful_review_ids(self.request, reviews)
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            html = render_to_string('reviews/components/review_card.html', context, self.request)
            return JsonResponse({
                'html': html,
                'total': context['total_reviews'],
                'avg': float(context['package'].average_rating),
            })
        return super().render_to_response(context, **response_kwargs)


class HelpfulToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(Review, id=pk, is_approved=True)
        vote, created = HelpfulVote.objects.get_or_create(
            user=request.user, review=review
        )

        if not created:
            vote.delete()
            review.helpful_count = HelpfulVote.objects.filter(review=review).count()
            review.save(update_fields=['helpful_count'])
            return JsonResponse({'helpful': False, 'count': review.helpful_count})

        review.helpful_count = HelpfulVote.objects.filter(review=review).count()
        review.save(update_fields=['helpful_count'])
        return JsonResponse({'helpful': True, 'count': review.helpful_count})
