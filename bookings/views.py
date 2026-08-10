from decimal import Decimal

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from .forms import BookingForm
from .models import Booking
from .services import BookingService
from .utils import calculate_price

TYPE_MODEL_MAP = {
    'flight': ('flights', 'Flight'),
    'hotel': ('hotels', 'Hotel'),
    'package': ('packages', 'TravelPackage'),
}

TYPE_LABEL_MAP = {
    'flight': 'Flight',
    'hotel': 'Hotel',
    'package': 'Package',
}


def _get_product(booking_type, product_id):
    if booking_type not in TYPE_MODEL_MAP:
        return None
    app_label, model_name = TYPE_MODEL_MAP[booking_type]
    model = apps.get_model(app_label, model_name)
    return get_object_or_404(model, id=product_id)


class BookingHistoryView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'bookings/booking_history.html'
    context_object_name = 'bookings'
    paginate_by = 10

    def get_queryset(self):
        qs = Booking.objects.filter(user=self.request.user)
        status = self.request.GET.get('status')
        booking_type = self.request.GET.get('type')
        search = self.request.GET.get('search')

        if status:
            qs = qs.filter(status=status)
        if booking_type:
            qs = qs.filter(booking_type=booking_type)
        if search:
            qs = qs.filter(
                Q(booking_id__icontains=search) |
                Q(contact_name__icontains=search)
            )

        return qs.select_related('flight', 'hotel', 'package').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_status'] = self.request.GET.get('status', '')
        context['active_type'] = self.request.GET.get('type', '')
        return context


class BookingCreateView(LoginRequiredMixin, FormView):
    template_name = 'bookings/booking_form.html'
    form_class = BookingForm

    def dispatch(self, request, *args, **kwargs):
        raw_type = request.GET.get('type', '')
        self.booking_type_label = TYPE_LABEL_MAP.get(raw_type)
        if not self.booking_type_label:
            messages.error(request, 'Invalid booking type.')
            return redirect('booking_history')

        self.product = _get_product(raw_type, request.GET.get('id'))
        if not self.product:
            messages.error(request, 'Product not found.')
            return redirect('booking_history')

        if self.booking_type_label == 'Flight' and self.product.status == 'cancelled':
            messages.error(request, 'This flight is no longer available.')
            return redirect('flight_detail', id=self.product.id)

        if self.booking_type_label in ('Hotel', 'Package') and not self.product.active:
            messages.error(request, 'This item is no longer available.')
            return redirect('booking_history')

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['booking_type'] = self.booking_type_label
        kwargs['product'] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking_type'] = self.booking_type_label
        context['product'] = self.product

        if self.booking_type_label == 'Flight':
            context['nights'] = (self.product.arrival_date - self.product.departure_date).days or 1
        elif self.booking_type_label == 'Package':
            context['nights'] = self.product.duration_nights or 0

        return context

    def form_valid(self, form):
        cd = form.cleaned_data
        form_data = {
            'adults': cd['adults'],
            'children': cd['children'],
            'infants': cd['infants'],
            'contact_name': cd['contact_name'],
            'contact_email': cd['contact_email'],
            'contact_phone': cd['contact_phone'],
            'special_requests': cd.get('special_requests', ''),
        }

        bt = self.booking_type_label
        if bt == 'Flight':
            form_data['travel_start'] = self.product.departure_date.isoformat()
            form_data['travel_end'] = self.product.arrival_date.isoformat()
            nights = (self.product.arrival_date - self.product.departure_date).days or 1
            rooms = 1
        elif bt == 'Hotel':
            form_data['travel_start'] = cd['check_in'].isoformat()
            form_data['travel_end'] = cd['check_out'].isoformat()
            nights = max((cd['check_out'] - cd['check_in']).days, 1)
            rooms = cd.get('rooms', 1)
        else:
            form_data['travel_start'] = cd['travel_start'].isoformat()
            form_data['travel_end'] = cd['travel_end'].isoformat()
            nights = max((cd['travel_end'] - cd['travel_start']).days, 1)
            rooms = 1

        price_data = calculate_price(
            self.product, bt,
            form_data['adults'], form_data['children'],
            form_data['infants'], nights, rooms
        )

        self.request.session['booking_data'] = {
            'type': bt,
            'product_id': str(self.product.id),
            'form_data': {k: str(v) for k, v in form_data.items()},
            'price_data': {k: str(v) for k, v in price_data.items()},
            'nights': nights,
            'rooms': rooms,
        }

        return redirect('booking_review')

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def _load_booking_session(request):
    bd = request.session.get('booking_data')
    if not bd:
        return None, None
    raw_type = next((k for k, v in TYPE_LABEL_MAP.items() if v == bd['type']), None)
    if not raw_type:
        return None, None
    product = _get_product(raw_type, bd['product_id'])
    return bd, product


class BookingReviewView(LoginRequiredMixin, TemplateView):
    template_name = 'bookings/booking_review.html'

    def dispatch(self, request, *args, **kwargs):
        self.bd, self.product = _load_booking_session(request)
        if not self.bd or not self.product:
            messages.error(request, 'No booking in progress. Please start again.')
            return redirect('booking_history')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fd = self.bd['form_data']
        pd = self.bd['price_data']

        context.update(
            booking_type=self.bd['type'],
            product=self.product,
            adults=fd['adults'],
            children=fd['children'],
            infants=fd['infants'],
            total_travelers=int(fd['adults']) + int(fd['children']) + int(fd['infants']),
            contact_name=fd['contact_name'],
            contact_email=fd['contact_email'],
            contact_phone=fd['contact_phone'],
            special_requests=fd.get('special_requests', ''),
            travel_start=fd['travel_start'],
            travel_end=fd['travel_end'],
            nights=self.bd.get('nights', 1),
            rooms=self.bd.get('rooms', 1),
            base_price=Decimal(pd['base_price']),
            tax=Decimal(pd['tax']),
            discount=Decimal(pd['discount']),
            service_fee=Decimal(pd['service_fee']),
            grand_total=Decimal(pd['grand_total']),
        )
        return context

    def post(self, request, *args, **kwargs):
        bd, product = _load_booking_session(request)
        if not bd or not product:
            messages.error(request, 'Session expired. Please start again.')
            return redirect('booking_history')

        fd = bd['form_data']
        pd = bd['price_data']

        try:
            booking = BookingService.create_booking(
                user=request.user,
                product=product,
                booking_type=bd['type'],
                form_data={
                    'adults': int(fd['adults']),
                    'children': int(fd['children']),
                    'infants': int(fd['infants']),
                    'travel_start': fd['travel_start'],
                    'travel_end': fd['travel_end'],
                    'contact_name': fd['contact_name'],
                    'contact_email': fd['contact_email'],
                    'contact_phone': fd['contact_phone'],
                    'special_requests': fd.get('special_requests', ''),
                },
                price_data={
                    'base_price': Decimal(pd['base_price']),
                    'tax': Decimal(pd['tax']),
                    'discount': Decimal(pd['discount']),
                    'service_fee': Decimal(pd['service_fee']),
                    'grand_total': Decimal(pd['grand_total']),
                },
                nights=bd.get('nights', 1),
                rooms=bd.get('rooms', 1),
            )

            del request.session['booking_data']
            messages.success(request, f'Booking {booking.booking_id} created successfully!')
            return redirect('booking_detail', booking_id=booking.booking_id)

        except Exception as e:
            messages.error(request, str(e))
            return redirect('booking_create')


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'
    slug_field = 'booking_id'
    slug_url_kwarg = 'booking_id'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            'flight', 'hotel', 'package'
        )


class BookingCancelView(LoginRequiredMixin, View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        try:
            BookingService.cancel_booking(booking)
            messages.success(request, f'Booking {booking_id} has been cancelled.')
        except Exception as e:
            messages.error(request, str(e))
        return redirect('booking_detail', booking_id=booking_id)

    def get(self, request, booking_id):
        return self.post(request, booking_id)


class BookingDownloadView(LoginRequiredMixin, View):
    def get(self, request, booking_id):
        messages.info(request, 'Download functionality coming soon.')
        return redirect('booking_detail', booking_id=booking_id)
