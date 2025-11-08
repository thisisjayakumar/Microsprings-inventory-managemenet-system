from rest_framework.permissions import BasePermission


class IsPackingZoneUser(BasePermission):
    """
    Permission for Packing Zone users to access their functionality
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        return active_role.role.name == 'packing_zone'


class IsProductionHeadOrAdmin(BasePermission):
    """
    Permission for Production Head to approve merge requests and adjustments
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        return active_role.role.name in ['admin', 'production_head']


class IsManagerOrAbove(BasePermission):
    """
    Permission for Manager (read-only) and Production Head (full access)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        # Manager has read-only access
        if active_role.role.name == 'manager':
            return request.method in ['GET', 'HEAD', 'OPTIONS']
        
        # Production Head and Admin have full access
        return active_role.role.name in ['admin', 'production_head']


class IsPackingZoneUserOrManagerAbove(BasePermission):
    """
    Combined permission: Packing Zone user for operations, Manager+ for viewing
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        role_name = active_role.role.name
        
        # Packing Zone user has full access
        if role_name == 'packing_zone':
            return True
        
        # Manager has read-only access
        if role_name == 'manager':
            return request.method in ['GET', 'HEAD', 'OPTIONS']
        
        # Production Head and Admin have full access
        return role_name in ['admin', 'production_head']

