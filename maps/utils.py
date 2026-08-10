"""Map & Location Intelligence — presentation helpers.

Formatting, Google Maps deep links and admin helpers. Kept free of model
imports so it can be used safely from templates, admin modules and views.
"""
from django.utils.html import format_html

from .links import (
    format_distance,
    google_maps_directions_url,
    google_maps_place_url,
    google_maps_route_url,
)
from .services import CATEGORY_META, to_float


def place_with_urls(place):
    """Augment a services place dict with display + navigation links."""
    row = dict(place)
    lat, lng = row.get('lat'), row.get('lng')
    row['distance_display'] = format_distance(row.get('distance_km'))
    row['maps_url'] = google_maps_place_url(lat, lng, row.get('name'))
    row['directions_url'] = google_maps_directions_url(lat, lng)
    meta = CATEGORY_META.get(row.get('category'), {})
    row['category_label'] = meta.get('label', row.get('category', '').title())
    row['icon'] = meta.get('icon', 'bi-geo-alt-fill')
    row['color'] = meta.get('color', '#64748B')
    return row


def admin_map_preview_html(lat, lng, title='Map Preview', width=320, height=220):
    """Reusable read-only OpenStreetMap preview for the Django admin."""
    lat, lng = to_float(lat), to_float(lng)
    if None in (lat, lng):
        return format_html(
            '<span style="color:#94a3b8;font-size:12px;">'
            'No coordinates provided — add latitude & longitude to preview.</span>'
        )
    dlat, dlng = 0.008, 0.012
    bbox = f"{lng - dlng:.5f},{lat - dlat:.5f},{lng + dlng:.5f},{lat + dlat:.5f}"
    src = (
        f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}"
        f"&layer=mapnik&marker={lat:.6f},{lng:.6f}"
    )
    return format_html(
        '<div style="margin-bottom:6px;">'
        '<iframe src="{src}" width="{w}" height="{h}" style="border:0;'
        'border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.08);" '
        'loading="lazy" title="{title}"></iframe>'
        '<div style="margin-top:6px;color:#64748b;font-size:12px;">'
        '<strong>{title}:</strong> {lat}, {lng}</div></div>',
        src=src, w=width, h=height, title=title, lat=f"{lat:.6f}", lng=f"{lng:.6f}",
    )


def marker_data_with_urls(marker):
    """Add Google Maps links to a serialized marker dict."""
    row = dict(marker)
    lat, lng = row.get('lat'), row.get('lng')
    if None not in (lat, lng):
        row['maps_url'] = google_maps_place_url(lat, lng, row.get('name'))
        row['directions_url'] = google_maps_directions_url(lat, lng)
    return row


__all__ = [
    'format_distance',
    'google_maps_directions_url',
    'google_maps_place_url',
    'google_maps_route_url',
    'place_with_urls',
    'admin_map_preview_html',
    'marker_data_with_urls',
]
