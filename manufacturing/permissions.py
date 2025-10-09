from rest_framework.permissions import BasePermission
from django.core.cache import cache


class IsManagerOrReadOnly(BasePermission):
    """
    Custom permission to only allow managers and production heads to create/edit manufacturing orders and purchase orders.
    Other authenticated users can only view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read permissions for any authenticated user
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions for managers and production heads
        user_role = self._get_user_role(request.user)
        return user_role in ['admin', 'manager', 'production_head']
    
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
    Custom permission to only allow managers and production heads to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager or production head
        user_role = self._get_user_role(request.user)
        return user_role in ['admin', 'manager', 'production_head']
    
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
    Custom permission to allow managers, production heads, and supervisors to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager, production head, or supervisor
        user_role = self._get_user_role(request.user)
        return user_role in ['admin', 'manager', 'production_head', 'supervisor']
    
    def _get_user_role(self, user):
        """Get user role with caching"""
        cache_key = f'user_role_{user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)  # Cache for 5 minutes
        
        return user_role


class IsManagerOrRMStore(BasePermission):
    """
    Custom permission to allow managers and production heads to create/edit purchase orders and RM Store users to view/update status.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user role
        user_role = self._get_user_role(request.user)
        
        # Managers and Production Heads can do everything
        if user_role in ['admin', 'manager', 'production_head']:
            return True
        
        # RM Store users can view and update status
        if user_role == 'rm_store':
            # Allow read operations
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return True
            # Allow status changes
            if request.method == 'POST' and 'change_status' in request.path:
                return True
        
        return False
    
    def _get_user_role(self, user):
        """Get user role with caching"""
        cache_key = f'user_role_{user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)  # Cache for 5 minutes
        
        return user_role
