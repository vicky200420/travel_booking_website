import json
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models.fields.files import FieldFile

from hotels.models import Hotel
from packages.models import TravelPackage


def serialize_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, FieldFile):
        return str(value.name) if value.name else None
    return value


def serialize_row(obj):
    row = {}
    for field in obj._meta.local_fields:
        if field.primary_key or not field.editable:
            continue
        value = getattr(obj, field.attname)
        row[field.name] = serialize_value(value)
    return row


class Command(BaseCommand):
    help = (
        'Export all Hotel and TravelPackage records to a JSON file so they can be '
        're-created safely on another instance (e.g. production).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='data/travel_data.json',
            help='Path to the JSON file to write (default: data/travel_data.json).',
        )

    def handle(self, *args, **options):
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            'model': 'travel_data',
            'version': 1,
            'exported_at': datetime.now().isoformat(),
            'hotels': [serialize_row(h) for h in Hotel.objects.all()],
            'packages': [serialize_row(p) for p in TravelPackage.objects.all()],
        }

        with output.open('w', encoding='utf-8') as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(
                'Exported {} hotels and {} packages to {}'.format(
                    len(payload['hotels']),
                    len(payload['packages']),
                    output,
                )
            )
        )