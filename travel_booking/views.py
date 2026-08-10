"""Project-level views: health check + custom error handlers."""
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string


def robots_txt(request):
    """Render robots.txt with the absolute SITE_URL for the sitemap."""
    content = render_to_string('robots.txt', {'SITE_URL': settings.SITE_URL})
    return HttpResponse(content, content_type='text/plain')


def offline(request):
    """PWA offline fallback shown by the service worker when the network drops."""
    return render(request, 'errors/offline.html', status=200)


def health(request):
    """Liveness/readiness probe for load balancers and orchestrators.

    Returns 200 with a minimal JSON payload when the app boots and the
    database is reachable, otherwise 503. Exempt from CSRF (GET-only).
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False

    if not db_ok:
        return JsonResponse(
            {'status': 'unhealthy', 'database': 'unreachable'},
            status=503,
        )
    return JsonResponse({
        'status': 'ok',
        'database': 'ok',
        'environment': 'production' if not settings.DEBUG else 'development',
    })


def error_400(request, exception=None):
    return render(request, 'errors/400.html', status=400)


def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)
