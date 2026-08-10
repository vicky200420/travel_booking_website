from django.urls import path

from . import views

app_name = 'maps'

urlpatterns = [
    path('hotels/', views.HotelMapView.as_view(), name='hotel_map'),
    path('hotels/<slug:slug>/nearby/', views.HotelNearbyJsonView.as_view(), name='hotel_nearby'),
    path('packages/', views.DestinationMapView.as_view(), name='destination_map'),
    path('packages/<slug:slug>/', views.DestinationMapView.as_view(), name='destination_map_detail'),
    path('api/nearby/', views.NearbyPlacesApiView.as_view(), name='nearby_api'),
    path('api/landmarks/', views.LandmarkSearchApiView.as_view(), name='landmark_api'),
]
