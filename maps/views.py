"""Map & Location Intelligence — views."""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from hotels.models import Hotel
from packages.models import TravelPackage

from . import services, utils


def _get_coords(request):
    return services.to_float(request.GET.get('lat')), services.to_float(request.GET.get('lng'))


def _get_radius(request):
    try:
        return float(request.GET.get('radius') or services.DEFAULT_RADIUS_KM)
    except (TypeError, ValueError):
        return services.DEFAULT_RADIUS_KM


class HotelMapView(TemplateView):
    """Full-screen interactive map of every hotel with location search.

    Supports city / landmark / radius filtering. The full dataset is embedded
    so the client can re-filter instantly without a round trip; initial GET
    params are honoured server-side for shareable URLs.
    """
    template_name = 'maps/hotel_map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hotels = Hotel.objects.filter(active=True)
        city = self.request.GET.get('city', '').strip()
        landmark = self.request.GET.get('landmark', '').strip()
        query = self.request.GET.get('q', '').strip()
        radius = _get_radius(self.request)

        qs = services.filter_hotels(hotels, city=city, landmark=landmark, radius=radius, query=query)
        qs = list(qs)

        markers = [utils.marker_data_with_urls(m) for m in services.build_hotel_list_data(qs) if m]
        all_markers = [
            utils.marker_data_with_urls(m)
            for m in services.build_hotel_list_data(Hotel.objects.filter(active=True)) if m
        ]

        city_options = list(
            Hotel.objects.filter(active=True)
            .exclude(city='')
            .order_by('city')
            .values_list('city', flat=True)
            .distinct()
        )

        context.update({
            'hotels': markers,
            'all_hotels': all_markers,
            'landmarks': services.landmark_index(),
            'city_options': city_options,
            'result_count': len(markers),
            'total_count': len(all_markers),
            'prefill_city': city,
            'prefill_landmark': landmark,
            'prefill_query': query,
            'prefill_radius': radius,
            'filter_active': bool(city or landmark or query),
        })
        return context


class DestinationMapView(TemplateView):
    """Package destination map.

    Without a slug it renders every package destination with clustering; with a
    slug it renders a single destination with nearby attractions and a travel
    route placeholder (suggested airport transfer).
    """
    template_name = 'maps/destination_map.html'

    def get_context_data(self, slug=None, **kwargs):
        context = super().get_context_data(**kwargs)

        if slug:
            package = get_object_or_404(
                TravelPackage.objects.filter(active=True).exclude(latitude__isnull=True),
                slug=slug,
            )
            return self._single_package_context(context, package)

        packages = TravelPackage.objects.filter(active=True).exclude(latitude__isnull=True)
        markers = [utils.marker_data_with_urls(m) for m in services.build_destination_list_data(packages) if m]

        country_groups = {}
        for p in packages:
            country_groups.setdefault(p.country, []).append(p.destination)

        context.update({
            'mode': 'all',
            'destinations': markers,
            'destination_count': len(markers),
            'country_groups': country_groups,
        })
        return context

    def _single_package_context(self, context, package):
        marker = services.build_destination_marker(package)
        marker = utils.marker_data_with_urls(marker) if marker else None
        lat, lng = services.to_float(package.latitude), services.to_float(package.longitude)

        attractions = [
            utils.place_with_urls(p)
            for p in services.get_nearby_places(lat, lng, radius_km=60, category='attraction')
        ]
        grouped = []
        for group in services.get_nearby_grouped(lat, lng, radius_km=60):
            group['places'] = [utils.place_with_urls(p) for p in group['places']]
            grouped.append(group)

        # Travel route placeholder: nearest airport -> destination.
        route = services.package_route(package)

        context.update({
            'mode': 'single',
            'package': package,
            'destinations': [marker] if marker else [],
            'destination_lat': lat,
            'destination_lng': lng,
            'attractions': attractions,
            'nearby_grouped': grouped,
            'route': route,
        })
        return context


class NearbyPlacesApiView(View):
    """JSON API: curated nearby places around an arbitrary coordinate."""

    def get(self, request):
        lat, lng = _get_coords(request)
        if None in (lat, lng):
            return JsonResponse({'error': 'lat and lng query params are required.'}, status=400)
        radius = _get_radius(request)
        category = request.GET.get('category', '').strip() or None
        limit = request.GET.get('limit', '')
        limit = int(limit) if limit.isdigit() else None

        places = services.get_nearby_places(lat, lng, radius_km=radius, category=category, limit=limit)
        places = [utils.place_with_urls(p) for p in places]
        return JsonResponse({'places': places, 'count': len(places), 'radius_km': radius})


class HotelNearbyJsonView(View):
    """JSON API: nearby places for a specific hotel."""

    def get(self, request, slug):
        hotel = get_object_or_404(Hotel, slug=slug, active=True)
        lat, lng = services.to_float(hotel.latitude), services.to_float(hotel.longitude)
        if None in (lat, lng):
            return JsonResponse({'error': 'Hotel has no coordinates.'}, status=400)
        radius = _get_radius(request)
        places = services.get_nearby_places(lat, lng, radius_km=radius)
        places = [utils.place_with_urls(p) for p in places]
        return JsonResponse({
            'hotel': {'name': hotel.name, 'lat': lat, 'lng': lng},
            'places': places,
            'count': len(places),
        })


class LandmarkSearchApiView(View):
    """JSON API: landmark / place autocomplete for location search."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        city = request.GET.get('city', '').strip() or None
        if len(query) < 2:
            return JsonResponse({'results': []})
        results = services.search_landmarks(query, city=city, limit=10)
        return JsonResponse({'results': results})
