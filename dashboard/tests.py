"""Dashboard — tests: auth, ownership, wishlist, settings, invoice."""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from bookings.services import BookingService
from flights.models import Flight
from hotels.models import Hotel
from notifications.models import Notification
from packages.models import TravelPackage
from payments.models import Payment
from reviews.models import Review

from .models import UserProfile, WishlistItem
from .services import DashboardService

User = get_user_model()


_hotel_seq = 0


def _make_hotel(name='Dashboard Hotel', price='2500', active=True):
    global _hotel_seq
    _hotel_seq += 1
    name = f'{name} {_hotel_seq}'
    return Hotel.objects.create(
        name=name, slug=name.lower().replace(' ', '-'),
        city='Bali', country='Indonesia', address='1 Beach Road',
        price_per_night=Decimal(price), total_rooms=50, available_rooms=40,
        active=active,
    )


def _make_package(title='Bali Escape'):
    return TravelPackage.objects.create(
        title=title, slug=title.lower().replace(' ', '-'),
        destination='Bali', country='Indonesia',
        duration_days=5, duration_nights=4, category='Beach',
        description='A great escape.', price=Decimal('40000'),
        max_travelers=10, active=True,
    )


def _make_flight():
    return Flight.objects.create(
        airline_name='Sky Airways', flight_number='SK101',
        departure_airport='DEL', arrival_airport='BAL',
        departure_city='Delhi', destination_city='Bali',
        departure_date=datetime.date.today() + datetime.timedelta(days=30),
        departure_time='10:00', arrival_date=datetime.date.today() + datetime.timedelta(days=30),
        arrival_time='14:00', flight_duration=datetime.timedelta(hours=4),
        total_seats=100, available_seats=90, price=Decimal('15000'),
    )


def _make_booking(user, product=None, status=Booking.Status.PENDING,
                  start_delta=14, end_delta=17, total='5000'):
    product = product or _make_hotel()
    booking = BookingService.create_booking(
        user=user, product=product, booking_type='Hotel',
        form_data={
            'adults': 1, 'children': 0, 'infants': 0,
            'travel_start': datetime.date.today() + datetime.timedelta(days=start_delta),
            'travel_end': datetime.date.today() + datetime.timedelta(days=end_delta),
            'contact_name': 'Alice', 'contact_email': 'alice@example.com',
            'contact_phone': '12345', 'special_requests': '',
        },
        price_data={
            'base_price': Decimal(total), 'tax': Decimal('100'),
            'discount': Decimal('0'), 'service_fee': Decimal('50'),
            'grand_total': Decimal(total),
        },
        nights=end_delta - start_delta, rooms=1,
    )
    if status != Booking.Status.PENDING:
        booking.status = status
        booking.save(update_fields=['status'])
    return booking


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )

    def test_dashboard_requires_login(self):
        for url in ('dashboard', 'dashboard_bookings', 'dashboard_payments',
                    'dashboard_wishlist', 'dashboard_reviews',
                    'dashboard_notifications', 'dashboard_settings'):
            response = self.client.get(reverse(url))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_all_pages_render_for_authenticated_user(self):
        self.client.login(username='alice', password='secret123')
        for url in ('dashboard', 'dashboard_bookings', 'dashboard_payments',
                    'dashboard_wishlist', 'dashboard_reviews',
                    'dashboard_notifications', 'dashboard_settings'):
            response = self.client.get(reverse(url))
            self.assertEqual(response.status_code, 200, url)

    def test_dashboard_uses_dashboard_chrome(self):
        self.client.login(username='alice', password='secret123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Welcome back,')
        self.assertContains(response, 'dash-sidebar')


class DashboardStatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )

    def test_stats_counts(self):
        _make_booking(self.user, status=Booking.Status.PENDING)
        _make_booking(self.user, status=Booking.Status.COMPLETED)
        b = _make_booking(self.user, status=Booking.Status.CANCELLED)
        b.status = Booking.Status.CANCELLED
        b.save()

        stats = DashboardService.stats(self.user)
        self.assertEqual(stats['total_trips'], 3)
        self.assertEqual(stats['upcoming_trips'], 1)
        self.assertEqual(stats['completed_trips'], 1)
        self.assertEqual(stats['cancelled_trips'], 1)

    def test_membership_and_points_from_spend(self):
        hotel = _make_hotel()
        booking = _make_booking(self.user, product=hotel, total='250000')
        Payment.objects.create(
            booking=booking, user=self.user, amount=Decimal('250000'),
            currency='INR', gateway='razorpay',
            status=Payment.Status.SUCCESS, paid_at=timezone.now(),
        )
        self.assertEqual(DashboardService.total_spent(self.user), Decimal('250000'))
        self.assertEqual(DashboardService.loyalty_points(self.user), 2500)
        self.assertEqual(DashboardService.membership_level(self.user)['label'], 'Gold')

    def test_upcoming_bookings_only_future(self):
        _make_booking(self.user, start_delta=5)
        _make_booking(self.user, start_delta=-5)  # past trip
        upcoming = DashboardService.upcoming_bookings(self.user)
        self.assertEqual(len(upcoming), 1)
        self.assertGreaterEqual(upcoming[0].travel_start_date, datetime.date.today())


class DashboardBookingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def test_only_own_bookings_listed(self):
        mine = _make_booking(self.user)
        _make_booking(self.other)
        response = self.client.get(reverse('dashboard_bookings'))
        self.assertContains(response, mine.booking_id)
        other = Booking.objects.filter(user=self.other).first()
        self.assertNotContains(response, other.booking_id)

    def test_search_by_booking_id(self):
        mine = _make_booking(self.user)
        response = self.client.get(reverse('dashboard_bookings'), {'q': mine.booking_id})
        self.assertContains(response, mine.booking_id)

    def test_status_filter(self):
        mine = _make_booking(self.user)
        response = self.client.get(reverse('dashboard_bookings'), {'status': 'Cancelled'})
        self.assertNotContains(response, mine.booking_id)


class DashboardPaymentsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def _pay(self, user, amount='2000', status=Payment.Status.SUCCESS):
        booking = _make_booking(user)
        return Payment.objects.create(
            booking=booking, user=user, amount=Decimal(amount),
            currency='INR', gateway='razorpay', status=status,
            order_id=f'order-{booking.booking_id}-{amount}',
            paid_at=timezone.now() if status == Payment.Status.SUCCESS else None,
        )

    def test_only_own_payments_listed(self):
        mine = self._pay(self.user)
        self._pay(self.other)
        response = self.client.get(reverse('dashboard_payments'))
        self.assertContains(response, mine.transaction_id)
        other = Payment.objects.filter(user=self.other).first()
        self.assertNotContains(response, other.transaction_id)

    def test_invoice_download_own_payment(self):
        payment = self._pay(self.user)
        response = self.client.get(reverse('dashboard_invoice', args=[payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertContains(response, 'INR 2000.00')

    def test_invoice_forbidden_for_other_user(self):
        payment = self._pay(self.other)
        response = self.client.get(reverse('dashboard_invoice', args=[payment.id]))
        self.assertEqual(response.status_code, 404)


class DashboardWishlistTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def test_toggle_add_and_remove(self):
        hotel = _make_hotel()
        url = reverse('dashboard_wishlist_toggle')
        response = self.client.post(url, {'model': 'hotel', 'object_id': hotel.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action'], 'added')
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)

        response = self.client.post(url, {'model': 'hotel', 'object_id': hotel.id})
        self.assertEqual(response.json()['action'], 'removed')
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 0)

    def test_toggle_rejects_unknown_model(self):
        response = self.client.post(
            reverse('dashboard_wishlist_toggle'),
            {'model': 'spaceship', 'object_id': 1},
        )
        self.assertEqual(response.status_code, 400)

    def test_wishlist_page_lists_only_own(self):
        hotel = _make_hotel()
        DashboardService.add_wishlist(self.user, 'hotel', hotel.id)
        other_hotel = _make_hotel('Other Hotel')
        DashboardService.add_wishlist(self.other, 'hotel', other_hotel.id)

        response = self.client.get(reverse('dashboard_wishlist'))
        self.assertContains(response, hotel.name)
        self.assertNotContains(response, other_hotel.name)

    def test_remove_post(self):
        hotel = _make_hotel()
        item, _ = DashboardService.add_wishlist(self.user, 'hotel', hotel.id)
        response = self.client.post(reverse('dashboard_wishlist_remove', args=[item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WishlistItem.objects.filter(id=item.id).exists())


class DashboardReviewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def test_only_own_reviews_listed(self):
        booking = _make_booking(self.user, status=Booking.Status.COMPLETED)
        Review.objects.create(
            user=self.user, booking=booking, hotel=booking.hotel,
            rating=5, title='Amazing', review_text='Loved it.',
        )
        other_booking = _make_booking(self.other, status=Booking.Status.COMPLETED)
        Review.objects.create(
            user=self.other, booking=other_booking, hotel=other_booking.hotel,
            rating=3, title='Meh', review_text='Okay.',
        )
        response = self.client.get(reverse('dashboard_reviews'))
        self.assertContains(response, 'Amazing')
        self.assertNotContains(response, 'Meh')


class DashboardNotificationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def test_notifications_page_filters_by_type(self):
        Notification.objects.create(user=self.user, title='Booking update', type='booking')
        Notification.objects.create(user=self.user, title='Payment alert', type='payment')
        Notification.objects.create(user=self.other, title='Secret', type='booking')

        response = self.client.get(reverse('dashboard_notifications'), {'type': 'booking'})
        titles = [n.title for n in response.context['notifications']]
        self.assertIn('Booking update', titles)
        self.assertNotIn('Payment alert', titles)
        self.assertNotIn('Secret', titles)


class DashboardSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )
        self.client.login(username='alice', password='secret123')

    def test_update_profile(self):
        response = self.client.post(
            reverse('dashboard_settings') + '?tab=profile',
            {'action': 'profile', 'first_name': 'Alice', 'last_name': 'Wong',
             'phone_number': '9990001111', 'city': 'Mumbai', 'country': 'India',
             'address': '', 'date_of_birth': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alice')
        self.assertEqual(self.user.last_name, 'Wong')

    def test_change_password(self):
        response = self.client.post(
            reverse('dashboard_settings') + '?tab=password',
            {'action': 'password', 'current_password': 'secret123',
             'new_password': 'NewPassw0rd!', 'confirm_password': 'NewPassw0rd!'},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassw0rd!'))

    def test_change_password_wrong_current(self):
        response = self.client.post(
            reverse('dashboard_settings') + '?tab=password',
            {'action': 'password', 'current_password': 'wrongpass',
             'new_password': 'NewPassw0rd!', 'confirm_password': 'NewPassw0rd!'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrect')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('secret123'))

    def test_travel_preferences_saved(self):
        response = self.client.post(
            reverse('dashboard_settings') + '?tab=travel',
            {'action': 'travel_preferences', 'budget_range': 'luxury',
             'seat_preference': 'window', 'meal_preference': 'veg',
             'hotel_amenities': ['wifi', 'pool'], 'airline_preferences': '',
             'frequent_flyer': '', 'special_needs': ''},
        )
        self.assertEqual(response.status_code, 302)
        profile = DashboardService.get_profile(self.user)
        self.assertEqual(profile.travel_preferences['budget_range'], 'luxury')
        self.assertEqual(sorted(profile.travel_preferences['hotel_amenities']), ['pool', 'wifi'])

    def test_notification_preferences_saved(self):
        response = self.client.post(
            reverse('dashboard_settings') + '?tab=notifications',
            {'action': 'notification_preferences', 'email_notifications': 'on',
             'trip_reminders': 'on'},
        )
        self.assertEqual(response.status_code, 302)
        profile = DashboardService.get_profile(self.user)
        self.assertTrue(profile.notification_preferences['email_notifications'])
        self.assertTrue(profile.notification_preferences['trip_reminders'])
        self.assertFalse(profile.notification_preferences['promotions'])
