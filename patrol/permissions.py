from rest_framework.permissions import BasePermission


class IsProductionHeadOrAdmin(BasePermission):
    """
    Permission for Production Head to create/manage patrol duties
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


class IsPatrolUser(BasePermission):
    """
    Permission for Patrol users to access their own duties and uploads
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        return active_role.role.name == 'patrol'
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check"""
        # Patrol users can only access their own duties/uploads
        if hasattr(obj, 'patrol_user'):
            return obj.patrol_user == request.user
        elif hasattr(obj, 'duty'):
            return obj.duty.patrol_user == request.user
        return False


class IsPatrolUserOrManagerAbove(BasePermission):
    """
    Combined permission: Patrol can access own data, Manager+ can access all
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        return active_role.role.name in ['admin', 'manager', 'production_head', 'patrol']
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check"""
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        
        # Admin, Manager, Production Head can access all
        if active_role.role.name in ['admin', 'manager', 'production_head']:
            return True
        
        # Patrol users can only access their own
        if active_role.role.name == 'patrol':
            if hasattr(obj, 'patrol_user'):
                return obj.patrol_user == request.user
            elif hasattr(obj, 'duty'):
                return obj.duty.patrol_user == request.user
        
        return False

