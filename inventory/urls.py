from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Placeholder for inventory endpoints
    path('health/', views.health_check, name='health_check'),
]
