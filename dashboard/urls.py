from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/bookings/', views.DashboardBookingsView.as_view(), name='dashboard_bookings'),
    path('dashboard/payments/', views.DashboardPaymentsView.as_view(), name='dashboard_payments'),
    path('dashboard/payments/invoice/<int:payment_id>/', views.DashboardInvoiceView.as_view(), name='dashboard_invoice'),
    path('dashboard/wishlist/', views.DashboardWishlistView.as_view(), name='dashboard_wishlist'),
    path('dashboard/wishlist/toggle/', views.WishlistToggleView.as_view(), name='dashboard_wishlist_toggle'),
    path('dashboard/wishlist/<int:item_id>/remove/', views.WishlistRemoveView.as_view(), name='dashboard_wishlist_remove'),
    path('dashboard/reviews/', views.DashboardReviewsView.as_view(), name='dashboard_reviews'),
    path('dashboard/notifications/', views.DashboardNotificationsView.as_view(), name='dashboard_notifications'),
    path('dashboard/settings/', views.DashboardSettingsView.as_view(), name='dashboard_settings'),

    # Admin analytics (staff / superuser only)
    path('admin-analytics/', views.AdminDashboardView.as_view(), name='admin_analytics'),
    path('admin-analytics/search/', views.AdminAnalyticsSearchView.as_view(), name='admin_analytics_search'),
    path(
        'admin-analytics/export/<str:report>/<str:fmt>/',
        views.AdminReportExportView.as_view(),
        name='admin_report_export',
    ),
]
