"""Site-wide template context: exposes key settings to every template."""
from django.conf import settings


def site_settings(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_URL': settings.SITE_URL,
        'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
        'SUPPORT_PHONE': settings.SUPPORT_PHONE,
        'DEFAULT_CURRENCY': settings.DEFAULT_CURRENCY,
    }
