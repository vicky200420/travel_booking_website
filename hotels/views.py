from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import DetailView, FormView, ListView

from maps import services as map_services

from .forms import HotelSearchForm
from .models import Hotel


class HotelListView(ListView):
    model = Hotel
    template_name = 'hotels/hotel_list.html'
    context_object_name = 'hotel_list'
    paginate_by = 9

    def get_queryset(self):
        return Hotel.objects.filter(active=True).order_by('-featured', '-average_rating', 'name')


class HotelSearchView(FormView):
    template_name = 'hotels/hotel_list.html'
    form_class = HotelSearchForm
    paginate_by = 9

    def form_valid(self, form):
        qs = Hotel.objects.filter(active=True)

        destination = form.cleaned_data.get('destination')
        rooms_req = form.cleaned_data.get('rooms', 1)
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        star_rating = form.cleaned_data.get('star_rating')
        featured = form.cleaned_data.get('featured')
        sort_by = form.cleaned_data.get('sort_by')

        if featured:
            qs = qs.filter(featured=True)
        if star_rating:
            qs = qs.filter(star_rating__gte=star_rating)
        if min_price:
            qs = qs.filter(discounted_price__gte=min_price)
        if max_price:
            qs = qs.filter(discounted_price__lte=max_price)

        amenity_fields = ['wifi', 'pool', 'parking', 'spa', 'gym', 'restaurant', 'ac', 'breakfast', 'pet_friendly']
        for field in amenity_fields:
            val = form.cleaned_data.get(field)
            if val:
                qs = qs.filter(**{field: True})

        if destination:
            qs = qs.filter(
                Q(city__icontains=destination) |
                Q(state__icontains=destination) |
                Q(country__icontains=destination) |
                Q(name__icontains=destination) |
                Q(address__icontains=destination)
            )

        if rooms_req:
            qs = qs.filter(available_rooms__gte=rooms_req)

        sort_map = {
            'price_low': 'discounted_price',
            'price_high': '-discounted_price',
            'rating_high': '-average_rating',
            'newest': '-created_at',
        }
        order = sort_map.get(sort_by)
        if order:
            qs = qs.order_by(order)
        else:
            qs = qs.order_by('-featured', '-average_rating', 'name')

        page = self.request.GET.get('page', 1)
        paginator = Paginator(qs, self.paginate_by)
        hotel_list = paginator.get_page(page)

        context = self.get_context_data(
            form=form,
            hotel_list=hotel_list,
            search_performed=True,
        )
        context['is_paginated'] = hotel_list.has_other_pages()
        context['page_obj'] = hotel_list
        return self.render_to_response(context)

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                hotel_list=Paginator(Hotel.objects.none(), self.paginate_by).get_page(1),
                search_performed=False,
            )
        )

    def get(self, request, *args, **kwargs):
        form = self.form_class(data=request.GET)
        if form.is_valid():
            return self.form_valid(form)
        return self.render_to_response(
            self.get_context_data(
                form=form,
                hotel_list=Paginator(Hotel.objects.none(), self.paginate_by).get_page(1),
                search_performed=False,
            )
        )


class HotelDetailView(DetailView):
    model = Hotel
    template_name = 'hotels/hotel_detail.html'
    context_object_name = 'hotel'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Hotel.objects.filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.object
        context['related_hotels'] = Hotel.objects.filter(
            active=True,
            city=hotel.city
        ).exclude(id=hotel.id)[:4]
        context['gallery_images'] = hotel.gallery.all()

        map_data = map_services.build_hotel_detail_data(hotel)
        context['hotel_marker'] = map_data['marker']
        context['hotel_marker_json'] = map_data['markers_json']
        context['nearby_places'] = map_data['nearby_places']
        context['distance_chips'] = map_data['distance_chips']
        return context
