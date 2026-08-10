"""Payments — domain services.

Everything payment-related lives here so views stay thin. Two layers:

* :class:`PaymentService` — high-level, idempotent orchestration used by the
  views and webhooks (initiate → verify → confirm → email → invoice).
* :class:`RazorpayService` — the Razorpay-specific primitives requested by the
  product (create_order, verify_signature, capture_payment, save_transaction,
  refund_payment).

Security invariants enforced in this module:

* the Razorpay signature is ALWAYS verified server-side with the SDK,
* a payment only ever transitions Pending → Success once (row-locked),
* a booking is only confirmed after a verified payment,
* refunds are only allowed on already-successful payments.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .gateway import get_gateway
from .models import Payment
from .utils import paise_to_amount

logger = logging.getLogger(__name__)


def _mark_failed(payment, error):
    payment.status = Payment.Status.FAILED
    payment.gateway_response = {
        **(payment.gateway_response or {}),
        'error': str(error),
        'failed_at': timezone.now().isoformat(),
    }
    payment.save(update_fields=['status', 'gateway_response', 'updated_at'])


class RazorpayService:
    """Razorpay-specific payment primitives (TEST MODE)."""

    gateway_name = 'razorpay'

    # ------------------------------------------------------------- orders

    @staticmethod
    @transaction.atomic
    def create_order(payment):
        """Create the Razorpay order and persist ``order_id`` on payment."""
        gateway = get_gateway('razorpay')
        return gateway.create_order(payment)

    # ----------------------------------------------------------- signature

    @staticmethod
    def verify_signature(payment, gateway_data):
        """Verify the Razorpay checkout signature.

        Returns ``True``/``False``. Never trusts data sent by the browser.
        """
        gateway = get_gateway('razorpay')
        return gateway.verify_payment(payment, gateway_data)

    @staticmethod
    @transaction.atomic
    def save_transaction(payment, gateway_data):
        """Persist verified gateway transaction details on the payment row."""
        payment.payment_id = gateway_data.get('razorpay_payment_id') or payment.payment_id
        payment.order_id = gateway_data.get('razorpay_order_id') or payment.order_id
        payment.payment_method = gateway_data.get('method') or gateway_data.get('payment_method') or payment.payment_method
        payment.paid_at = timezone.now()
        payment.gateway_response = {
            **(payment.gateway_response or {}),
            'verification_data': gateway_data,
            'verified_at': timezone.now().isoformat(),
        }
        payment.save(update_fields=[
            'payment_id', 'order_id', 'payment_method',
            'paid_at', 'gateway_response', 'updated_at',
        ])
        return payment

    # ------------------------------------------------------------- capture

    @staticmethod
    @transaction.atomic
    def capture_payment(payment):
        """Capture an authorised Razorpay payment (test-mode auto-capture).

        Kept as an explicit reconciliation hook: it is safe to call repeatedly
        because capture is only attempted on payments still in Pending state.
        """
        if payment.status != Payment.Status.PENDING or not payment.payment_id:
            return None
        gateway = get_gateway('razorpay')
        response = gateway.capture_payment(payment)
        payment.gateway_response = {
            **(payment.gateway_response or {}),
            'capture_response': response,
        }
        payment.save(update_fields=['gateway_response', 'updated_at'])
        return response

    # -------------------------------------------------------------- refund

    @staticmethod
    @transaction.atomic
    def refund_payment(payment, amount=None, notes=None):
        """Refund a successful payment and mark it refunded.

        :param amount: optional partial amount; defaults to the full amount.
        :raises ValueError: if the payment is not refundable.
        """
        if payment.status != Payment.Status.SUCCESS:
            raise ValueError('Only successful payments can be refunded.')
        if payment.status == Payment.Status.REFUNDED:
            return payment

        notes = notes or {'refunded_by': 'admin', 'booking_id': payment.booking.booking_id}
        gateway = get_gateway(payment.gateway)
        response = gateway.refund_payment(payment, amount=amount, notes=notes)

        payment.refund_id = response.get('id', '') or None
        payment.status = Payment.Status.REFUNDED
        payment.refunded_at = timezone.now()
        payment.gateway_response = {
            **(payment.gateway_response or {}),
            'refund_response': response,
            'refunded_at': timezone.now().isoformat(),
        }
        payment.save(update_fields=[
            'refund_id', 'status', 'refunded_at',
            'gateway_response', 'updated_at',
        ])

        booking = payment.booking
        booking.payment_status = 'Refunded'
        booking.status = 'Refunded'
        booking.save(update_fields=['payment_status', 'status', 'updated_at'])
        return payment


class PaymentService:
    """High-level, idempotent payment orchestration."""

    # ---------------------------------------------------------- initiate

    @staticmethod
    @transaction.atomic
    def initiate_payment(booking, gateway_name=None):
        """Create a pending Payment + Razorpay order for ``booking``.

        * Re-uses an in-flight Pending payment (no duplicate orders),
        * creates a fresh Payment for a previously Failed/Refunded one,
        * never touches an already-paid booking.
        """
        gateway_name = gateway_name or getattr(settings, 'DEFAULT_PAYMENT_GATEWAY', 'razorpay')

        existing = Payment.objects.filter(
            booking=booking, status=Payment.Status.PENDING
        ).select_for_update().first()
        if existing:
            return existing

        payment = Payment.objects.create(
            booking=booking,
            user=booking.user,
            amount=booking.grand_total,
            currency=getattr(settings, 'DEFAULT_CURRENCY', 'INR'),
            gateway=gateway_name,
            status=Payment.Status.PENDING,
        )

        try:
            gateway = get_gateway(gateway_name)
            gateway.create_order(payment)
        except Exception as exc:
            logger.exception('Order creation failed for booking %s', booking.booking_id)
            _mark_failed(payment, exc)
            raise

        return payment

    # ----------------------------------------------------------- verify

    @staticmethod
    @transaction.atomic
    def verify_payment(payment_id, gateway_data):
        """Verify a Razorpay signature and, on success, confirm the booking.

        Idempotent & concurrency-safe:

        * the Payment row is locked with ``select_for_update``,
        * only a Pending payment can transition,
        * booking confirmation + emails fire exactly once.
        """
        payment = Payment.objects.select_for_update().select_related('booking').get(id=payment_id)

        if payment.status == Payment.Status.SUCCESS:
            return payment  # already verified — replay-safe
        if payment.status != Payment.Status.PENDING:
            return payment  # Failed/Refunded payments are never re-verified

        gateway = get_gateway(payment.gateway)
        is_valid = gateway.verify_payment(payment, gateway_data)

        if is_valid:
            RazorpayService.save_transaction(payment, gateway_data)
            payment.status = Payment.Status.SUCCESS
            payment.save(update_fields=['status', 'updated_at'])

            booking = payment.booking
            if booking.status == 'Pending':
                from bookings.services import BookingService
                booking._confirmed_by_payment = True
                BookingService.confirm_booking(booking)
        else:
            _mark_failed(payment, 'Signature verification failed')

        return payment

    # --------------------------------------------------- server reconcile

    @staticmethod
    @transaction.atomic
    def reconcile_payment(payment):
        """Reconcile a Pending payment against the live gateway state.

        Used by retry/status endpoints and the admin dashboard so a payment
        that actually succeeded at Razorpay but never got a callback is still
        marked paid.
        """
        if payment.status != Payment.Status.PENDING or not payment.payment_id:
            return payment

        gateway = get_gateway(payment.gateway)
        entity = gateway.fetch_payment(payment.payment_id)

        if entity.get('status') in ('captured', 'authorized') and entity.get('captured'):
            RazorpayService.save_transaction(payment, {
                'razorpay_payment_id': entity.get('id'),
                'razorpay_order_id': entity.get('order_id'),
                'method': entity.get('method'),
                'gateway_status': entity.get('status'),
                'amount_paise': entity.get('amount'),
            })
            payment.amount = paise_to_amount(entity.get('amount', 0)) or payment.amount
            payment.status = Payment.Status.SUCCESS
            payment.save(update_fields=['status', 'amount', 'updated_at'])

            booking = payment.booking
            if booking.status == 'Pending':
                from bookings.services import BookingService
                booking._confirmed_by_payment = True
                BookingService.confirm_booking(booking)
        return payment

    # ------------------------------------------------------------ webhook

    @staticmethod
    @transaction.atomic
    def process_webhook(gateway_name, request):
        """Process a verified gateway webhook and update local state."""
        gateway = get_gateway(gateway_name)
        event = gateway.process_webhook(request)

        if not event:
            return None

        event_type = event['event']
        payment_id = event.get('payment_id') or ''
        order_id = event.get('order_id') or ''

        if event_type in ('payment.captured', 'payment_intent.succeeded', 'order.paid'):
            payment = Payment.objects.select_for_update().select_related('booking').filter(
                status=Payment.Status.PENDING
            ).filter(
                Q(payment_id=payment_id) | Q(order_id=order_id)
            ).first()

            if payment:
                RazorpayService.save_transaction(payment, {
                    'razorpay_payment_id': payment_id,
                    'razorpay_order_id': order_id,
                    'method': event.get('method', ''),
                    'amount': str(event.get('amount', '')),
                })
                payment.status = Payment.Status.SUCCESS
                payment.save(update_fields=['status', 'updated_at'])

                booking = payment.booking
                if booking.status == 'Pending':
                    from bookings.services import BookingService
                    booking._confirmed_by_payment = True
                    BookingService.confirm_booking(booking)

        elif event_type in ('payment.failed', 'payment_intent.payment_failed'):
            payment = Payment.objects.select_for_update().filter(
                status=Payment.Status.PENDING,
                payment_id=payment_id,
            ).first()
            if payment:
                _mark_failed(payment, 'Gateway reported payment failure')

        return event