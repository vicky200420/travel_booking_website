"""Notification & Communication — shared helpers."""
from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

signer = TimestampSigner(salt='travelbooking.email-verification')

VERIFICATION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def generate_verification_token(user):
    """Signed, time-limited token proving email ownership."""
    return signer.sign(user.email)


def load_verification_token(token, max_age=VERIFICATION_MAX_AGE_SECONDS):
    """Return the verified email address or ``None`` for invalid/expired token."""
    try:
        return signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def format_money(amount, currency=None):
    """INR-style symbol formatting with sensible fallback to USD."""
    amount = amount or 0
    currency = (currency or getattr(settings, 'DEFAULT_CURRENCY', 'INR')).upper()
    if currency == 'INR':
        return f'\u20b9{amount:,.2f}'
    return f'${amount:,.2f}'


def booking_context(booking):
    """Flat, template-friendly trip details for a booking (email-safe)."""
    flight = booking.flight
    ctx = {
        'booking': booking,
        'booking_id': booking.booking_id,
        'booking_type': booking.booking_type,
        'destination': booking.destination_display,
        'item_name': booking.title_display,
        'travel_start': booking.travel_start_date,
        'travel_end': booking.travel_end_date,
        'nights': max((booking.travel_end_date - booking.travel_start_date).days, 1),
        'adults': booking.adults,
        'children': booking.children,
        'infants': booking.infants,
        'total_travelers': booking.total_travelers,
        'contact_name': booking.contact_name,
        'contact_email': booking.contact_email,
        'contact_phone': booking.contact_phone,
        'special_requests': booking.special_requests,
        'grand_total': format_money(booking.grand_total),
        'booking_url': None,
        'pay_url': None,
    }
    if flight:
        ctx.update({
            'flight_number': flight.flight_number,
            'airline': flight.airline_name,
            'departure_city': flight.departure_city,
            'destination_city': flight.destination_city,
            'departure_airport': flight.departure_airport,
            'arrival_airport': flight.arrival_airport,
            'departure_time': f'{flight.departure_time:%H:%M}',
            'arrival_time': f'{flight.arrival_time:%H:%M}',
        })
    return ctx


def payment_context(payment):
    booking = payment.booking
    return {
        'payment': payment,
        'booking': booking,
        'booking_id': booking.booking_id,
        'transaction_id': payment.transaction_id,
        'order_id': payment.order_id,
        'gateway': payment.get_gateway_display(),
        'payment_method': payment.payment_method or 'Online',
        'amount': format_money(payment.amount, payment.currency),
        'currency': payment.currency,
        'paid_at': payment.paid_at or timezone.now(),
        'booking_url': None,
        'pay_url': None,
    }
