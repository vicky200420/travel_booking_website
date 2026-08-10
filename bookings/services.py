from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Booking
from .utils import generate_booking_id


class BookingService:

    @staticmethod
    def validate_availability(product, booking_type, adults, children=0, infants=0, rooms=1):
        total_pax = adults + children + infants

        if booking_type == 'Flight':
            if not product or product.status == 'cancelled':
                raise ValidationError('This flight is no longer available.')
            if product.available_seats < total_pax:
                raise ValidationError(
                    f'Only {product.available_seats} seat(s) available. '
                    f'Requested {total_pax}.'
                )

        elif booking_type == 'Hotel':
            if not product or not product.active:
                raise ValidationError('This hotel is no longer available.')
            if product.available_rooms < rooms:
                raise ValidationError(
                    f'Only {product.available_rooms} room(s) available. '
                    f'Requested {rooms}.'
                )

        elif booking_type == 'Package':
            if not product or not product.active:
                raise ValidationError('This package is no longer available.')
            if total_pax > product.max_travelers:
                raise ValidationError(
                    f'Maximum {product.max_travelers} traveler(s) allowed per booking.'
                )

        return True

    @staticmethod
    @transaction.atomic
    def create_booking(user, product, booking_type, form_data, price_data, nights=1, rooms=1):
        adults = form_data['adults']
        children = form_data['children']
        infants = form_data['infants']
        total_pax = adults + children + infants
        travel_start = form_data['travel_start']
        travel_end = form_data['travel_end']

        BookingService.validate_availability(
            product, booking_type, adults, children, infants, rooms
        )

        booking_id = generate_booking_id()

        booking = Booking.objects.create(
            booking_id=booking_id,
            user=user,
            booking_type=booking_type,
            flight=product if booking_type == 'Flight' else None,
            hotel=product if booking_type == 'Hotel' else None,
            package=product if booking_type == 'Package' else None,
            travel_start_date=travel_start,
            travel_end_date=travel_end,
            adults=adults,
            children=children,
            infants=infants,
            total_travelers=total_pax,
            contact_name=form_data['contact_name'],
            contact_email=form_data['contact_email'],
            contact_phone=form_data['contact_phone'],
            special_requests=form_data.get('special_requests', ''),
            status=Booking.Status.PENDING,
            payment_status=Booking.PaymentStatus.PENDING,
            base_price=price_data['base_price'],
            taxes=price_data['tax'],
            discount=price_data['discount'],
            service_fee=price_data['service_fee'],
            grand_total=price_data['grand_total'],
        )

        BookingService._update_availability(product, booking_type, adults, children, infants, rooms, decrease=True)

        return booking

    @staticmethod
    @transaction.atomic
    def cancel_booking(booking):
        if not booking.can_cancel:
            raise ValidationError('This booking cannot be cancelled.')

        product = booking.related_item
        if product and booking.status not in ['Cancelled', 'Refunded']:
            rooms = getattr(booking, '_rooms', 1)
            BookingService._update_availability(
                product, booking.booking_type,
                booking.adults, booking.children, booking.infants,
                rooms, decrease=False
            )

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])
        return booking

    @staticmethod
    @transaction.atomic
    def confirm_booking(booking):
        if booking.status != Booking.Status.PENDING:
            raise ValidationError('Only pending bookings can be confirmed.')

        booking.status = Booking.Status.CONFIRMED
        booking.payment_status = Booking.PaymentStatus.PAID
        booking.save(update_fields=['status', 'payment_status', 'updated_at'])
        return booking

    @staticmethod
    def _update_availability(product, booking_type, adults, children, infants, rooms, decrease=True):
        total_pax = adults + children + infants
        modifier = -1 if decrease else 1

        if booking_type == 'Flight' and product:
            product.available_seats += modifier * total_pax
            product.save(update_fields=['available_seats'])

        elif booking_type == 'Hotel' and product:
            product.available_rooms += modifier * rooms
            product.save(update_fields=['available_rooms'])
