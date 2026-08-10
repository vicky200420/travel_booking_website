from django.urls import path

from . import views

urlpatterns = [
    path('', views.PackageListView.as_view(), name='package_list'),
    path('search/', views.PackageSearchView.as_view(), name='package_search'),
    path('<slug:slug>/', views.PackageDetailView.as_view(), name='package_detail'),
]
