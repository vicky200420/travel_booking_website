"""WSGI config for travel_booking project."""

import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_booking.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
