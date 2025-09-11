from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/me/', views.user_profile, name='user_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
]
