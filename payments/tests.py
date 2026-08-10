"""Payments — unit tests for the Razorpay service layer.

These exercise the money + state-transition logic without contacting the live
gateway (the SDK is mocked). They verify idempotency, signature gating,
booking confirmation, refunds and the security invariants.
"""
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from bookings.models import Booking
from payments.models import Payment
from payments.services import PaymentService, RazorpayService

User = get_user_model()


def _success_gateway(order_id='order_test123'):
    gateway = mock.Mock()
    gateway.create_order.side_effect = lambda payment: setattr(
        payment, 'order_id', order_id) or {'id': order_id, 'amount': 1120000}
    gateway.verify_payment.return_value = True
    gateway.capture_payment.return_value = {'status': 'captured'}
    gateway.refund_payment.return_value = {'id': 'rfnd_test123'}
    gateway.fetch_payment.return_value = {}
    return gateway


class PaymentFlowTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='traveller', email='traveller@example.com',
            password='pass12345',
        )
        self.booking = Booking.objects.create(
            booking_id='TB202600001',
            user=self.user,
            booking_type='Hotel',
            travel_start_date='2026-09-01',
            travel_end_date='2026-09-05',
            adults=2, children=0, infants=0,
            total_travelers=2,
            contact_name='Test Traveller',
            contact_email='traveller@example.com',
            contact_phone='+919999999999',
            status=Booking.Status.PENDING,
            payment_status=Booking.PaymentStatus.PENDING,
            base_price=Decimal('10000.00'),
            taxes=Decimal('1200.00'),
            discount=Decimal('500.00'),
            service_fee=Decimal('500.00'),
            grand_total=Decimal('11200.00'),
        )

    @override_settings(DEFAULT_PAYMENT_GATEWAY='razorpay')
    @mock.patch('payments.services.get_gateway')
    def test_initiate_reuses_pending_attempt_and_marks_order(self, get_gateway):
        gateway = _success_gateway()
        get_gateway.return_value = gateway

        first = PaymentService.initiate_payment(self.booking)
        second = PaymentService.initiate_payment(self.booking)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.status, Payment.Status.PENDING)
        self.assertEqual(first.order_id, 'order_test123')
        # One order created for the pair (re-use, no duplicate orders).
        self.assertEqual(gateway.create_order.call_count, 1)

    @mock.patch('payments.services.get_gateway')
    def test_verify_success_confirms_booking_and_persists_payment_id(self, get_gateway):
        gateway = _success_gateway()
        get_gateway.return_value = gateway

        payment = PaymentService.initiate_payment(self.booking)

        payload = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test456',
            'razorpay_signature': 'sig',
            'method': 'upi',
        }
        payment = PaymentService.verify_payment(payment.id, payload)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.payment_id, 'pay_test456')
        self.assertEqual(payment.payment_method, 'upi')
        self.assertIsNotNone(payment.paid_at)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.PAID)

    @mock.patch('payments.services.get_gateway')
    def test_verify_rejects_invalid_signature_and_keeps_booking_pending(self, get_gateway):
        gateway = _success_gateway()
        gateway.verify_payment.return_value = False
        get_gateway.return_value = gateway

        payment = PaymentService.initiate_payment(self.booking)

        payment = PaymentService.verify_payment(payment.id, {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_bad',
            'razorpay_signature': 'bad',
        })

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.PENDING)

    @mock.patch('payments.services.get_gateway')
    def test_verify_is_idempotent_for_replayed_requests(self, get_gateway):
        get_gateway.return_value = _success_gateway()

        payment = PaymentService.initiate_payment(self.booking)
        payload = {'razorpay_order_id': 'order_test123',
                   'razorpay_payment_id': 'pay_test456',
                   'razorpay_signature': 'sig'}

        PaymentService.verify_payment(payment.id, payload)
        # Replay must not re-confirm or double-process.
        PaymentService.verify_payment(payment.id, payload)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)

    @mock.patch('payments.services.get_gateway')
    def test_refund_marks_payment_and_booking_refunded(self, get_gateway):
        get_gateway.return_value = _success_gateway()

        payment = PaymentService.initiate_payment(self.booking)
        payment = PaymentService.verify_payment(payment.id, {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test456',
            'razorpay_signature': 'sig',
        })

        payment = RazorpayService.refund_payment(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(payment.refund_id, 'rfnd_test123')
        self.assertIsNotNone(payment.refunded_at)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.REFUNDED)
        self.assertEqual(self.booking.payment_status, Booking.PaymentStatus.REFUNDED)

    @mock.patch('payments.services.get_gateway')
    def test_refund_rejects_non_success_payment(self, get_gateway):
        get_gateway.return_value = _success_gateway()
        payment = PaymentService.initiate_payment(self.booking)
        with self.assertRaises(ValueError):
            RazorpayService.refund_payment(payment)