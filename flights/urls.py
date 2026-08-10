from django.urls import path

from . import views

urlpatterns = [
    path('', views.FlightListView.as_view(), name='flights'),
    path('search/', views.FlightSearchView.as_view(), name='flight_search'),
    path('<int:id>/', views.FlightDetailView.as_view(), name='flight_detail'),
]
