from django.test import TestCase

from hotels.models import Hotel
from packages.models import TravelPackage

from . import services, utils


class HaversineTests(TestCase):
    def test_known_distance(self):
        # Paris -> London is ~344 km great-circle.
        distance = services.haversine_km(48.8566, 2.3522, 51.5074, -0.1278)
        self.assertIsNotNone(distance)
        self.assertAlmostEqual(distance, 344, delta=6)

    def test_zero_distance(self):
        self.assertEqual(services.haversine_km(10, 10, 10, 10), 0)

    def test_invalid_input(self):
        self.assertIsNone(services.haversine_km(None, 10, 10, 10))


class PlaceQueryTests(TestCase):
    def test_city_center(self):
        center = services.city_center('Paris')
        self.assertIsNotNone(center)
        self.assertAlmostEqual(center[0], 48.8683, delta=0.1)

    def test_nearby_places_returns_curated_data(self):
        places = services.get_nearby_places(48.8683, 2.3290, radius_km=5)
        self.assertTrue(places)
        self.assertIn('Eiffel Tower', [p['name'] for p in places])

    def test_nearby_places_respects_category_and_radius(self):
        places = services.get_nearby_places(40.7484, -73.9857, radius_km=2, category='airport')
        self.assertEqual(places, [])

    def test_landmark_lookup(self):
        coord = services.get_place_lookup('Eiffel Tower')
        self.assertIsNotNone(coord)
        self.assertAlmostEqual(coord[0], 48.8584, delta=0.01)

    def test_landmark_search(self):
        results = services.search_landmarks('Tower')
        self.assertTrue(any('Tokyo Tower' == r['name'] for r in results))


class DistanceSummaryTests(TestCase):
    def test_hotel_distance_summary(self):
        hotel = Hotel(
            name='Test', city='Paris', country='France', address='x',
            price_per_night=100, total_rooms=10, available_rooms=5,
            latitude=48.8683, longitude=2.3290,
        )
        summary = services.hotel_distance_summary(hotel)
        self.assertTrue(summary)
        self.assertEqual(summary[0]['icon'], 'bi-airplane')


class UtilsTests(TestCase):
    def test_format_distance(self):
        self.assertEqual(utils.format_distance(0.05), '50 m')
        self.assertEqual(utils.format_distance(3.456), '3.5 km')

    def test_google_maps_urls(self):
        url = utils.google_maps_directions_url(48.8584, 2.2945)
        self.assertIn('google.com/maps/dir/', url)
        self.assertIn('48.858400,2.294500', url)
        self.assertIsNone(utils.google_maps_directions_url(None, None))

    def test_place_with_urls(self):
        place = utils.place_with_urls({'name': 'X', 'lat': 1.0, 'lng': 2.0, 'distance_km': 1.2})
        self.assertIn('distance_display', place)
        self.assertIn('maps_url', place)
        self.assertIn('directions_url', place)


class MarkerBuildTests(TestCase):
    def test_build_destination_marker(self):
        package = TravelPackage(
            title='Test Trip', destination='Paris', country='France',
            duration_days=3, price=100,
            latitude=48.8683, longitude=2.3290,
        )
        marker = services.build_destination_marker(package)
        self.assertIsNotNone(marker)
        self.assertEqual(marker['type'], 'destination')
