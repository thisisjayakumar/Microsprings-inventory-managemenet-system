"""
URL patterns for third_party app
"""

from django.urls import path
from . import views

app_name = 'third_party'

urlpatterns = [
    # Brand URLs
    path('brands/', views.BrandListCreateView.as_view(), name='brand-list-create'),
    path('brands/<int:pk>/', views.BrandDetailView.as_view(), name='brand-detail'),
    
    # Vendor URLs
    path('vendors/', views.VendorListCreateView.as_view(), name='vendor-list-create'),
    path('vendors/<int:pk>/', views.VendorDetailView.as_view(), name='vendor-detail'),
    
    # Customer URLs
    path('customers/', views.CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    
    # Additional Customer endpoints
    path('customers/search/', views.customer_search, name='customer-search'),
    path('customers/<int:pk>/contacts/', views.customer_contacts, name='customer-contacts'),
    path('customers/bulk-update/', views.bulk_customer_update, name='customer-bulk-update'),
    
    # Utility endpoints
    path('industry-types/', views.industry_types, name='industry-types'),
]
