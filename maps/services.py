"""Map & Location Intelligence — GIS service layer.

All geographic calculations and point-of-interest lookups live here so the
view layer stays thin and the logic is reusable across hotels, packages and
any future module that needs geo awareness.
"""
import math
import re
from functools import lru_cache

from django.db.models import Q

EARTH_RADIUS_KM = 6371.0088
DEFAULT_RADIUS_KM = 5.0

# ---------------------------------------------------------------- categories

CATEGORY_META = {
    'attraction': {'label': 'Tourist Attractions', 'icon': 'bi-camera-fill', 'color': '#06B6D4'},
    'restaurant': {'label': 'Restaurants', 'icon': 'bi-egg-fried', 'color': '#F59E0B'},
    'hospital': {'label': 'Hospitals', 'icon': 'bi-hospital', 'color': '#EF4444'},
    'atm': {'label': 'ATMs', 'icon': 'bi-cash-coin', 'color': '#10B981'},
    'bus_stop': {'label': 'Bus Stops', 'icon': 'bi-bus-front-fill', 'color': '#8B5CF6'},
    'metro': {'label': 'Metro Stations', 'icon': 'bi-train-front-fill', 'color': '#6366F1'},
    'mall': {'label': 'Shopping Malls', 'icon': 'bi-bag-fill', 'color': '#EC4899'},
    'airport': {'label': 'Airports', 'icon': 'bi-airplane-fill', 'color': '#3B82F6'},
    'railway': {'label': 'Railway Stations', 'icon': 'bi-train-freight-front-fill', 'color': '#14B8A6'},
}

CATEGORY_ORDER = [
    'restaurant', 'hospital', 'atm', 'bus_stop', 'metro', 'mall', 'attraction',
    'airport', 'railway',
]


def category_meta(category):
    return CATEGORY_META.get(category, {'label': category.title(), 'icon': 'bi-geo-alt-fill', 'color': '#64748B'})


# -------------------------------------------------------------- coordinates

def to_float(value):
    """Safely coerce a value (Decimal/str/float) to float or None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres between two coordinates."""
    lat1, lng1, lat2, lng2 = to_float(lat1), to_float(lng1), to_float(lat2), to_float(lng2)
    if None in (lat1, lng1, lat2, lng2):
        return None
    lat1, lng1, lat2, lng2 = map(math.radians, (lat1, lng1, lat2, lng2))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def destination_point(lat, lng, bearing_deg, distance_km):
    """Return the coordinate reached by travelling `distance_km` along `bearing_deg`."""
    lat, lng = to_float(lat), to_float(lng)
    if None in (lat, lng):
        return None
    angular = distance_km / EARTH_RADIUS_KM
    bearing = math.radians(bearing_deg)
    lat1, lng1 = map(math.radians, (lat, lng))
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular) +
        math.cos(lat1) * math.sin(angular) * math.cos(bearing)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return (math.degrees(lat2), math.degrees(lng2))


# ------------------------------------------------------- curated POI registry

# Each city stores a centre coordinate and a curated set of real, verifiable
# points of interest. Coordinates are approximate (WGS84) which is more than
# adequate for the "approximate distances" promised in the UI.
CITY_PLACES = {
    'miami': {
        'center': (25.7617, -80.1918),
        'places': [
            {'name': 'South Beach', 'category': 'attraction', 'lat': 25.7826, 'lng': -80.1296},
            {'name': 'Art Deco Historic District', 'category': 'attraction', 'lat': 25.7840, 'lng': -80.1338},
            {'name': 'Wynwood Walls', 'category': 'attraction', 'lat': 25.8020, 'lng': -80.1989},
            {'name': 'Little Havana', 'category': 'attraction', 'lat': 25.7660, 'lng': -80.2240},
            {'name': 'Miami International Airport', 'category': 'airport', 'lat': 25.7959, 'lng': -80.2870},
            {'name': 'MiamiCentral Station', 'category': 'railway', 'lat': 25.7832, 'lng': -80.1910},
            {'name': "Joe's Stone Crab", 'category': 'restaurant', 'lat': 25.7914, 'lng': -80.1317},
            {'name': 'Versailles Restaurant', 'category': 'restaurant', 'lat': 25.7700, 'lng': -80.2280},
            {'name': 'Mount Sinai Medical Center', 'category': 'hospital', 'lat': 25.7863, 'lng': -80.1272},
            {'name': 'Bayside Marketplace', 'category': 'mall', 'lat': 25.7788, 'lng': -80.1850},
            {'name': 'Brickell City Centre', 'category': 'mall', 'lat': 25.7609, 'lng': -80.1913},
            {'name': 'Government Center Metromover', 'category': 'metro', 'lat': 25.7718, 'lng': -80.1911},
            {'name': 'Lincoln Road Bus Stop', 'category': 'bus_stop', 'lat': 25.7905, 'lng': -80.1370},
            {'name': 'Ocean Drive ATM', 'category': 'atm', 'lat': 25.7800, 'lng': -80.1310},
        ],
    },
    'new york': {
        'center': (40.7484, -73.9857),
        'places': [
            {'name': 'Empire State Building', 'category': 'attraction', 'lat': 40.7484, 'lng': -73.9857},
            {'name': 'Times Square', 'category': 'attraction', 'lat': 40.7580, 'lng': -73.9855},
            {'name': 'Central Park', 'category': 'attraction', 'lat': 40.7829, 'lng': -73.9654},
            {'name': 'Statue of Liberty', 'category': 'attraction', 'lat': 40.6892, 'lng': -74.0445},
            {'name': 'Brooklyn Bridge', 'category': 'attraction', 'lat': 40.7061, 'lng': -73.9969},
            {'name': 'John F. Kennedy Airport', 'category': 'airport', 'lat': 40.6413, 'lng': -73.7781},
            {'name': 'LaGuardia Airport', 'category': 'airport', 'lat': 40.7769, 'lng': -73.8740},
            {'name': 'Grand Central Terminal', 'category': 'railway', 'lat': 40.7527, 'lng': -73.9772},
            {'name': 'Penn Station', 'category': 'railway', 'lat': 40.7506, 'lng': -73.9936},
            {'name': "Katz's Delicatessen", 'category': 'restaurant', 'lat': 40.7222, 'lng': -73.9873},
            {'name': "Grimaldi's Pizza", 'category': 'restaurant', 'lat': 40.7036, 'lng': -73.9860},
            {'name': 'Mount Sinai Hospital', 'category': 'hospital', 'lat': 40.7900, 'lng': -73.9530},
            {'name': 'Rockefeller Center', 'category': 'attraction', 'lat': 40.7587, 'lng': -73.9787},
            {'name': 'Herald Square Station', 'category': 'metro', 'lat': 40.7499, 'lng': -73.9870},
            {'name': 'Fifth Avenue Shopping District', 'category': 'mall', 'lat': 40.7580, 'lng': -73.9770},
            {'name': 'Fifth Avenue ATM', 'category': 'atm', 'lat': 40.7510, 'lng': -73.9770},
        ],
    },
    'cancun': {
        'center': (21.1619, -86.8515),
        'places': [
            {'name': 'Hotel Zone Beaches', 'category': 'attraction', 'lat': 21.1200, 'lng': -86.7670},
            {'name': 'El Rey Ruins', 'category': 'attraction', 'lat': 21.0740, 'lng': -86.7740},
            {'name': 'Playa Delfines', 'category': 'attraction', 'lat': 21.0670, 'lng': -86.7820},
            {'name': 'Mercado 28', 'category': 'attraction', 'lat': 21.1612, 'lng': -86.8235},
            {'name': 'Cancun International Airport', 'category': 'airport', 'lat': 21.0365, 'lng': -86.8771},
            {'name': 'ADO Bus Terminal', 'category': 'bus_stop', 'lat': 21.1580, 'lng': -86.8390},
            {'name': 'La Casa de las Islas', 'category': 'restaurant', 'lat': 21.1620, 'lng': -86.8170},
            {'name': 'El Tigre y El Toro', 'category': 'restaurant', 'lat': 21.1590, 'lng': -86.8190},
            {'name': 'Hospital General de Cancún', 'category': 'hospital', 'lat': 21.1690, 'lng': -86.8460},
            {'name': 'Plaza Las Américas', 'category': 'mall', 'lat': 21.1560, 'lng': -86.8250},
            {'name': 'Downtown ATM', 'category': 'atm', 'lat': 21.1590, 'lng': -86.8240},
        ],
    },
    'zurich': {
        'center': (47.3769, 8.5417),
        'places': [
            {'name': 'Bahnhofstrasse', 'category': 'attraction', 'lat': 47.3700, 'lng': 8.5400},
            {'name': 'Grossmünster', 'category': 'attraction', 'lat': 47.3700, 'lng': 8.5440},
            {'name': 'Lake Zurich Promenade', 'category': 'attraction', 'lat': 47.3630, 'lng': 8.5480},
            {'name': 'Lindenhof', 'category': 'attraction', 'lat': 47.3720, 'lng': 8.5410},
            {'name': 'Zurich Airport', 'category': 'airport', 'lat': 47.4647, 'lng': 8.5492},
            {'name': 'Zürich Hauptbahnhof', 'category': 'railway', 'lat': 47.3775, 'lng': 8.5402},
            {'name': 'Zeughauskeller', 'category': 'restaurant', 'lat': 47.3736, 'lng': 8.5420},
            {'name': 'Confiserie Sprüngli', 'category': 'restaurant', 'lat': 47.3710, 'lng': 8.5390},
            {'name': 'Universitätsspital Zürich', 'category': 'hospital', 'lat': 47.3790, 'lng': 8.5480},
            {'name': 'Sihlcity', 'category': 'mall', 'lat': 47.3650, 'lng': 8.5260},
            {'name': 'Paradeplatz Tram Stop', 'category': 'bus_stop', 'lat': 47.3680, 'lng': 8.5390},
            {'name': 'Central Tram Station', 'category': 'metro', 'lat': 47.3765, 'lng': 8.5440},
            {'name': 'Hauptbahnhof ATM', 'category': 'atm', 'lat': 47.3778, 'lng': 8.5400},
        ],
    },
    'tokyo': {
        'center': (35.6580, 139.7016),
        'places': [
            {'name': 'Shibuya Crossing', 'category': 'attraction', 'lat': 35.6595, 'lng': 139.7005},
            {'name': 'Sensō-ji Temple', 'category': 'attraction', 'lat': 35.7148, 'lng': 139.7967},
            {'name': 'Tokyo Tower', 'category': 'attraction', 'lat': 35.6586, 'lng': 139.7454},
            {'name': 'Meiji Shrine', 'category': 'attraction', 'lat': 35.6764, 'lng': 139.6993},
            {'name': 'Tokyo Skytree', 'category': 'attraction', 'lat': 35.7101, 'lng': 139.8107},
            {'name': 'Haneda Airport', 'category': 'airport', 'lat': 35.5494, 'lng': 139.7798},
            {'name': 'Narita International Airport', 'category': 'airport', 'lat': 35.7720, 'lng': 140.3929},
            {'name': 'Tokyo Station', 'category': 'railway', 'lat': 35.6812, 'lng': 139.7671},
            {'name': 'Shibuya Station', 'category': 'metro', 'lat': 35.6580, 'lng': 139.7016},
            {'name': 'Shinjuku Station', 'category': 'metro', 'lat': 35.6896, 'lng': 139.7006},
            {'name': 'Ichiran Shibuya', 'category': 'restaurant', 'lat': 35.6610, 'lng': 139.7000},
            {'name': 'Sukiyabashi Jiro', 'category': 'restaurant', 'lat': 35.6720, 'lng': 139.7680},
            {'name': 'Tokyo Metropolitan Hospital', 'category': 'hospital', 'lat': 35.6490, 'lng': 139.6690},
            {'name': 'Ginza Six', 'category': 'mall', 'lat': 35.6700, 'lng': 139.7640},
            {'name': 'Harajuku Bus Stop', 'category': 'bus_stop', 'lat': 35.6690, 'lng': 139.7040},
            {'name': 'Ginza District ATM', 'category': 'atm', 'lat': 35.6720, 'lng': 139.7650},
        ],
    },
    'paris': {
        'center': (48.8683, 2.3290),
        'places': [
            {'name': 'Eiffel Tower', 'category': 'attraction', 'lat': 48.8584, 'lng': 2.2945},
            {'name': 'Louvre Museum', 'category': 'attraction', 'lat': 48.8606, 'lng': 2.3376},
            {'name': 'Notre-Dame Cathedral', 'category': 'attraction', 'lat': 48.8530, 'lng': 2.3499},
            {'name': 'Champs-Élysées', 'category': 'attraction', 'lat': 48.8698, 'lng': 2.3077},
            {'name': 'Arc de Triomphe', 'category': 'attraction', 'lat': 48.8738, 'lng': 2.2950},
            {'name': 'Charles de Gaulle Airport', 'category': 'airport', 'lat': 49.0097, 'lng': 2.5479},
            {'name': 'Orly Airport', 'category': 'airport', 'lat': 48.7262, 'lng': 2.3652},
            {'name': 'Gare du Nord', 'category': 'railway', 'lat': 48.8809, 'lng': 2.3553},
            {'name': 'Gare de Lyon', 'category': 'railway', 'lat': 48.8441, 'lng': 2.3737},
            {'name': 'Café de Flore', 'category': 'restaurant', 'lat': 48.8534, 'lng': 2.3320},
            {'name': 'Le Meurice', 'category': 'restaurant', 'lat': 48.8655, 'lng': 2.3275},
            {'name': 'Hôtel-Dieu de Paris', 'category': 'hospital', 'lat': 48.8520, 'lng': 2.3490},
            {'name': 'Galeries Lafayette', 'category': 'mall', 'lat': 48.8738, 'lng': 2.3320},
            {'name': 'Louvre-Rivoli Metro', 'category': 'metro', 'lat': 48.8600, 'lng': 2.3400},
            {'name': 'Opéra Garnier', 'category': 'attraction', 'lat': 48.8720, 'lng': 2.3316},
            {'name': 'Opéra ATM', 'category': 'atm', 'lat': 48.8710, 'lng': 2.3310},
        ],
    },
    'dubai': {
        'center': (24.7136, 55.1673),
        'places': [
            {'name': 'Burj Khalifa', 'category': 'attraction', 'lat': 25.1972, 'lng': 55.2744},
            {'name': 'Palm Jumeirah', 'category': 'attraction', 'lat': 25.1124, 'lng': 55.1390},
            {'name': 'Dubai Marina', 'category': 'attraction', 'lat': 25.0806, 'lng': 55.1403},
            {'name': 'Gold Souk', 'category': 'attraction', 'lat': 25.2680, 'lng': 55.2970},
            {'name': 'Dubai International Airport', 'category': 'airport', 'lat': 25.2532, 'lng': 55.3657},
            {'name': 'Union Metro Station', 'category': 'metro', 'lat': 25.2615, 'lng': 55.2985},
            {'name': 'Dubai Mall Metro Station', 'category': 'metro', 'lat': 25.1967, 'lng': 55.2790},
            {'name': 'Pierchic', 'category': 'restaurant', 'lat': 25.1320, 'lng': 55.1850},
            {'name': 'Al Fanar Restaurant', 'category': 'restaurant', 'lat': 25.2150, 'lng': 55.2870},
            {'name': 'Rashid Hospital', 'category': 'hospital', 'lat': 25.2610, 'lng': 55.3120},
            {'name': 'Dubai Mall', 'category': 'mall', 'lat': 25.1975, 'lng': 55.2796},
            {'name': 'Deira City Centre', 'category': 'mall', 'lat': 25.2490, 'lng': 55.3250},
            {'name': 'Dubai Bus Station', 'category': 'bus_stop', 'lat': 25.2670, 'lng': 55.3000},
            {'name': 'Dubai Creek ATM', 'category': 'atm', 'lat': 25.2570, 'lng': 55.3020},
        ],
    },
    'sydney': {
        'center': (-33.8568, 151.2153),
        'places': [
            {'name': 'Sydney Opera House', 'category': 'attraction', 'lat': -33.8568, 'lng': 151.2153},
            {'name': 'Sydney Harbour Bridge', 'category': 'attraction', 'lat': -33.8523, 'lng': 151.2108},
            {'name': 'Bondi Beach', 'category': 'attraction', 'lat': -33.8915, 'lng': 151.2767},
            {'name': 'Darling Harbour', 'category': 'attraction', 'lat': -33.8731, 'lng': 151.1989},
            {'name': 'Royal Botanic Garden', 'category': 'attraction', 'lat': -33.8630, 'lng': 151.2160},
            {'name': 'Sydney Kingsford Smith Airport', 'category': 'airport', 'lat': -33.9399, 'lng': 151.1753},
            {'name': 'Central Station', 'category': 'railway', 'lat': -33.8832, 'lng': 151.2066},
            {'name': 'Circular Quay Station', 'category': 'railway', 'lat': -33.8617, 'lng': 151.2108},
            {'name': 'Quay Restaurant', 'category': 'restaurant', 'lat': -33.8570, 'lng': 151.2130},
            {'name': "Tetsuya's", 'category': 'restaurant', 'lat': -33.8710, 'lng': 151.2040},
            {'name': 'Royal Prince Alfred Hospital', 'category': 'hospital', 'lat': -33.8850, 'lng': 151.1800},
            {'name': 'Westfield Sydney', 'category': 'mall', 'lat': -33.8715, 'lng': 151.2085},
            {'name': 'Town Hall Station', 'category': 'metro', 'lat': -33.8731, 'lng': 151.2066},
            {'name': 'Pitt Street ATM', 'category': 'atm', 'lat': -33.8690, 'lng': 151.2080},
            {'name': 'CBD Bus Stop', 'category': 'bus_stop', 'lat': -33.8680, 'lng': 151.2070},
        ],
    },
    'jaipur': {
        'center': (26.9852, 75.8516),
        'places': [
            {'name': 'Amber Fort', 'category': 'attraction', 'lat': 26.9850, 'lng': 75.8510},
            {'name': 'Hawa Mahal', 'category': 'attraction', 'lat': 26.9239, 'lng': 75.8267},
            {'name': 'City Palace', 'category': 'attraction', 'lat': 26.9258, 'lng': 75.8237},
            {'name': 'Jantar Mantar', 'category': 'attraction', 'lat': 26.9247, 'lng': 75.8246},
            {'name': 'Jaipur International Airport', 'category': 'airport', 'lat': 26.8245, 'lng': 75.8122},
            {'name': 'Jaipur Junction Station', 'category': 'railway', 'lat': 26.9183, 'lng': 75.7870},
            {'name': 'Laxmi Misthan Bhandar', 'category': 'restaurant', 'lat': 26.9210, 'lng': 75.8260},
            {'name': 'Chokhi Dhani', 'category': 'restaurant', 'lat': 26.8560, 'lng': 75.9020},
            {'name': 'Sawai Man Singh Hospital', 'category': 'hospital', 'lat': 26.8930, 'lng': 75.8210},
            {'name': 'World Trade Park', 'category': 'mall', 'lat': 26.8550, 'lng': 75.8060},
            {'name': 'Johari Bazaar', 'category': 'attraction', 'lat': 26.9180, 'lng': 75.8200},
            {'name': 'City Bus Stand', 'category': 'bus_stop', 'lat': 26.9220, 'lng': 75.7970},
            {'name': 'Sanganeri Gate ATM', 'category': 'atm', 'lat': 26.9100, 'lng': 75.8050},
        ],
    },
    'bergen': {
        'center': (60.3913, 5.3221),
        'places': [
            {'name': 'Bryggen Wharf', 'category': 'attraction', 'lat': 60.3970, 'lng': 5.3240},
            {'name': 'Fløibanen Funicular', 'category': 'attraction', 'lat': 60.3950, 'lng': 5.3300},
            {'name': 'Bergenhus Fortress', 'category': 'attraction', 'lat': 60.4000, 'lng': 5.3170},
            {'name': 'Fish Market', 'category': 'attraction', 'lat': 60.3930, 'lng': 5.3230},
            {'name': 'Bergen Airport', 'category': 'airport', 'lat': 60.2926, 'lng': 5.2181},
            {'name': 'Bergen Station', 'category': 'railway', 'lat': 60.3896, 'lng': 5.3290},
            {'name': 'To Søstre', 'category': 'restaurant', 'lat': 60.3940, 'lng': 5.3190},
            {'name': 'Bryggen Restaurant', 'category': 'restaurant', 'lat': 60.3975, 'lng': 5.3240},
            {'name': 'Haukeland University Hospital', 'category': 'hospital', 'lat': 60.3730, 'lng': 5.3610},
            {'name': 'Galleriet', 'category': 'mall', 'lat': 60.3890, 'lng': 5.3300},
            {'name': 'Bergen Bus Station', 'category': 'bus_stop', 'lat': 60.3890, 'lng': 5.3270},
            {'name': 'Torget ATM', 'category': 'atm', 'lat': 60.3930, 'lng': 5.3240},
        ],
    },
    'bali': {
        'center': (-8.6181, 115.0885),
        'places': [
            {'name': 'Tanah Lot Temple', 'category': 'attraction', 'lat': -8.6210, 'lng': 115.0860},
            {'name': 'Nirwana Bali Golf', 'category': 'attraction', 'lat': -8.6330, 'lng': 115.1020},
            {'name': 'Alas Kedaton Monkey Forest', 'category': 'attraction', 'lat': -8.5540, 'lng': 115.1570},
            {'name': 'Tabanan Market', 'category': 'attraction', 'lat': -8.5410, 'lng': 115.1240},
            {'name': 'Ngurah Rai International Airport', 'category': 'airport', 'lat': -8.7482, 'lng': 115.1670},
            {'name': 'Sari Restaurant', 'category': 'restaurant', 'lat': -8.6200, 'lng': 115.0900},
            {'name': 'RSU Tabanan Hospital', 'category': 'hospital', 'lat': -8.5440, 'lng': 115.1280},
            {'name': 'Tabanan Bus Terminal', 'category': 'bus_stop', 'lat': -8.5380, 'lng': 115.1240},
            {'name': 'Tanah Lot ATM', 'category': 'atm', 'lat': -8.6190, 'lng': 115.0870},
        ],
    },
    'bangkok': {
        'center': (13.7367, 100.5604),
        'places': [
            {'name': 'Grand Palace', 'category': 'attraction', 'lat': 13.7500, 'lng': 100.4913},
            {'name': 'Wat Arun', 'category': 'attraction', 'lat': 13.7437, 'lng': 100.4888},
            {'name': 'Chatuchak Weekend Market', 'category': 'attraction', 'lat': 13.7987, 'lng': 100.5510},
            {'name': 'Khao San Road', 'category': 'attraction', 'lat': 13.7592, 'lng': 100.4973},
            {'name': 'Suvarnabhumi Airport', 'category': 'airport', 'lat': 13.6900, 'lng': 100.7501},
            {'name': 'Don Mueang Airport', 'category': 'airport', 'lat': 13.9094, 'lng': 100.6068},
            {'name': 'Hua Lamphong Station', 'category': 'railway', 'lat': 13.7390, 'lng': 100.5170},
            {'name': 'Thip Samai Pad Thai', 'category': 'restaurant', 'lat': 13.7580, 'lng': 100.5010},
            {'name': 'Siam Paragon', 'category': 'mall', 'lat': 13.7460, 'lng': 100.5350},
            {'name': 'Terminal 21', 'category': 'mall', 'lat': 13.7390, 'lng': 100.5600},
            {'name': 'Siriraj Hospital', 'category': 'hospital', 'lat': 13.7600, 'lng': 100.4850},
            {'name': 'BTS Siam Station', 'category': 'metro', 'lat': 13.7454, 'lng': 100.5340},
            {'name': 'Ekkamai Bus Terminal', 'category': 'bus_stop', 'lat': 13.7200, 'lng': 100.5840},
            {'name': 'Asok BTS ATM', 'category': 'atm', 'lat': 13.7370, 'lng': 100.5600},
        ],
    },
    'tuscany': {
        'center': (43.0587, 11.4892),
        'places': [
            {'name': 'Fortezza di Montalcino', 'category': 'attraction', 'lat': 43.0570, 'lng': 11.4880},
            {'name': 'Abbazia di Sant\'Antimo', 'category': 'attraction', 'lat': 43.0300, 'lng': 11.5220},
            {'name': 'Castello Banfi Winery', 'category': 'attraction', 'lat': 43.0930, 'lng': 11.4920},
            {'name': 'Piazza del Campo, Siena', 'category': 'attraction', 'lat': 43.3186, 'lng': 11.3312},
            {'name': 'Florence Peretola Airport', 'category': 'airport', 'lat': 43.8080, 'lng': 11.2020},
            {'name': 'Siena Station', 'category': 'railway', 'lat': 43.3330, 'lng': 11.3250},
            {'name': 'Trattoria Il Moro', 'category': 'restaurant', 'lat': 43.0590, 'lng': 11.4900},
            {'name': 'Ospedale di Montalcino', 'category': 'hospital', 'lat': 43.0610, 'lng': 11.4880},
            {'name': 'Montalcino Bus Stop', 'category': 'bus_stop', 'lat': 43.0585, 'lng': 11.4890},
            {'name': 'Piazza del Popolo ATM', 'category': 'atm', 'lat': 43.0580, 'lng': 11.4870},
        ],
    },
    'nairobi': {
        'center': (-1.3701, 36.7503),
        'places': [
            {'name': 'Nairobi National Park', 'category': 'attraction', 'lat': -1.3670, 'lng': 36.8580},
            {'name': 'Giraffe Centre', 'category': 'attraction', 'lat': -1.3420, 'lng': 36.7650},
            {'name': 'David Sheldrick Elephant Orphanage', 'category': 'attraction', 'lat': -1.3400, 'lng': 36.7700},
            {'name': 'Nairobi National Museum', 'category': 'attraction', 'lat': -1.2740, 'lng': 36.8050},
            {'name': 'Jomo Kenyatta International Airport', 'category': 'airport', 'lat': -1.3192, 'lng': 36.9278},
            {'name': 'Nairobi Railway Station', 'category': 'railway', 'lat': -1.2880, 'lng': 36.8250},
            {'name': 'Carnivore Restaurant', 'category': 'restaurant', 'lat': -1.3230, 'lng': 36.7980},
            {'name': 'The Talisman Restaurant', 'category': 'restaurant', 'lat': -1.2690, 'lng': 36.8050},
            {'name': 'Kenyatta National Hospital', 'category': 'hospital', 'lat': -1.3000, 'lng': 36.8070},
            {'name': 'Village Market', 'category': 'mall', 'lat': -1.2280, 'lng': 36.8280},
            {'name': 'Sarit Centre', 'category': 'mall', 'lat': -1.2650, 'lng': 36.8010},
            {'name': 'Kenyatta Avenue ATM', 'category': 'atm', 'lat': -1.2860, 'lng': 36.8220},
            {'name': 'CBD Bus Stop', 'category': 'bus_stop', 'lat': -1.2830, 'lng': 36.8190},
        ],
    },
    'cape town': {
        'center': (-33.9249, 18.4241),
        'places': [
            {'name': 'Table Mountain', 'category': 'attraction', 'lat': -33.9628, 'lng': 18.4098},
            {'name': 'V&A Waterfront', 'category': 'attraction', 'lat': -33.9055, 'lng': 18.4200},
            {'name': 'Cape Point', 'category': 'attraction', 'lat': -34.3566, 'lng': 18.4960},
            {'name': 'Boulders Beach Penguins', 'category': 'attraction', 'lat': -34.3540, 'lng': 18.4540},
            {'name': 'Cape Town International Airport', 'category': 'airport', 'lat': -33.9714, 'lng': 18.6021},
            {'name': 'Cape Town Station', 'category': 'railway', 'lat': -33.9210, 'lng': 18.4270},
            {'name': 'The Test Kitchen', 'category': 'restaurant', 'lat': -33.9200, 'lng': 18.4500},
            {'name': 'Groote Schuur Hospital', 'category': 'hospital', 'lat': -33.9460, 'lng': 18.4660},
            {'name': 'Canal Walk', 'category': 'mall', 'lat': -33.8950, 'lng': 18.5100},
            {'name': 'Cavendish Square', 'category': 'mall', 'lat': -33.9760, 'lng': 18.4500},
            {'name': 'MyCiTi Bus Station', 'category': 'bus_stop', 'lat': -33.9190, 'lng': 18.4230},
            {'name': 'Adderley Street ATM', 'category': 'atm', 'lat': -33.9230, 'lng': 18.4230},
        ],
    },
    'male': {
        'center': (4.1755, 73.5093),
        'places': [
            {'name': 'Artificial Beach', 'category': 'attraction', 'lat': 4.1740, 'lng': 73.5120},
            {'name': 'Sultan Park', 'category': 'attraction', 'lat': 4.1770, 'lng': 73.5100},
            {'name': 'Old Friday Mosque', 'category': 'attraction', 'lat': 4.1770, 'lng': 73.5090},
            {'name': 'Velana International Airport', 'category': 'airport', 'lat': 4.1910, 'lng': 73.5290},
            {'name': 'Hulhulé Ferry Terminal', 'category': 'bus_stop', 'lat': 4.2120, 'lng': 73.5410},
            {'name': 'Sea House Café', 'category': 'restaurant', 'lat': 4.1770, 'lng': 73.5100},
            {'name': 'ADK Hospital', 'category': 'hospital', 'lat': 4.1750, 'lng': 73.5100},
            {'name': 'STO Trade Centre', 'category': 'mall', 'lat': 4.1780, 'lng': 73.5130},
            {'name': 'Boduthakurufaanu Magu ATM', 'category': 'atm', 'lat': 4.1760, 'lng': 73.5110},
        ],
    },
    'reykjavik': {
        'center': (64.1466, -21.9426),
        'places': [
            {'name': 'Hallgrímskirkja', 'category': 'attraction', 'lat': 64.1416, 'lng': -21.9265},
            {'name': 'Harpa Concert Hall', 'category': 'attraction', 'lat': 64.1500, 'lng': -21.9320},
            {'name': 'Perlan', 'category': 'attraction', 'lat': 64.1290, 'lng': -21.9180},
            {'name': 'Sun Voyager', 'category': 'attraction', 'lat': 64.1480, 'lng': -21.9220},
            {'name': 'Keflavík Airport', 'category': 'airport', 'lat': 63.9850, 'lng': -22.6056},
            {'name': 'BSÍ Bus Terminal', 'category': 'bus_stop', 'lat': 64.1370, 'lng': -21.9230},
            {'name': 'The Coocoo\'s Nest', 'category': 'restaurant', 'lat': 64.1410, 'lng': -21.9430},
            {'name': 'Landspítali Hospital', 'category': 'hospital', 'lat': 64.1340, 'lng': -21.9430},
            {'name': 'Kringlan Mall', 'category': 'mall', 'lat': 64.1310, 'lng': -21.9010},
            {'name': 'Laugavegur ATM', 'category': 'atm', 'lat': 64.1450, 'lng': -21.9330},
        ],
    },
    'interlaken': {
        'center': (46.6863, 7.8632),
        'places': [
            {'name': 'Harder Kulm', 'category': 'attraction', 'lat': 46.6910, 'lng': 7.8480},
            {'name': 'Höhematte Park', 'category': 'attraction', 'lat': 46.6850, 'lng': 7.8580},
            {'name': 'Lake Brienz', 'category': 'attraction', 'lat': 46.7200, 'lng': 7.9800},
            {'name': 'Lake Thun', 'category': 'attraction', 'lat': 46.6900, 'lng': 7.7200},
            {'name': 'Bern-Belp Airport', 'category': 'airport', 'lat': 46.9141, 'lng': 7.4972},
            {'name': 'Interlaken Ost Station', 'category': 'railway', 'lat': 46.6900, 'lng': 7.8680},
            {'name': 'Interlaken West Station', 'category': 'railway', 'lat': 46.6830, 'lng': 7.8520},
            {'name': 'Hüsi Bierhaus', 'category': 'restaurant', 'lat': 46.6850, 'lng': 7.8530},
            {'name': 'Spital Interlaken', 'category': 'hospital', 'lat': 46.6870, 'lng': 7.8690},
            {'name': 'Höheweg ATM', 'category': 'atm', 'lat': 46.6850, 'lng': 7.8590},
            {'name': 'Interlaken West Bus Stop', 'category': 'bus_stop', 'lat': 46.6840, 'lng': 7.8520},
        ],
    },
    'athens': {
        'center': (37.9838, 23.7275),
        'places': [
            {'name': 'Acropolis', 'category': 'attraction', 'lat': 37.9715, 'lng': 23.7267},
            {'name': 'Plaka District', 'category': 'attraction', 'lat': 37.9720, 'lng': 23.7290},
            {'name': 'Syntagma Square', 'category': 'attraction', 'lat': 37.9750, 'lng': 23.7340},
            {'name': 'Monastiraki Flea Market', 'category': 'attraction', 'lat': 37.9760, 'lng': 23.7260},
            {'name': 'Athens International Airport', 'category': 'airport', 'lat': 37.9364, 'lng': 23.9445},
            {'name': 'Athens Railway Station', 'category': 'railway', 'lat': 37.9930, 'lng': 23.7200},
            {'name': 'Dionysos Zonar\'s', 'category': 'restaurant', 'lat': 37.9720, 'lng': 23.7250},
            {'name': 'Evangelismos Hospital', 'category': 'hospital', 'lat': 37.9770, 'lng': 23.7500},
            {'name': 'The Mall Athens', 'category': 'mall', 'lat': 38.0160, 'lng': 23.7600},
            {'name': 'Acropolis Metro Station', 'category': 'metro', 'lat': 37.9680, 'lng': 23.7290},
            {'name': 'Syntagma Bus Stop', 'category': 'bus_stop', 'lat': 37.9740, 'lng': 23.7350},
            {'name': 'Syntagma ATM', 'category': 'atm', 'lat': 37.9750, 'lng': 23.7340},
        ],
    },
    'leh': {
        'center': (34.1526, 77.5771),
        'places': [
            {'name': 'Leh Palace', 'category': 'attraction', 'lat': 34.1650, 'lng': 77.5870},
            {'name': 'Shanti Stupa', 'category': 'attraction', 'lat': 34.1690, 'lng': 77.5740},
            {'name': 'Thiksey Monastery', 'category': 'attraction', 'lat': 34.0580, 'lng': 77.6660},
            {'name': 'Leh Main Bazaar', 'category': 'attraction', 'lat': 34.1640, 'lng': 77.5850},
            {'name': 'Leh Kushok Bakula Airport', 'category': 'airport', 'lat': 34.1359, 'lng': 77.5465},
            {'name': 'SNM Hospital', 'category': 'hospital', 'lat': 34.1600, 'lng': 77.5800},
            {'name': 'The Tibetan Kitchen', 'category': 'restaurant', 'lat': 34.1620, 'lng': 77.5830},
            {'name': 'Leh Bus Stand', 'category': 'bus_stop', 'lat': 34.1580, 'lng': 77.5700},
            {'name': 'J&K Bank ATM', 'category': 'atm', 'lat': 34.1630, 'lng': 77.5840},
        ],
    },
    'santorini': {
        'center': (36.3932, 25.4615),
        'places': [
            {'name': 'Oia Village', 'category': 'attraction', 'lat': 36.4610, 'lng': 25.3760},
            {'name': 'Red Beach', 'category': 'attraction', 'lat': 36.3590, 'lng': 25.3990},
            {'name': 'Fira Town', 'category': 'attraction', 'lat': 36.4190, 'lng': 25.4330},
            {'name': 'Akrotiri Ruins', 'category': 'attraction', 'lat': 36.3520, 'lng': 25.4010},
            {'name': 'Santorini Airport', 'category': 'airport', 'lat': 36.3996, 'lng': 25.4794},
            {'name': 'Athinios Port', 'category': 'bus_stop', 'lat': 36.4130, 'lng': 25.3940},
            {'name': 'Metaxi Mas Tavern', 'category': 'restaurant', 'lat': 36.3710, 'lng': 25.4390},
            {'name': 'Santorini Hospital', 'category': 'hospital', 'lat': 36.4170, 'lng': 25.4310},
            {'name': 'Fira Bus Station', 'category': 'bus_stop', 'lat': 36.4180, 'lng': 25.4310},
            {'name': 'Fira ATM', 'category': 'atm', 'lat': 36.4200, 'lng': 25.4330},
        ],
    },
    'ubud': {
        'center': (-8.5069, 115.2625),
        'places': [
            {'name': 'Sacred Monkey Forest', 'category': 'attraction', 'lat': -8.5180, 'lng': 115.2580},
            {'name': 'Tegalalang Rice Terraces', 'category': 'attraction', 'lat': -8.4310, 'lng': 115.2760},
            {'name': 'Ubud Palace', 'category': 'attraction', 'lat': -8.5060, 'lng': 115.2620},
            {'name': 'Campuhan Ridge Walk', 'category': 'attraction', 'lat': -8.4990, 'lng': 115.2590},
            {'name': 'Ubud Market', 'category': 'attraction', 'lat': -8.5068, 'lng': 115.2623},
            {'name': 'Ngurah Rai International Airport', 'category': 'airport', 'lat': -8.7482, 'lng': 115.1670},
            {'name': 'Locavore', 'category': 'restaurant', 'lat': -8.5090, 'lng': 115.2650},
            {'name': 'Ubud Clinic', 'category': 'hospital', 'lat': -8.5080, 'lng': 115.2600},
            {'name': 'Ubud Shuttle Stop', 'category': 'bus_stop', 'lat': -8.5070, 'lng': 115.2610},
            {'name': 'BCA ATM Ubud', 'category': 'atm', 'lat': -8.5070, 'lng': 115.2630},
        ],
    },
    'san jose': {
        'center': (9.9281, -84.0907),
        'places': [
            {'name': 'National Theater', 'category': 'attraction', 'lat': 9.9330, 'lng': -84.0760},
            {'name': 'Museo Nacional', 'category': 'attraction', 'lat': 9.9330, 'lng': -84.0710},
            {'name': 'Mercado Central', 'category': 'attraction', 'lat': 9.9340, 'lng': -84.0820},
            {'name': 'Juan Santamaría Airport', 'category': 'airport', 'lat': 9.9939, 'lng': -84.2088},
            {'name': 'Estación del Atlántico', 'category': 'railway', 'lat': 9.9370, 'lng': -84.0770},
            {'name': 'Café Mundo', 'category': 'restaurant', 'lat': 9.9340, 'lng': -84.0840},
            {'name': 'Hospital Calderón Guardia', 'category': 'hospital', 'lat': 9.9350, 'lng': -84.0620},
            {'name': 'Multiplaza Escazú', 'category': 'mall', 'lat': 9.9390, 'lng': -84.1410},
            {'name': 'San José Bus Terminal', 'category': 'bus_stop', 'lat': 9.9330, 'lng': -84.0810},
            {'name': 'Avenida Central ATM', 'category': 'atm', 'lat': 9.9330, 'lng': -84.0790},
        ],
    },
    'edinburgh': {
        'center': (55.9533, -3.1883),
        'places': [
            {'name': 'Edinburgh Castle', 'category': 'attraction', 'lat': 55.9486, 'lng': -3.1999},
            {'name': 'Arthur\'s Seat', 'category': 'attraction', 'lat': 55.9444, 'lng': -3.1616},
            {'name': 'Royal Mile', 'category': 'attraction', 'lat': 55.9500, 'lng': -3.1890},
            {'name': 'Palace of Holyroodhouse', 'category': 'attraction', 'lat': 55.9525, 'lng': -3.1724},
            {'name': 'Edinburgh Airport', 'category': 'airport', 'lat': 55.9502, 'lng': -3.3633},
            {'name': 'Waverley Station', 'category': 'railway', 'lat': 55.9521, 'lng': -3.1890},
            {'name': 'The Witchery', 'category': 'restaurant', 'lat': 55.9490, 'lng': -3.1950},
            {'name': 'Royal Infirmary of Edinburgh', 'category': 'hospital', 'lat': 55.9230, 'lng': -3.1400},
            {'name': 'St James Quarter', 'category': 'mall', 'lat': 55.9540, 'lng': -3.1900},
            {'name': 'Princes Street Bus Stop', 'category': 'bus_stop', 'lat': 55.9525, 'lng': -3.1900},
            {'name': 'Princes Street ATM', 'category': 'atm', 'lat': 55.9520, 'lng': -3.1950},
        ],
    },
    'port blair': {
        'center': (11.6234, 92.7265),
        'places': [
            {'name': 'Cellular Jail', 'category': 'attraction', 'lat': 11.6240, 'lng': 92.7290},
            {'name': 'Corbyn\'s Cove Beach', 'category': 'attraction', 'lat': 11.6470, 'lng': 92.7520},
            {'name': 'Ross Island', 'category': 'attraction', 'lat': 11.6720, 'lng': 92.7650},
            {'name': 'Chidiya Tapu', 'category': 'attraction', 'lat': 11.4930, 'lng': 92.7020},
            {'name': 'Veer Savarkar Airport', 'category': 'airport', 'lat': 11.6410, 'lng': 92.7320},
            {'name': 'Phoenix Bay Jetty', 'category': 'bus_stop', 'lat': 11.6620, 'lng': 92.7350},
            {'name': 'New Lighthouse Restaurant', 'category': 'restaurant', 'lat': 11.6690, 'lng': 92.7430},
            {'name': 'GB Pant Hospital', 'category': 'hospital', 'lat': 11.6640, 'lng': 92.7370},
            {'name': 'Aberdeen Bazaar', 'category': 'attraction', 'lat': 11.6690, 'lng': 92.7450},
            {'name': 'Aberdeen ATM', 'category': 'atm', 'lat': 11.6670, 'lng': 92.7420},
        ],
    },
    'cairo': {
        'center': (30.0444, 31.2357),
        'places': [
            {'name': 'Pyramids of Giza', 'category': 'attraction', 'lat': 29.9792, 'lng': 31.1342},
            {'name': 'Egyptian Museum', 'category': 'attraction', 'lat': 30.0478, 'lng': 31.2336},
            {'name': 'Khan el-Khalili', 'category': 'attraction', 'lat': 30.0470, 'lng': 31.2620},
            {'name': 'Cairo Citadel', 'category': 'attraction', 'lat': 30.0290, 'lng': 31.2610},
            {'name': 'Cairo International Airport', 'category': 'airport', 'lat': 30.1219, 'lng': 31.4056},
            {'name': 'Ramses Station', 'category': 'railway', 'lat': 30.0630, 'lng': 31.2470},
            {'name': 'Naguib Mahfouz Café', 'category': 'restaurant', 'lat': 30.0450, 'lng': 31.2590},
            {'name': 'Cairo University Hospital', 'category': 'hospital', 'lat': 30.0260, 'lng': 31.2070},
            {'name': 'City Stars Mall', 'category': 'mall', 'lat': 30.0670, 'lng': 31.3290},
            {'name': 'Tahrir Square', 'category': 'attraction', 'lat': 30.0444, 'lng': 31.2357},
            {'name': 'Cairo Bus Terminal', 'category': 'bus_stop', 'lat': 30.0550, 'lng': 31.2430},
            {'name': 'Tahrir ATM', 'category': 'atm', 'lat': 30.0440, 'lng': 31.2360},
        ],
    },
    'kumarakom': {
        'center': (9.5979, 76.4273),
        'places': [
            {'name': 'Kumarakom Bird Sanctuary', 'category': 'attraction', 'lat': 9.6100, 'lng': 76.4350},
            {'name': 'Vembanad Lake', 'category': 'attraction', 'lat': 9.6100, 'lng': 76.4000},
            {'name': 'Kumarakom Backwaters', 'category': 'attraction', 'lat': 9.6000, 'lng': 76.4200},
            {'name': 'Cochin International Airport', 'category': 'airport', 'lat': 10.1520, 'lng': 76.4019},
            {'name': 'Kottayam Railway Station', 'category': 'railway', 'lat': 9.5840, 'lng': 76.5280},
            {'name': 'Tharavadu Restaurant', 'category': 'restaurant', 'lat': 9.5980, 'lng': 76.4280},
            {'name': 'Kottayam Medical College', 'category': 'hospital', 'lat': 9.6060, 'lng': 76.5270},
            {'name': 'Kumarakom Bus Stop', 'category': 'bus_stop', 'lat': 9.5980, 'lng': 76.4260},
            {'name': 'Kumarakom Jetty ATM', 'category': 'atm', 'lat': 9.5990, 'lng': 76.4290},
        ],
    },
    'manali': {
        'center': (32.2396, 77.1887),
        'places': [
            {'name': 'Hadimba Temple', 'category': 'attraction', 'lat': 32.2530, 'lng': 77.1810},
            {'name': 'Solang Valley', 'category': 'attraction', 'lat': 32.3120, 'lng': 77.1450},
            {'name': 'Mall Road', 'category': 'attraction', 'lat': 32.2430, 'lng': 77.1900},
            {'name': 'Kullu-Manali Airport', 'category': 'airport', 'lat': 31.8770, 'lng': 77.1510},
            {'name': 'Johnson\'s Café', 'category': 'restaurant', 'lat': 32.2400, 'lng': 77.1890},
            {'name': 'Kullu Valley Hospital', 'category': 'hospital', 'lat': 32.2440, 'lng': 77.1860},
            {'name': 'Manali Bus Stand', 'category': 'bus_stop', 'lat': 32.2420, 'lng': 77.1910},
            {'name': 'Mall Road ATM', 'category': 'atm', 'lat': 32.2430, 'lng': 77.1900},
        ],
    },
    'hanoi': {
        'center': (21.0278, 105.8342),
        'places': [
            {'name': 'Hoan Kiem Lake', 'category': 'attraction', 'lat': 21.0285, 'lng': 105.8520},
            {'name': 'Temple of Literature', 'category': 'attraction', 'lat': 21.0286, 'lng': 105.8350},
            {'name': 'Ho Chi Minh Mausoleum', 'category': 'attraction', 'lat': 21.0360, 'lng': 105.8340},
            {'name': 'Old Quarter', 'category': 'attraction', 'lat': 21.0330, 'lng': 105.8500},
            {'name': 'Noi Bai Airport', 'category': 'airport', 'lat': 21.2212, 'lng': 105.8070},
            {'name': 'Hanoi Railway Station', 'category': 'railway', 'lat': 21.0240, 'lng': 105.8410},
            {'name': 'Phở Gia Truyền', 'category': 'restaurant', 'lat': 21.0330, 'lng': 105.8520},
            {'name': 'Bach Mai Hospital', 'category': 'hospital', 'lat': 21.0000, 'lng': 105.8530},
            {'name': 'Vincom Ba Trieu', 'category': 'mall', 'lat': 21.0110, 'lng': 105.8460},
            {'name': 'Long Bien Bus Stop', 'category': 'bus_stop', 'lat': 21.0450, 'lng': 105.8700},
            {'name': 'Hoan Kiem ATM', 'category': 'atm', 'lat': 21.0290, 'lng': 105.8520},
        ],
    },
    'goa': {
        'center': (15.2993, 74.1240),
        'places': [
            {'name': 'Calangute Beach', 'category': 'attraction', 'lat': 15.5440, 'lng': 73.7560},
            {'name': 'Basilica of Bom Jesus', 'category': 'attraction', 'lat': 15.5010, 'lng': 73.9110},
            {'name': 'Fort Aguada', 'category': 'attraction', 'lat': 15.4920, 'lng': 73.8070},
            {'name': 'Dona Paula', 'category': 'attraction', 'lat': 15.4560, 'lng': 73.8080},
            {'name': 'Goa International Airport', 'category': 'airport', 'lat': 15.3800, 'lng': 73.8310},
            {'name': 'Madgaon Railway Station', 'category': 'railway', 'lat': 15.2760, 'lng': 73.9650},
            {'name': 'Ritz Classic Restaurant', 'category': 'restaurant', 'lat': 15.4900, 'lng': 73.8280},
            {'name': 'Goa Medical College', 'category': 'hospital', 'lat': 15.4860, 'lng': 73.8990},
            {'name': 'Caculo Mall', 'category': 'mall', 'lat': 15.4890, 'lng': 73.8270},
            {'name': 'Panaji Market', 'category': 'attraction', 'lat': 15.4990, 'lng': 73.8280},
            {'name': 'Panaji Bus Stand', 'category': 'bus_stop', 'lat': 15.4950, 'lng': 73.8260},
            {'name': 'Panaji ATM', 'category': 'atm', 'lat': 15.4980, 'lng': 73.8280},
        ],
    },
}

# Alias registry keys that may be referenced differently by modules.
CITY_ALIASES = {
    'san josé': 'san jose',
    'uae': 'dubai',
    'united arab emirates': 'dubai',
    'new york city': 'new york',
    'nyc': 'new york',
    'bali': 'bali',
    'tuscany': 'tuscany',
    'maldives': 'male',
    'thira': 'santorini',
    'portblair': 'port blair',
    'keral': 'kumarakom',
    'ubud': 'ubud',
}


def _normalize_city(city):
    if not city:
        return ''
    key = city.strip().lower()
    key = re.sub(r'\s+', ' ', key)
    return CITY_ALIASES.get(key, key)


@lru_cache(maxsize=256)
def get_city_entry(city):
    """Resolve a free-text city to a registry entry (dict) or None."""
    key = _normalize_city(city)
    if key in CITY_PLACES:
        return CITY_PLACES[key]
    # try progressive match: 'new york, ny' -> 'new york'
    for registered, entry in CITY_PLACES.items():
        if key.startswith(registered) or registered.startswith(key):
            if len(key) > 2:
                return entry
    return None


def city_center(city):
    entry = get_city_entry(city)
    return entry['center'] if entry else None


def _closest_city_entry(lat, lng, max_km=120):
    """Find the registry entry whose centre is nearest the given point."""
    best, best_dist = None, max_km
    for entry in CITY_PLACES.values():
        dist = haversine_km(lat, lng, *entry['center'])
        if dist is not None and dist < best_dist:
            best, best_dist = entry, dist
    return best


# ------------------------------------------------------------ place queries

def get_city_places(city):
    """Return all curated places for a city with distances from city centre."""
    entry = get_city_entry(city)
    if not entry:
        return []
    out = []
    for place in entry['places']:
        row = dict(place)
        row['distance_km'] = haversine_km(*entry['center'], place['lat'], place['lng'])
        out.append(row)
    return out


def get_nearby_places(lat, lng, radius_km=None, category=None, limit=None):
    """Return curated places near a coordinate, filtered by radius/category.

    The nearest city registry entry is used as the source dataset so that any
    hotel (even one with coordinates outside our curated centres) still gets
    sensible, deterministic results nearby.
    """
    lat, lng = to_float(lat), to_float(lng)
    if None in (lat, lng):
        return []
    radius_km = radius_km or DEFAULT_RADIUS_KM
    entry = _closest_city_entry(lat, lng)
    if not entry:
        return []

    places = []
    for place in entry['places']:
        dist = haversine_km(lat, lng, place['lat'], place['lng'])
        if dist is None or dist > radius_km:
            continue
        if category and place['category'] != category:
            continue
        row = {
            'name': place['name'],
            'category': place['category'],
            'lat': place['lat'],
            'lng': place['lng'],
            'distance_km': dist,
        }
        places.append(row)

    places.sort(key=lambda p: (p['distance_km'] or 1e9))
    if limit:
        places = places[:limit]
    return places


def get_nearby_grouped(lat, lng, radius_km=None):
    """Nearby places grouped by category in display order."""
    places = get_nearby_places(lat, lng, radius_km=radius_km)
    grouped = []
    for category in CATEGORY_ORDER:
        items = [p for p in places if p['category'] == category]
        if items:
            meta = category_meta(category)
            grouped.append({
                'category': category,
                'label': meta['label'],
                'icon': meta['icon'],
                'color': meta['color'],
                'places': items[:6],
            })
    return grouped


def get_place_lookup(name, city=None):
    """Resolve a place name (landmark search) to coordinates or None."""
    name = (name or '').strip()
    if not name:
        return None
    if city:
        for place in get_city_places(city):
            if name.lower() in place['name'].lower():
                return (place['lat'], place['lng'], place['name'])
        center = city_center(city)
        if center and name.lower() in city.lower():
            return (center[0], center[1], city)
        return None
    for entry in CITY_PLACES.values():
        for place in entry['places']:
            if name.lower() in place['name'].lower():
                return (place['lat'], place['lng'], place['name'])
    return None


def search_landmarks(query, city=None, limit=8):
    """Landmark autocomplete — name contains matches, optionally city scoped."""
    query = (query or '').strip().lower()
    if not query:
        return []
    results = []
    if city:
        for place in get_city_places(city):
            if query in place['name'].lower():
                results.append({'name': place['name'], 'city': city, 'lat': place['lat'], 'lng': place['lng']})
    else:
        for key, entry in CITY_PLACES.items():
            if query in key:
                results.append({'name': key.title(), 'city': key.title(), 'lat': entry['center'][0], 'lng': entry['center'][1]})
            for place in entry['places']:
                if query in place['name'].lower():
                    results.append({'name': place['name'], 'city': key.title(), 'lat': place['lat'], 'lng': place['lng']})
        # de-duplicate on name+city
    seen, unique = set(), []
    for r in results:
        dedupe_key = (r['name'], r['city'])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(r)
        if len(unique) >= limit:
            break
    return unique


def landmark_index():
    """Compact landmark index used by the map page client-side autocomplete."""
    items = []
    for key, entry in CITY_PLACES.items():
        items.append({'name': key.title(), 'city': key.title(), 'lat': entry['center'][0], 'lng': entry['center'][1], 'category': 'city'})
        for place in entry['places']:
            items.append({
                'name': place['name'], 'city': key.title(),
                'lat': place['lat'], 'lng': place['lng'],
                'category': place['category'],
            })
    return items


# ----------------------------------------------------------- hotel filtering

def filter_hotels(hotels, city=None, landmark=None, radius=None, query=None):
    """Filter a hotel queryset by city / landmark radius / free text.

    - ``city``    : match against city/state/country
    - ``landmark``: only hotels within ``radius`` km of the landmark
    - ``query``   : free text over name/city/state/country/address
    """
    qs = hotels
    if query:
        qs = qs.filter(
            Q(name__icontains=query) | Q(city__icontains=query) |
            Q(state__icontains=query) | Q(country__icontains=query) |
            Q(address__icontains=query)
        )
    if city:
        qs = qs.filter(
            Q(city__icontains=city) | Q(state__icontains=city) | Q(country__icontains=city)
        )
    if landmark:
        coord = get_place_lookup(landmark)
        if coord:
            radius = radius or DEFAULT_RADIUS_KM
            point = (coord[0], coord[1])
            qs = [h for h in qs if _has_coords(h) and (haversine_km(h.latitude, h.longitude, *point) or 1e9) <= radius]
        else:
            qs = qs.none() if hasattr(qs, 'none') else []
    return qs


def _has_coords(hotel):
    return to_float(getattr(hotel, 'latitude', None)) is not None and to_float(getattr(hotel, 'longitude', None)) is not None


def hotels_within_radius(hotels, lat, lng, radius_km):
    """Hotel list objects/queryset filtered by straight-line radius of a point."""
    lat, lng = to_float(lat), to_float(lng)
    if None in (lat, lng):
        return []
    radius_km = float(radius_km or DEFAULT_RADIUS_KM)
    out = []
    for hotel in hotels:
        if not _has_coords(hotel):
            continue
        dist = haversine_km(hotel.latitude, hotel.longitude, lat, lng)
        if dist is not None and dist <= radius_km:
            out.append((dist, hotel))
    out.sort(key=lambda x: x[0])
    return out


# ------------------------------------------------------------- serialization

def build_hotel_marker(hotel):
    """Serialize a Hotel to the marker dict consumed by maps/js/script.js."""
    lat, lng = to_float(hotel.latitude), to_float(hotel.longitude)
    if None in (lat, lng):
        return None
    return {
        'id': hotel.id,
        'type': 'hotel',
        'name': hotel.name,
        'lat': lat,
        'lng': lng,
        'city': hotel.city,
        'state': hotel.state,
        'country': hotel.country,
        'address': hotel.address,
        'rating': float(hotel.average_rating or 0),
        'star_rating': hotel.star_rating,
        'reviews': hotel.total_reviews,
        'price': float(hotel.display_price()),
        'currency': 'INR',
        'url': hotel.get_absolute_url() if hasattr(hotel, 'get_absolute_url') else None,
        'image': hotel.image.url if hotel.image else None,
    }


def build_hotel_list_data(hotels):
    """Full hotel list payload (markers + side-panel fields) for the map page."""
    return [m for m in (build_hotel_marker(h) for h in hotels) if m]


def build_destination_marker(package):
    lat, lng = to_float(package.latitude), to_float(package.longitude)
    if None in (lat, lng):
        return None
    return {
        'id': package.id,
        'type': 'destination',
        'name': package.destination,
        'title': package.title,
        'lat': lat,
        'lng': lng,
        'country': package.country,
        'category': package.category,
        'price': float(package.display_price()),
        'rating': float(package.average_rating or 0),
        'duration': package.duration_display,
        'url': package.get_absolute_url() if hasattr(package, 'get_absolute_url') else None,
        'image': package.cover_image.url if package.cover_image else None,
    }


def build_destination_list_data(packages):
    return [m for m in (build_destination_marker(p) for p in packages) if m]


# ------------------------------------------------------------ distance chips

def package_route(package):
    """Suggested transfer route (nearest airport -> destination) for a package.

    Used as a travel-route placeholder on destination maps since the booking
    engine does not hold real-time navigation data.
    """
    from . import links

    lat, lng = to_float(package.latitude), to_float(package.longitude)
    if None in (lat, lng):
        return None
    entry = _closest_city_entry(lat, lng)
    if not entry:
        return None
    airports = [p for p in entry['places'] if p['category'] == 'airport']
    if not airports:
        return None
    airport = min(airports, key=lambda p: haversine_km(lat, lng, p['lat'], p['lng']))
    distance = haversine_km(lat, lng, airport['lat'], airport['lng'])
    if distance is None:
        return None
    return {
        'from': {'name': airport['name'], 'lat': airport['lat'], 'lng': airport['lng']},
        'to': {'name': package.destination, 'lat': lat, 'lng': lng},
        'distance_km': distance,
        'distance_display': links.format_distance(distance),
        'directions_url': links.google_maps_route_url(
            (airport['lat'], airport['lng']), (lat, lng)
        ),
    }


def hotel_distance_summary(hotel):
    """Distances from the hotel to key references (airport, city centre, etc.)."""
    lat, lng = to_float(hotel.latitude), to_float(hotel.longitude)
    if None in (lat, lng):
        return []
    entry = _closest_city_entry(lat, lng)
    if not entry:
        return []
    summary = []
    # Nearest airport
    airports = [p for p in entry['places'] if p['category'] == 'airport']
    for airport in sorted(airports, key=lambda p: haversine_km(lat, lng, p['lat'], p['lng'])):
        summary.append({
            'label': airport['name'],
            'icon': 'bi-airplane',
            'distance_km': haversine_km(lat, lng, airport['lat'], airport['lng']),
            'lat': airport['lat'], 'lng': airport['lng'],
        })
        break
    # City centre
    summary.append({
        'label': f"{hotel.city or 'City'} Centre",
        'icon': 'bi-geo-alt',
        'distance_km': haversine_km(lat, lng, *entry['center']),
        'lat': entry['center'][0], 'lng': entry['center'][1],
    })
    # Nearest attraction
    attractions = [p for p in entry['places'] if p['category'] == 'attraction']
    for attraction in sorted(attractions, key=lambda p: haversine_km(lat, lng, p['lat'], p['lng'])):
        summary.append({
            'label': attraction['name'],
            'icon': 'bi-camera',
            'distance_km': haversine_km(lat, lng, attraction['lat'], attraction['lng']),
            'lat': attraction['lat'], 'lng': attraction['lng'],
        })
        break
    return summary

# -------------------------------------------------------- detail page payload

def build_hotel_detail_data(hotel, nearby_radius_km=5):
    """Everything the hotel detail page needs for its Location section.

    Returns a dict with:
        marker         serialized hotel marker (+ Google Maps links)
        markers_json   JSON array ready for the map_card data attribute
        nearby_places  enriched nearby place cards
        distance_chips enriched distance references (airport / centre / landmark)
    """
    from . import links

    lat, lng = to_float(hotel.latitude), to_float(hotel.longitude)
    if None in (lat, lng):
        return {'marker': None, 'markers_json': '[]', 'nearby_places': [], 'distance_chips': []}

    marker = build_hotel_marker(hotel)
    if marker:
        marker['maps_url'] = links.google_maps_place_url(lat, lng, marker['name'])
        marker['directions_url'] = links.google_maps_directions_url(lat, lng)

    nearby_places = get_nearby_places(lat, lng, radius_km=nearby_radius_km)
    for place in nearby_places:
        place['distance_display'] = links.format_distance(place['distance_km'])
        place['maps_url'] = links.google_maps_place_url(place['lat'], place['lng'], place['name'])
        place['directions_url'] = links.google_maps_directions_url(place['lat'], place['lng'])
        meta = CATEGORY_META.get(place['category'], {})
        place['category_label'] = meta.get('label', place['category'].title())
        place['icon'] = meta.get('icon', 'bi-geo-alt-fill')
        place['color'] = meta.get('color', '#64748B')

    distance_chips = hotel_distance_summary(hotel)
    for chip in distance_chips:
        chip['distance_display'] = links.format_distance(chip['distance_km'])
        chip['maps_url'] = links.google_maps_place_url(chip['lat'], chip['lng'], chip['label'])
        chip['directions_url'] = links.google_maps_directions_url(chip['lat'], chip['lng'])

    import json
    return {
        'marker': marker,
        'markers_json': json.dumps([marker], ensure_ascii=False) if marker else '[]',
        'nearby_places': nearby_places,
        'distance_chips': distance_chips,
    }
