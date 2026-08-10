from django.urls import path

from . import views

urlpatterns = [
    path('checkout/', views.PaymentCheckoutView.as_view(), name='payment_checkout'),
    path('verify/', views.PaymentVerifyView.as_view(), name='payment_verify'),
    path('success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('failed/', views.PaymentFailedView.as_view(), name='payment_failed'),
    path('history/', views.PaymentHistoryView.as_view(), name='payment_history'),
    path('retry/<int:payment_id>/', views.PaymentRetryView.as_view(), name='payment_retry'),
    path('reconcile/<int:payment_id>/', views.PaymentReconcileView.as_view(), name='payment_reconcile'),
    path('invoice/<int:payment_id>/', views.InvoiceDownloadView.as_view(), name='payment_invoice'),
    path('refund/<int:payment_id>/', views.PaymentAdminRefundView.as_view(), name='payment_refund'),
    path('webhook/<str:gateway>/', views.PaymentWebhookView.as_view(), name='payment_webhook'),
]