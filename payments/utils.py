"""Payments — shared helpers.

Thin, pure helpers (no Django ORM, no gateway SDK) used across the payment
service, gateway and views. Keeping them isolated makes the money logic easy
to unit test.
"""
from decimal import Decimal, InvalidOperation


def amount_to_paise(amount):
    """Convert a :class:`Decimal` (in rupees) to the smallest currency unit.

    Razorpay works in paise (1/100 of a rupee), always as an integer.

    :raises ValueError: if ``amount`` is negative or not a finite Decimal.
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'Invalid amount: {amount!r}') from exc

    if value < 0:
        raise ValueError('Amount cannot be negative.')

    paise = (value * Decimal('100')).quantize(Decimal('1'))
    return int(paise)


def paise_to_amount(paise):
    """Convert integer paise back to a two-decimal-rupee :class:`Decimal`."""
    try:
        return (Decimal(paise) / Decimal('100')).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00')


def safe_decimal(value, default='0.00'):
    """Return a clean :class:`Decimal` or ``default`` for unknown inputs."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def build_signature_message(order_id, payment_id):
    """Concatenated payload that Razorpay signs for a checkout payment."""
    return f'{order_id}|{payment_id}'


def idempotency_key(payment):
    """Stable, attack-proof reference used to prevent duplicate gateway calls."""
    return payment.transaction_id or f'TXN{payment.id}'