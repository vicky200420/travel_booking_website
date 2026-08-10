from django.shortcuts import render

from hotels.models import Hotel
from packages.models import TravelPackage


def home(request):
    """Landing page — surfaces a curated slice of existing catalogue data."""
    featured_packages = TravelPackage.objects.filter(active=True).order_by(
        '-featured', '-average_rating', 'created_at'
    )[:6]

    featured_hotels = Hotel.objects.filter(active=True).order_by(
        '-featured', '-average_rating', 'created_at'
    )[:4]

    # Curated destination tiles from catalogue cities/destinations.
    hotel_destinations = (
        Hotel.objects.filter(active=True)
        .exclude(city='')
        .values_list('city', 'country')
        .distinct()[:6]
    )
    package_destinations = (
        TravelPackage.objects.filter(active=True)
        .exclude(destination='')
        .values_list('destination', 'country')
        .distinct()[:6]
    )
    destinations = list(hotel_destinations) + list(package_destinations)
    # De-duplicate while preserving order.
    seen = set()
    unique_destinations = []
    dest_images = [
        'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1518684079-3c830dcef090?auto=format&fit=crop&w=800&q=80',
        'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80',
    ]
    for i, (city, country) in enumerate(destinations):
        key = (city.strip().lower(), (country or '').strip().lower())
        if key[0] and key not in seen:
            seen.add(key)
            unique_destinations.append({
                'city': city,
                'country': country,
                'image': dest_images[i % len(dest_images)],
            })

    stats = {
        'destinations': unique_destinations[:6] or [],
        'package_count': TravelPackage.objects.filter(active=True).count(),
        'hotel_count': Hotel.objects.filter(active=True).count(),
        'review_count': None,
    }

    context = {
        'featured_packages': featured_packages,
        'featured_hotels': featured_hotels,
        'stats': stats,
    }
    return render(request, 'home/index.html', context)
