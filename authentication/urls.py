from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'roles', views.RoleViewSet, basename='role')
router.register(r'process-supervisors', views.ProcessSupervisorViewSet, basename='process-supervisor')
router.register(r'operator-engagements', views.OperatorEngagementViewSet, basename='operator-engagement')
router.register(r'login-sessions', views.LoginSessionViewSet, basename='login-session')

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('profile/', views.user_profile, name='user_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('permissions/', views.user_permissions, name='user_permissions'),
    
    # Bulk operations
    path('bulk/role-assignment/', views.bulk_role_assignment, name='bulk_role_assignment'),
    
    # Dashboard and stats
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    
    # Network restrictions
    path('ip-restrictions/update/', views.update_ip_restrictions, name='update_ip_restrictions'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Include router URLs
    path('', include(router.urls)),
]

# Additional URL patterns for specific endpoints
urlpatterns += [
    # User management specific endpoints
    path('users/available-operators/', views.UserViewSet.as_view({'get': 'available_operators'}), name='available_operators'),
    path('users/supervisors-by-department/', views.UserViewSet.as_view({'get': 'supervisors_by_department'}), name='supervisors_by_department'),
    path('users/<int:pk>/assign-role/', views.UserViewSet.as_view({'post': 'assign_role'}), name='assign_role'),
    path('users/<int:pk>/engage-operator/', views.UserViewSet.as_view({'post': 'engage_operator'}), name='engage_operator'),
    path('users/<int:pk>/release-operator/', views.UserViewSet.as_view({'post': 'release_operator'}), name='release_operator'),
    
    # Role management
    path('roles/hierarchy/', views.RoleViewSet.as_view({'get': 'hierarchy'}), name='role_hierarchy'),
]