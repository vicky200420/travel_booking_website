import json
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models

from hotels.models import Hotel
from packages.models import TravelPackage


def convert_value(model, field_name, value):
    if value is None:
        return None
    field = model._meta.get_field(field_name)
    if isinstance(field, models.DecimalField):
        return Decimal(str(value))
    if isinstance(field, models.DateTimeField):
        return datetime.fromisoformat(value)
    if isinstance(field, models.DateField):
        return date.fromisoformat(value)
    if isinstance(field, models.TimeField):
        return time.fromisoformat(value)
    if isinstance(field, models.BooleanField):
        return bool(value)
    if isinstance(field, (models.ImageField, models.FileField)):
        media_path = Path(settings.MEDIA_ROOT) / value
        if media_path.is_file():
            return value
        return None
    return value


def import_records(model, items):
    created = 0
    existing = 0
    skipped = 0
    for item in items:
        slug = item.get('slug')
        if not slug:
            skipped += 1
            continue
        defaults = {
            name: convert_value(model, name, value)
            for name, value in item.items()
            if name != 'slug'
        }
        _, was_created = model.objects.get_or_create(slug=slug, defaults=defaults)
        if was_created:
            created += 1
        else:
            existing += 1
    return created, existing, skipped


class Command(BaseCommand):
    help = (
        'Import Hotel and TravelPackage records from a JSON file produced by '
        'export_travel_data. Uses slug-based get_or_create so it never creates '
        'duplicates and never overwrites existing rows.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/travel_data.json',
            help='Path to the JSON file to read (default: data/travel_data.json).',
        )

    def handle(self, *args, **options):
        source = Path(options['file'])
        if not source.is_file():
            self.stderr.write(self.style.ERROR(f'Data file not found: {source}'))
            raise SystemExit(1)

        with source.open('r', encoding='utf-8') as file:
            payload = json.load(file)

        hotels_created, hotels_existing, hotels_skipped = import_records(Hotel, payload.get('hotels', []))
        packages_created, packages_existing, packages_skipped = import_records(
            TravelPackage, payload.get('packages', [])
        )

        self.stdout.write(self.style.SUCCESS(f'Hotels created: {hotels_created}'))
        self.stdout.write(self.style.SUCCESS(f'Hotels already existed: {hotels_existing}'))
        self.stdout.write(self.style.SUCCESS(f'Packages created: {packages_created}'))
        self.stdout.write(self.style.SUCCESS(f'Packages already existed: {packages_existing}'))

        if hotels_skipped or packages_skipped:
            self.stdout.write(
                self.style.WARNING(
                    f'Skipped {hotels_skipped} hotels and {packages_skipped} packages (missing slug).'
                )
            )