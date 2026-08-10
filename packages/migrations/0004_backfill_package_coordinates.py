from django.db import migrations

DESTINATION_COORDS = {
    'nairobi': (-1.3701, 36.7503),
    'male': (4.1755, 73.5093),
    'reykjavik': (64.1466, -21.9426),
    'tokyo': (35.6580, 139.7016),
    'interlaken': (46.6863, 7.8632),
    'athens': (37.9838, 23.7275),
    'jaipur': (26.9852, 75.8516),
    'leh': (34.1526, 77.5771),
    'santorini': (36.3932, 25.4615),
    'ubud': (-8.5069, 115.2625),
    'dubai': (24.7136, 55.1673),
    'edinburgh': (55.9533, -3.1883),
    'port blair': (11.6234, 92.7265),
    'cairo': (30.0444, 31.2357),
    'kumarakom': (9.5979, 76.4273),
    'bangkok': (13.7367, 100.5604),
    'manali': (32.2396, 77.1887),
    'hanoi': (21.0278, 105.8342),
    'goa': (15.2993, 74.1240),
    'sanjosé': (9.9281, -84.0907),
    'san josé': (9.9281, -84.0907),
}

# The seeded "San José" row may have been stored with mojibake; match by prefix.
PREFIX_MATCH = {
    'san jos': (9.9281, -84.0907),
}


def _lookup(destination):
    if not destination:
        return None
    key = destination.strip().lower().replace('  ', ' ')
    if key in DESTINATION_COORDS:
        return DESTINATION_COORDS[key]
    for prefix, coord in PREFIX_MATCH.items():
        if key.startswith(prefix):
            return coord
    return None


def backfill_coordinates(apps, schema_editor):
    TravelPackage = apps.get_model('packages', 'TravelPackage')
    updated = 0
    for package in TravelPackage.objects.all():
        coord = _lookup(package.destination)
        if coord and (package.latitude is None or package.longitude is None):
            package.latitude, package.longitude = coord
            package.save(update_fields=['latitude', 'longitude'])
            updated += 1
    if updated:
        print(f'Backfilled coordinates for {updated} package(s).')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0003_travelpackage_latitude_travelpackage_longitude'),
    ]

    operations = [
        migrations.RunPython(backfill_coordinates, noop),
    ]
