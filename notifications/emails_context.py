"""Notification & Communication — shared email rendering context."""
from django.conf import settings


def build_email_context(**overrides):
    """Base context shared by every email template (branding, footer, social)."""
    context = {
        'site_name': getattr(settings, 'SITE_NAME', 'TravelBooking'),
        'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/'),
        'logo_text': 'TravelBooking',
        'tagline': 'Plan. Book. Explore.',
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@travelbooking.local'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+1 (800) 555-0199'),
        'address': '700 Marina Bay Street, San Francisco, CA 94111',
        'social': {
            'facebook': '#',
            'instagram': '#',
            'twitter': '#',
            'youtube': '#',
        },
        'year': None,
        'preheader': '',
        'hero_icon': 'bi-envelope-paper-heart',
        'primary_action': None,      # {'label': str, 'url': str}
        'secondary_action': None,
        'summary_title': '',
        'summary_items': [],          # list of {'label', 'value'}
        'details_blocks': [],         # list of {'title', 'icon', 'rows': [{'label','value'}]}
        'amount': None,
        'currency': None,
        'message': '',
        'user_first_name': '',
        'user_email': '',
        'disclaimer': (
            'You are receiving this email because you have an account or active '
            'booking with {site}. If you believe this was sent in error, you can '
            'unsubscribe at any time from your notification preferences.'
        ),
    }
    import datetime
    context['year'] = datetime.date.today().year
    context.update(overrides)
    context['disclaimer'] = context['disclaimer'].format(site=context['site_name'])
    return context
