"""Google Maps deep-links and distance formatting.

This module has zero imports from the rest of the maps package so it can be
used by `services`, `utils` and third-party apps without circular imports.
"""


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_distance(distance_km, decimals=1):
    """Human friendly distance: '< 100 m' for tiny, 'x.x km' otherwise."""
    if distance_km is None:
        return '—'
    if distance_km < 0.1:
        return f"{max(int(distance_km * 1000), 1)} m"
    return f"{distance_km:.{decimals}f} km"


def _coerce(lat, lng):
    """Accept (lat, lng) tuple or two floats."""
    if isinstance(lat, (tuple, list)) and len(lat) == 2:
        lat, lng = lat
    return _to_float(lat), _to_float(lng)


def google_maps_place_url(lat, lng, name=None):
    """Pin location on Google Maps. Accepts a coordinate tuple or floats."""
    lat, lng = _coerce(lat, lng)
    if None in (lat, lng):
        return None
    query = f"{name}, {lat:.6f},{lng:.6f}" if name else f"{lat:.6f},{lng:.6f}"
    return f"https://www.google.com/maps/search/?api=1&query={query.replace(' ', '+')}"


def google_maps_directions_url(lat, lng, mode='driving'):
    """Open turn-by-turn navigation to a coordinate in Google Maps."""
    lat, lng = _coerce(lat, lng)
    if None in (lat, lng):
        return None
    return (
        f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lng:.6f}"
        f"&travelmode={mode}"
    )


def google_maps_route_url(origin, destination, mode='driving'):
    """Directions between two coordinate tuples."""
    if origin and destination:
        o = f"{origin[0]:.6f},{origin[1]:.6f}"
        d = f"{destination[0]:.6f},{destination[1]:.6f}"
        return f"https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}&travelmode={mode}"
    return None
