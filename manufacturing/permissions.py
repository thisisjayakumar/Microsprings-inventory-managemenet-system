from rest_framework.permissions import BasePermission
from django.core.cache import cache


class IsManagerOrReadOnly(BasePermission):
    """
    Custom permission to only allow managers to create/edit manufacturing orders and purchase orders.
    Other authenticated users can only view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read permissions for any authenticated user
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for managers
        return self._get_user_role(request.user) == 'manager'
    
    def _get_user_role(self, user):
        """Get user role with caching"""
        cache_key = f'user_role_{user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 3000)  # Cache for 50 minutes
        
        return user_role


class IsManager(BasePermission):
    """
    Custom permission to only allow managers to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager
        return self._get_user_role(request.user) == 'manager'
    
    def _get_user_role(self, user):
        """Get user role with caching"""
        cache_key = f'user_role_{user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)  # Cache for 5 minutes
        
        return user_role


class IsManagerOrSupervisor(BasePermission):
    """
    Custom permission to allow managers and supervisors to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager or supervisor
        user_role = self._get_user_role(request.user)
        return user_role in ['manager', 'supervisor']
    
    def _get_user_role(self, user):
        """Get user role with caching"""
        cache_key = f'user_role_{user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)  # Cache for 5 minutes
        
        return user_role
