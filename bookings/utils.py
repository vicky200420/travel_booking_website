from decimal import Decimal

from django.utils import timezone

from .models import Booking


def generate_booking_id():
    year = timezone.now().year
    prefix = f'TB{year}'
    last_booking = Booking.objects.filter(
        booking_id__startswith=prefix
    ).select_for_update().order_by('booking_id').last()
    if last_booking:
        last_num = int(last_booking.booking_id[len(prefix):])
        new_num = last_num + 1
    else:
        new_num = 1
    return f'{prefix}{new_num:05d}'


def calculate_price(product, booking_type, adults, children=0, infants=0, nights=1, rooms=1):
    TAX_RATE = Decimal('0.12')
    SERVICE_FEE_RATE = Decimal('0.05')

    unit_price = product.discounted_price if hasattr(product, 'discounted_price') else product.price

    if booking_type == 'Flight':
        base_price = unit_price * adults
    elif booking_type == 'Hotel':
        base_price = unit_price * nights * rooms
    elif booking_type == 'Package':
        total_pax = adults + children
        base_price = unit_price * total_pax
    else:
        base_price = unit_price

    discount_amount = Decimal('0')
    if hasattr(product, 'discount_percentage') and product.discount_percentage > 0:
        discount_amount = base_price * (product.discount_percentage / Decimal('100'))

    taxable_amount = base_price - discount_amount
    tax = taxable_amount * TAX_RATE
    service_fee = base_price * SERVICE_FEE_RATE
    grand_total = base_price + tax + service_fee - discount_amount

    return {
        'base_price': base_price.quantize(Decimal('0.01')),
        'tax': tax.quantize(Decimal('0.01')),
        'service_fee': service_fee.quantize(Decimal('0.01')),
        'discount': discount_amount.quantize(Decimal('0.01')),
        'grand_total': grand_total.quantize(Decimal('0.01')),
    }
