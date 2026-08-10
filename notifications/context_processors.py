"""Notification & Communication — template context processors.

Injects the unread count and recent notifications for the navbar bell into
every request rendered through the site's templates. Backed by a short-lived
per-user cache so page renders don't pay two DB queries each time.
"""


def notification_context(request):
    context = {
        'unread_notifications': 0,
        'recent_notifications': [],
    }
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return context

    from .services import NotificationService
    summary = NotificationService.summary(request.user)
    context['unread_notifications'] = summary['unread']
    context['recent_notifications'] = summary['recent']
    return context
