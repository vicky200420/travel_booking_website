from django.urls import path

from . import views

urlpatterns = [
    path('', views.BookingHistoryView.as_view(), name='booking_history'),
    path('create/', views.BookingCreateView.as_view(), name='booking_create'),
    path('create/review/', views.BookingReviewView.as_view(), name='booking_review'),
    path('<slug:booking_id>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('<slug:booking_id>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
    path('<slug:booking_id>/download/', views.BookingDownloadView.as_view(), name='booking_download'),
]
