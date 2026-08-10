"""Payment gateways — thin adapters around third-party SDKs.

The rest of the app talks to :class:`BasePaymentGateway` only. Every method
returns plain dicts / booleans so the service layer never imports a vendor SDK.

``RazorpayGateway`` is implemented with the official ``razorpay`` Python SDK
and is TEST-MODE only (keys come from ``.env``). No live credentials are ever
hardcoded.
"""
import json
import logging

import razorpay
import urllib.parse
from decimal import Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

from .utils import amount_to_paise, paise_to_amount

logger = logging.getLogger(__name__)


class SignatureVerificationFailed(Exception):
    """Raised when a gateway signature cannot be verified."""


class GatewayConfigurationError(Exception):
    """Raised when gateway credentials are missing or misconfigured."""


class BasePaymentGateway:
    """Interface every gateway adapter must implement."""

    name = 'base'

    def create_order(self, payment):
        raise NotImplementedError

    def verify_payment(self, payment, data):
        raise NotImplementedError

    def capture_payment(self, payment):
        raise NotImplementedError

    def refund_payment(self, payment, amount=None, notes=None):
        raise NotImplementedError

    def process_webhook(self, request):
        raise NotImplementedError


class RazorpayGateway(BasePaymentGateway):
    """Razorpay (TEST MODE) adapter backed by the official SDK."""

    name = 'razorpay'

    def __init__(self):
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        if not key_id or not key_secret:
            raise GatewayConfigurationError(
                'Razorpay keys are not configured. '
                'Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env.'
            )
        self.key_id = key_id
        self.key_secret = key_secret
        self.client = razorpay.Client(auth=(key_id, key_secret))

    # ------------------------------------------------------------ creation

    def create_order(self, payment):
        """Create a Razorpay order and persist the ``order_id`` on payment.

        ``payment_capture=1`` keeps the default auto-capture behaviour in test
        mode: funds are captured when the customer completes the checkout.
        """
        data = {
            'amount': amount_to_paise(payment.amount),
            'currency': payment.currency,
            'receipt': payment.transaction_id,
            'payment_capture': 1,
            'notes': {
                'booking_id': payment.booking.booking_id,
                'transaction_id': payment.transaction_id,
                'user_id': str(payment.user.id),
            },
        }
        logger.info('Razorpay create_order amount=%s %s receipt=%s',
                    payment.amount, payment.currency, payment.transaction_id)
        response = self.client.order.create(data)

        payment.order_id = response.get('id', '')
        payment.gateway_response = {
            **(payment.gateway_response or {}),
            'order_creation': response,
        }
        payment.save(update_fields=['order_id', 'gateway_response', 'updated_at'])
        return response

    # --------------------------------------------------------- verification

    def verify_payment(self, payment, data):
        """Cryptographically verify the Razorpay checkout signature.

        NEVER trusts the front-end. The signature is validated with the SDK
        utility using the server-side Key Secret, which defeats tampered /
        forged / replayed responses.
        """
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return False

        # Belt-and-braces: the order must belong to this local Payment row.
        if payment.order_id and razorpay_order_id != payment.order_id:
            logger.warning('Order mismatch for payment %s: expected %s got %s',
                           getattr(payment, 'transaction_id', None),
                           payment.order_id,
                           razorpay_order_id)
            return False

        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning('Signature verification failed for payment %s',
                           getattr(payment, 'transaction_id', None))
            return False

    # ------------------------------------------------------------- capture

    def capture_payment(self, payment):
        """Re-attempt payment capture (useful for pending-authorised orders)."""
        if not payment.payment_id:
            return None
        return self.client.payment.capture(payment.payment_id,
                                           amount_to_paise(payment.amount))

    def fetch_payment(self, payment_id):
        """Return the live Razorpay payment entity for ``payment_id``."""
        return self.client.payment.fetch(payment_id)

    # -------------------------------------------------------------- refund

    def refund_payment(self, payment, amount=None, notes=None):
        """Issue a full (or partial) refund through the gateway.

        Returns the raw gateway response; ``refund_id`` is extracted by the
        service layer so the caller only deals with domain data.
        """
        if not payment.payment_id:
            raise GatewayConfigurationError(
                'Cannot refund: no gateway payment_id recorded.'
            )
        refund_amount = amount if amount is not None else payment.amount
        data = {'amount': amount_to_paise(refund_amount)}
        if notes:
            data['notes'] = notes
        logger.info('Razorpay refund payment=%s amount=%s',
                    payment.payment_id, refund_amount)
        return self.client.payment.refund(payment.payment_id, data)

    # ------------------------------------------------------------- webhook

    def process_webhook(self, request):
        """Verify the webhook signature and normalise the Razorpay event."""
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        received_signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
        body = request.body

        if not webhook_secret:
            logger.warning('RAZORPAY_WEBHOOK_SECRET not set; webhooks ignored.')
            return None
        if not received_signature:
            return None

        try:
            self.client.utility.verify_webhook_signature(
                body, received_signature, webhook_secret
            )
        except razorpay.errors.SignatureVerificationError:
            logger.warning('Webhook signature verification failed.')
            return None

        payload = json.loads(body if isinstance(body, bytes) else body.decode())
        event = payload.get('event', '')
        payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})

        return {
            'event': event,
            'payment_id': payment_entity.get('id'),
            'order_id': payment_entity.get('order_id'),
            'status': payment_entity.get('status'),
            'method': payment_entity.get('method'),
            'amount': paise_to_amount(payment_entity.get('amount', 0)),
        }


class StripeGateway(BasePaymentGateway):
    """Stripe adapter (kept for backward compatibility; not required for
    the Razorpay TEST MODE integration)."""

    name = 'stripe'

    def __init__(self):
        from django.conf import settings as s
        if not getattr(s, 'STRIPE_SECRET_KEY', ''):
            raise GatewayConfigurationError('STRIPE_SECRET_KEY is not configured.')

    def _api_request(self, method, path, data=None):
        url = f'https://api.stripe.com/v1/{path}'
        body = urllib.parse.urlencode(data).encode() if data else None
        req = Request(url, data=body, method=method)
        req.add_header('Authorization', f'Bearer {settings.STRIPE_SECRET_KEY}')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        try:
            resp = urlopen(req)
            return json.loads(resp.read().decode())
        except URLError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            raise Exception(f'Stripe API error: {error_body}')

    def create_order(self, payment):
        amount_cents = int(payment.amount * Decimal('100'))
        data = {
            'amount': amount_cents,
            'currency': payment.currency.lower(),
            'metadata[booking_id]': payment.booking.booking_id,
            'metadata[user_id]': str(payment.user.id),
        }
        response = self._api_request('POST', 'payment_intents', data)
        payment.order_id = response.get('id')
        payment.gateway_response = response
        payment.save(update_fields=['order_id', 'gateway_response'])
        return response

    def verify_payment(self, payment, data):
        intent_id = data.get('payment_intent_id')
        if not intent_id:
            return False
        try:
            response = self._api_request('GET', f'payment_intents/{intent_id}')
            return response.get('status') == 'succeeded'
        except Exception:
            return False

    def capture_payment(self, payment):
        if not payment.order_id:
            return None
        return self._api_request('POST', f'payment_intents/{payment.order_id}/capture')

    def refund_payment(self, payment, amount=None, notes=None):
        data = {'payment_intent': payment.order_id}
        if amount is not None:
            data['amount'] = int(amount * Decimal('100'))
        return self._api_request('POST', 'refunds', data)

    def process_webhook(self, request):
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        body = request.body
        if not webhook_secret or not signature:
            return None

        try:
            timestamp, signatures = self._parse_signature(signature)
            signed_payload = f'{timestamp}.'.encode() + (body if isinstance(body, bytes) else body.encode())
            expected = self._hmac(webhook_secret, signed_payload)
            if not any(self._hmac_compare(expected, s) for s in signatures):
                return None
        except Exception:
            return None

        payload = json.loads(body)
        event_type = payload.get('type', '')
        intent = payload.get('data', {}).get('object', {})
        return {
            'event': event_type,
            'payment_id': intent.get('id'),
            'order_id': intent.get('id'),
            'status': intent.get('status'),
            'method': intent.get('payment_method_types', [None])[0],
            'amount': intent.get('amount'),
        }

    @staticmethod
    def _parse_signature(header):
        timestamp = None
        signatures = []
        for part in header.split(','):
            key, _, value = part.strip().partition('=')
            if key == 't':
                timestamp = value
            elif key == 'v1':
                signatures.append(value)
        if not timestamp or not signatures:
            raise ValueError('Invalid Stripe signature header')
        return timestamp, signatures

    @staticmethod
    def _hmac(secret, payload):
        import hashlib
        import hmac
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    @staticmethod
    def _hmac_compare(a, b):
        import hashlib
        import hmac
        return hmac.compare_digest(a, b)


GATEWAYS = {
    'razorpay': RazorpayGateway,
    'stripe': StripeGateway,
}


def get_gateway(name=None):
    """Return a configured gateway instance.

    Falls back to the settings default; any :class:`GatewayConfigurationError`
    raised by a constructor propagates to the caller.
    """
    name = name or getattr(settings, 'DEFAULT_PAYMENT_GATEWAY', 'razorpay')
    if name not in GATEWAYS:
        raise GatewayConfigurationError(f'Unsupported gateway: {name}')
    return GATEWAYS[name]()