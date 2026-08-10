from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import DetailView, FormView, ListView

from .forms import FlightSearchForm
from .models import Flight


class FlightSearchView(FormView):
    template_name = 'flights/search.html'
    form_class = FlightSearchForm
    paginate_by = 9

    def form_valid(self, form):
        qs = Flight.objects.filter(status__in=['scheduled', 'delayed'])

        departure = form.cleaned_data.get('departure_city')
        destination = form.cleaned_data.get('destination_city')
        departure_date = form.cleaned_data.get('departure_date')
        cabin_class = form.cleaned_data.get('cabin_class')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        non_stop = form.cleaned_data.get('non_stop')
        refundable = form.cleaned_data.get('refundable')
        sort_by = form.cleaned_data.get('sort_by')
        travellers = form.cleaned_data.get('travellers', 1)

        if departure:
            qs = qs.filter(
                Q(departure_city__icontains=departure) |
                Q(departure_airport__icontains=departure)
            )
        if destination:
            qs = qs.filter(
                Q(destination_city__icontains=destination) |
                Q(arrival_airport__icontains=destination)
            )
        if departure_date:
            qs = qs.filter(departure_date=departure_date)
        if cabin_class:
            qs = qs.filter(cabin_class=cabin_class)
        if min_price:
            qs = qs.filter(discounted_price__gte=min_price)
        if max_price:
            qs = qs.filter(discounted_price__lte=max_price)
        if non_stop:
            qs = qs.filter(flight_type=Flight.FlightType.ONE_WAY)
        if refundable:
            qs = qs.filter(refundable=True)
        if travellers:
            qs = qs.filter(available_seats__gte=travellers)

        if sort_by == 'price_low':
            qs = qs.order_by('discounted_price')
        elif sort_by == 'price_high':
            qs = qs.order_by('-discounted_price')
        elif sort_by == 'fastest':
            qs = qs.order_by('flight_duration')
        elif sort_by == 'earliest_departure':
            qs = qs.order_by('departure_time')
        elif sort_by == 'latest_departure':
            qs = qs.order_by('-departure_time')
        else:
            qs = qs.order_by('-departure_date', 'departure_time')

        page = self.request.GET.get('page', 1)
        paginator = Paginator(qs, self.paginate_by)
        flight_list = paginator.get_page(page)

        context = self.get_context_data(form=form, flight_list=flight_list, search_performed=True)
        context['travellers'] = travellers
        context['is_paginated'] = flight_list.has_other_pages()
        context['page_obj'] = flight_list
        context['results_title'] = '{} flight{} found'.format(
            flight_list.paginator.count, 's' if flight_list.paginator.count != 1 else ''
        )
        route_bits = []
        if departure:
            route_bits.append(departure)
        if destination:
            route_bits.append(destination)
        route = ' → '.join(route_bits)
        if departure_date:
            route += f' · {departure_date}'
        context['results_subtitle'] = route or 'Matching flights'
        return self.render_to_response(context)

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, flight_list=Paginator(Flight.objects.none(), self.paginate_by).get_page(1), search_performed=False)
        )

    def get(self, request, *args, **kwargs):
        form = self.form_class(data=request.GET)
        if form.is_valid():
            return self.form_valid(form)
        return self.render_to_response(
            self.get_context_data(form=form, flight_list=Paginator(Flight.objects.none(), self.paginate_by).get_page(1), search_performed=False)
        )


class FlightDetailView(DetailView):
    model = Flight
    template_name = 'flights/detail.html'
    context_object_name = 'flight'
    pk_url_kwarg = 'id'

    def get_queryset(self):
        return Flight.objects.all()


class FlightListView(ListView):
    model = Flight
    template_name = 'flights/results.html'
    context_object_name = 'flight_list'
    paginate_by = 9

    def get_queryset(self):
        return Flight.objects.filter(status__in=['scheduled', 'delayed']).order_by(
            '-departure_date', 'departure_time'
        )
