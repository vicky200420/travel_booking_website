"""Home + infrastructure tests: SEO, health, sitemap, error handlers, security."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from flights.models import Flight
from hotels.models import Hotel
from notifications.models import Notification
from notifications.services import NotificationService
from reviews.models import HelpfulVote, Review

User = get_user_model()


class HomePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='seo', email='seo@example.com', password='TestPass123!'
        )

    def test_home_renders_seo_meta(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('meta name="description"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('id="main-content"', html)
        self.assertIn('class="skip-link"', html)

    def test_home_has_manifest_and_icons(self):
        response = self.client.get(reverse('home'))
        html = response.content.decode()
        self.assertIn('rel="manifest"', html)
        self.assertIn('theme-color', html)

    def test_robots_txt(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'].split(';')[0], 'text/plain')
        self.assertIn('sitemap.xml', response.content.decode())

    def test_health_endpoint(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_sitemap_lists_catalogue(self):
        Hotel.objects.create(
            name='Sitemap Hotel', slug='sitemap-hotel', city='Goa',
            country='India', address='1 Beach Road',
            price_per_night=Decimal('2000'), total_rooms=10, available_rooms=5,
        )
        Flight.objects.create(
            flight_number='SMOKE001', airline_name='Test Air',
            departure_airport='DEL', arrival_airport='GOA',
            departure_city='Delhi', destination_city='Goa',
            departure_date='2026-09-01', departure_time='09:00',
            arrival_date='2026-09-01', arrival_time='11:00',
            flight_duration=timedelta(hours=2), total_seats=100,
            available_seats=80, price=Decimal('3500'),
        )
        response = self.client.get(reverse('django.contrib.sitemaps.views.sitemap'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('hotels/', content)
        self.assertIn('flights/', content)

    def test_404_uses_custom_handler(self):
        response = self.client.get('/definitely-not-a-real-page/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Page not found', response.content.decode())

    def test_api_schema_served(self):
        response = self.client.get(reverse('api_schema'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('openapi', response.content.decode())


class NotificationCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bell', email='bell@example.com', password='TestPass123!'
        )
        cache.clear()

    def test_summary_is_cached_and_invalidated(self):
        NotificationService.create(self.user, 'One')
        summary = NotificationService.summary(self.user)
        self.assertEqual(summary['unread'], 1)
        self.assertEqual(len(summary['recent']), 1)

        NotificationService.create(self.user, 'Two')
        summary = NotificationService.summary(self.user)
        self.assertEqual(summary['unread'], 2)
        self.assertEqual(len(summary['recent']), 2)

        notification = Notification.objects.filter(user=self.user).first()
        NotificationService.mark_read(notification)
        self.assertEqual(NotificationService.unread_count(self.user), 1)

    def test_context_processor_injects_cached_summary(self):
        NotificationService.create(self.user, 'Hello bell')
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hello bell', response.content.decode())


class ReviewHelpfulIdsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='helper', email='helper@example.com', password='TestPass123!'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='TestPass123!'
        )
        self.hotel = Hotel.objects.create(
            name='Helpful Hotel', slug='helpful-hotel', city='Delhi',
            country='India', address='1 MG Road',
            price_per_night=Decimal('3000'), total_rooms=10, available_rooms=5,
        )

    def test_helpful_ids_are_scoped_to_user(self):
        from bookings.models import Booking
        booking = Booking.objects.create(
            booking_id='TB123456', user=self.user, booking_type='Hotel',
            hotel=self.hotel, status='Completed', contact_name='Tester',
            contact_email='t@example.com', contact_phone='123',
            travel_start_date='2026-01-10', travel_end_date='2026-01-12',
            base_price=Decimal('6000'), taxes=Decimal('600'),
            total_travelers=2, grand_total=Decimal('6600'),
        )
        review = Review.objects.create(
            user=self.user, booking=booking, hotel=self.hotel,
            rating=5, title='Great', review_text='Lovely stay',
        )
        HelpfulVote.objects.create(user=self.user, review=review)
        HelpfulVote.objects.create(user=self.other, review=review)

        from django.test import RequestFactory
        from reviews.views import _helpful_review_ids
        request = RequestFactory().get('/')
        request.user = self.user

        self.assertEqual(_helpful_review_ids(request, [review]), {review.id})


class PaymentWebhookTests(TestCase):
    def test_webhook_rejected_when_secret_missing(self):
        from payments.gateway import RazorpayGateway, StripeGateway

        class FakeBody:
            META = {}

            def __init__(self):
                self.body = b'{"event": "payment.captured"}'

        for gateway in (RazorpayGateway(), StripeGateway()):
            with self.subTest(gateway=type(gateway).__name__):
                self.assertIsNone(gateway.process_webhook(FakeBody()))
