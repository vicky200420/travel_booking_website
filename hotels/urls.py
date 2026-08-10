from django.urls import path

from . import views

urlpatterns = [
    path('', views.HotelListView.as_view(), name='hotel_list'),
    path('search/', views.HotelSearchView.as_view(), name='hotel_search'),
    path('<slug:slug>/', views.HotelDetailView.as_view(), name='hotel_detail'),
]
