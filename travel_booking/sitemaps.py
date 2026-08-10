"""Sitemap definitions for public catalogue pages."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from flights.models import Flight
from hotels.models import Hotel
from packages.models import TravelPackage


class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'flights', 'hotel_list', 'package_list']

    def location(self, item):
        return reverse(item)


class HotelSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.6

    def items(self):
        return Hotel.objects.filter(active=True)

    def lastmod(self, obj):
        return obj.updated_at


class PackageSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.6

    def items(self):
        return TravelPackage.objects.filter(active=True)

    def lastmod(self, obj):
        return obj.updated_at


class FlightSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 0.5

    def items(self):
        return Flight.objects.filter(status__in=['scheduled', 'delayed'])

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('flight_detail', args=[obj.id])


sitemaps = {
    'static': StaticSitemap,
    'hotels': HotelSitemap,
    'packages': PackageSitemap,
    'flights': FlightSitemap,
}
