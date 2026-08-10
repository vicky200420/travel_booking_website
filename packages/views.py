from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import DetailView, FormView, ListView

from maps import services as map_services
from maps import utils as map_utils

from .forms import PackageSearchForm
from .models import TravelPackage


class PackageListView(ListView):
    model = TravelPackage
    template_name = 'packages/package_list.html'
    context_object_name = 'package_list'
    paginate_by = 9

    def get_queryset(self):
        return TravelPackage.objects.filter(active=True).order_by(
            '-featured', '-average_rating', 'title'
        )


class PackageSearchView(FormView):
    template_name = 'packages/package_list.html'
    form_class = PackageSearchForm
    paginate_by = 9

    def form_valid(self, form):
        qs = TravelPackage.objects.filter(active=True)

        destination = form.cleaned_data.get('destination')
        country = form.cleaned_data.get('country')
        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        duration = form.cleaned_data.get('duration')
        min_rating = form.cleaned_data.get('min_rating')
        featured = form.cleaned_data.get('featured')
        sort_by = form.cleaned_data.get('sort_by')

        if featured:
            qs = qs.filter(featured=True)

        if category:
            qs = qs.filter(category=category)

        if min_rating:
            qs = qs.filter(average_rating__gte=min_rating)

        if min_price:
            qs = qs.filter(discounted_price__gte=min_price)

        if max_price:
            qs = qs.filter(discounted_price__lte=max_price)

        if duration:
            if duration == '1_3':
                qs = qs.filter(duration_days__gte=1, duration_days__lte=3)
            elif duration == '4_7':
                qs = qs.filter(duration_days__gte=4, duration_days__lte=7)
            elif duration == '8_14':
                qs = qs.filter(duration_days__gte=8, duration_days__lte=14)
            elif duration == '15+':
                qs = qs.filter(duration_days__gte=15)

        if destination:
            qs = qs.filter(
                Q(destination__icontains=destination) |
                Q(state__icontains=destination) |
                Q(country__icontains=destination) |
                Q(title__icontains=destination)
            )

        if country:
            qs = qs.filter(country__icontains=country)

        sort_map = {
            'price_low': 'discounted_price',
            'price_high': '-discounted_price',
            'rating_high': '-average_rating',
            'most_popular': '-total_reviews',
            'newest': '-created_at',
        }
        order = sort_map.get(sort_by)
        if order:
            qs = qs.order_by(order)
        else:
            qs = qs.order_by('-featured', '-average_rating', 'title')

        page = self.request.GET.get('page', 1)
        paginator = Paginator(qs, self.paginate_by)
        package_list = paginator.get_page(page)

        context = self.get_context_data(
            form=form,
            package_list=package_list,
            search_performed=True,
        )
        context['is_paginated'] = package_list.has_other_pages()
        context['page_obj'] = package_list
        return self.render_to_response(context)

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                package_list=Paginator(TravelPackage.objects.none(), self.paginate_by).get_page(1),
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
                package_list=Paginator(TravelPackage.objects.none(), self.paginate_by).get_page(1),
                search_performed=False,
            )
        )


class PackageDetailView(DetailView):
    model = TravelPackage
    template_name = 'packages/package_detail.html'
    context_object_name = 'package'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return TravelPackage.objects.filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        package = self.object
        context['gallery_images'] = package.gallery.all()
        context['related_packages'] = TravelPackage.objects.filter(
            active=True,
            destination=package.destination
        ).exclude(id=package.id)[:4]

        context['destination_marker'] = None
        context['destination_marker_json'] = ''
        context['route'] = None
        context['route_json'] = ''
        context['attractions'] = []

        lat, lng = map_services.to_float(package.latitude), map_services.to_float(package.longitude)
        if None not in (lat, lng):
            marker = map_services.build_destination_marker(package)
            if marker:
                marker = map_utils.marker_data_with_urls(marker)
                import json
                context['destination_marker'] = marker
                context['destination_marker_json'] = json.dumps([marker], ensure_ascii=False)
            route = map_services.package_route(package)
            if route:
                import json
                context['route'] = route
                context['route_json'] = json.dumps(route, ensure_ascii=False)
            context['attractions'] = [
                map_utils.place_with_urls(p)
                for p in map_services.get_nearby_places(lat, lng, radius_km=60, category='attraction')
            ]
        return context
