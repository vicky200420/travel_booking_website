from django.urls import path

from . import views

urlpatterns = [
    path('', views.MyReviewsView.as_view(), name='my_reviews'),
    path('create/', views.ReviewCreateView.as_view(), name='review_create'),
    path('<int:pk>/edit/', views.ReviewUpdateView.as_view(), name='review_edit'),
    path('<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    path('hotel/<int:hotel_id>/', views.HotelReviewsView.as_view(), name='hotel_reviews'),
    path('package/<int:package_id>/', views.PackageReviewsView.as_view(), name='package_reviews'),
    path('<int:pk>/helpful/', views.HelpfulToggleView.as_view(), name='review_helpful'),
]
