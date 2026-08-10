"""Notification & Communication — tests."""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking
from bookings.services import BookingService
from hotels.models import Hotel
from notifications.models import Notification
from notifications.services import NotificationService
from payments.models import Payment

User = get_user_model()


def _make_hotel(name='Test Hotel'):
    return Hotel.objects.create(
        name=name,
        slug=name.lower().replace(' ', '-'),
        city='Bali',
        country='Indonesia',
        address='1 Beach Road',
        price_per_night=Decimal('100'),
        total_rooms=20,
        available_rooms=10,
        active=True,
    )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='secret123'
        )

    def test_effective_icon_and_color(self):
        n = NotificationService.create(self.user, 'Hello', type=Notification.Type.SUCCESS)
        self.assertEqual(n.effective_icon, 'bi-check-circle-fill')
        self.assertEqual(n.color, '#22C55E')

    def test_mark_read_toggles_state(self):
        n = NotificationService.create(self.user, 'Hello')
        self.assertFalse(n.is_read)
        n.mark_read()
        self.assertTrue(n.is_read)
        self.assertIsNotNone(n.read_at)
        n.mark_unread()
        self.assertFalse(n.is_read)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='bob', email='bob@example.com', password='secret123'
        )
        self.other = User.objects.create_user(
            username='carol', email='carol@example.com', password='secret123'
        )
        # Emails from setUp user creation are drained; tests that care about
        # email create their own user inside the test body.
        mail.outbox.clear()

    def test_create_and_unread_count(self):
        NotificationService.create(self.user, 'One', type=Notification.Type.BOOKING)
        NotificationService.create(self.user, 'Two')
        n = NotificationService.create(self.user, 'Three')
        NotificationService.mark_read(n)

        self.assertEqual(NotificationService.unread_count(self.user), 2)

    def test_mark_all_read(self):
        NotificationService.create(self.user, 'A')
        NotificationService.create(self.user, 'B')
        updated = NotificationService.mark_all_read(self.user)
        self.assertEqual(updated, 2)
        self.assertEqual(NotificationService.unread_count(self.user), 0)

    def test_broadcast_fans_out_to_all_users(self):
        count = NotificationService.broadcast('Flash sale!', 'Up to 40% off.')
        self.assertEqual(count, 2)
        self.assertEqual(Notification.objects.filter(is_broadcast=True).count(), 2)

    def test_registration_signals_send_welcome_and_verification_emails(self):
        with self.captureOnCommitCallbacks(execute=True):
            User.objects.create_user(
                username='fresh', email='fresh@example.com', password='secret123'
            )
        self.assertEqual(len(mail.outbox), 2)
        subjects = {m.subject for m in mail.outbox}
        self.assertTrue(any('Welcome' in s for s in subjects))
        self.assertTrue(any('email address' in s.lower() for s in subjects))

    def test_booking_created_and_cancelled_notifications(self):
        hotel = _make_hotel()
        with self.captureOnCommitCallbacks(execute=True):
            booking = BookingService.create_booking(
                user=self.user,
                product=hotel,
                booking_type='Hotel',
                form_data={
                    'adults': 1, 'children': 0, 'infants': 0,
                    'travel_start': datetime.date(2026, 12, 1),
                    'travel_end': datetime.date(2026, 12, 5),
                    'contact_name': 'Alice', 'contact_email': 'alice@example.com',
                    'contact_phone': '123', 'special_requests': '',
                },
                price_data={
                    'base_price': Decimal('400'), 'tax': Decimal('20'),
                    'discount': Decimal('0'), 'service_fee': Decimal('10'),
                    'grand_total': Decimal('430'),
                },
                nights=4, rooms=1,
            )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, metadata__event='booking_created'
            ).exists()
        )

        with self.captureOnCommitCallbacks(execute=True):
            BookingService.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, metadata__event='booking_cancelled'
            ).exists()
        )
        subjects = {m.subject for m in mail.outbox}
        self.assertTrue(any('cancelled' in s.lower() for s in subjects))

    def test_payment_success_notification(self):
        hotel = _make_hotel('Payment Hotel')
        with self.captureOnCommitCallbacks(execute=True):
            booking = BookingService.create_booking(
                user=self.user,
                product=hotel,
                booking_type='Hotel',
                form_data={
                    'adults': 1, 'children': 0, 'infants': 0,
                    'travel_start': '2027-01-10', 'travel_end': '2027-01-12',
                    'contact_name': 'Bob', 'contact_email': 'bob@example.com',
                    'contact_phone': '456', 'special_requests': '',
                },
                price_data={
                    'base_price': Decimal('180'), 'tax': Decimal('10'),
                    'discount': Decimal('0'), 'service_fee': Decimal('5'),
                    'grand_total': Decimal('195'),
                },
                nights=2, rooms=1,
            )
        payment = Payment.objects.create(
            booking=booking, user=self.user, amount=Decimal('195'),
            currency='INR', gateway='razorpay', status=Payment.Status.PENDING,
        )
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        with self.captureOnCommitCallbacks(execute=True):
            payment.save()

        self.assertTrue(
            Notification.objects.filter(
                user=self.user, metadata__event='payment_success'
            ).exists()
        )
        self.assertTrue(any('Payment received' in m.subject for m in mail.outbox))

    def test_review_submitted_notification(self):
        from reviews.models import Review
        hotel = _make_hotel('Review Hotel')
        with self.captureOnCommitCallbacks(execute=True):
            booking = BookingService.create_booking(
                user=self.user,
                product=hotel,
                booking_type='Hotel',
                form_data={
                    'adults': 1, 'children': 0, 'infants': 0,
                    'travel_start': '2027-02-01', 'travel_end': '2027-02-03',
                    'contact_name': 'Bob', 'contact_email': 'bob@example.com',
                    'contact_phone': '789', 'special_requests': '',
                },
                price_data={
                    'base_price': Decimal('160'), 'tax': Decimal('8'),
                    'discount': Decimal('0'), 'service_fee': Decimal('4'),
                    'grand_total': Decimal('172'),
                },
                nights=2, rooms=1,
            )
        with self.captureOnCommitCallbacks(execute=True):
            Review.objects.create(
                user=self.user, booking=booking, hotel=hotel,
                rating=5, title='Great!', review_text='Lovely stay.',
            )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, metadata__event='review_submitted'
            ).exists()
        )


class NotificationViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='dave', email='dave@example.com', password='secret123'
        )
        self.client.force_login(self.user)

    def test_center_requires_auth_and_lists(self):
        self.client.logout()
        resp = self.client.get(reverse('notifications:notification_center'))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('notifications:notification_center')}")

        self.client.force_login(self.user)
        NotificationService.create(self.user, 'First', type=Notification.Type.BOOKING)
        resp = self.client.get(reverse('notifications:notification_center'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'First')

    def test_unread_count_endpoint(self):
        NotificationService.create(self.user, 'Unread one')
        resp = self.client.get(reverse('notifications:notification_unread_count'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)

    def test_mark_read_redirects_to_action_url(self):
        n = NotificationService.create(self.user, 'Action', action_url='/dashboard/')
        resp = self.client.post(reverse('notifications:notification_read', args=[n.id]))
        self.assertRedirects(resp, '/dashboard/', fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_all_read(self):
        NotificationService.create(self.user, 'A')
        NotificationService.create(self.user, 'B')
        resp = self.client.post(reverse('notifications:notification_mark_all_read'))
        self.assertRedirects(resp, reverse('notifications:notification_center'))
        self.assertEqual(NotificationService.unread_count(self.user), 0)

    def test_delete(self):
        n = NotificationService.create(self.user, 'Delete me')
        resp = self.client.post(reverse('notifications:notification_delete', args=[n.id]))
        self.assertRedirects(resp, reverse('notifications:notification_center'))
        self.assertFalse(Notification.objects.filter(id=n.id).exists())

    def test_dropdown_context(self):
        resp = self.client.get(reverse('notifications:notification_dropdown'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'notification-dropdown')
