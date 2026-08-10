from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from . import views
from .sitemaps import sitemaps

urlpatterns = [
    path('', include('home.urls')),
    path('', include('accounts.urls')),
    path('', include('dashboard.urls')),
    path('flights/', include('flights.urls')),
    path('hotels/', include('hotels.urls')),
    path('packages/', include('packages.urls')),
    path('bookings/', include('bookings.urls')),
    path('payments/', include('payments.urls')),
    path('reviews/', include('reviews.urls')),
    path('maps/', include('maps.urls')),
    path('notifications/', include('notifications.urls')),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

    # Operational / infrastructure
    path('health/', views.health, name='health'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('offline/', views.offline, name='offline'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # API documentation (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='swagger_ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='api_schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'travel_booking.views.error_400'
handler403 = 'travel_booking.views.error_403'
handler404 = 'travel_booking.views.error_404'
handler500 = 'travel_booking.views.error_500'
