from rest_framework.permissions import BasePermission


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
        return hasattr(request.user, 'role') and request.user.role == 'manager'


class IsManager(BasePermission):
    """
    Custom permission to only allow managers to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager
        return hasattr(request.user, 'role') and request.user.role == 'manager'


class IsManagerOrSupervisor(BasePermission):
    """
    Custom permission to allow managers and supervisors to access the view.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is a manager or supervisor
        if hasattr(request.user, 'role'):
            return request.user.role in ['manager', 'supervisor']
        
        return False
