from rest_framework.permissions import BasePermission
from django.core.cache import cache


class IsAdminOrManager(BasePermission):
    """
    Permission for Admin or Manager roles only
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check cache first
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)  # Cache for 5 minutes
        
        return user_role in ['admin', 'manager']


class IsManagerOrAbove(BasePermission):
    """
    Permission for Manager and above (Admin, Manager, Production Head)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)
        
        return user_role in ['admin', 'manager', 'production_head']


class IsSupervisorOrAbove(BasePermission):
    """
    Permission for Supervisor and above (Admin, Manager, Production Head, Supervisor)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)
        
        return user_role in ['admin', 'manager', 'production_head', 'supervisor']


class IsRMStoreOrAbove(BasePermission):
    """
    Permission for RM Store and above
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)
        
        return user_role in ['admin', 'manager', 'production_head', 'supervisor', 'rm_store']


class IsFGStoreOrAbove(BasePermission):
    """
    Permission for FG Store and above
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)
        
        return user_role in ['admin', 'manager', 'production_head', 'supervisor', 'fg_store']


class DepartmentAccessPermission(BasePermission):
    """
    Permission based on department access
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get requested department from query params or view kwargs
        requested_dept = (
            request.query_params.get('department') or 
            view.kwargs.get('department') or
            getattr(view, 'required_department', None)
        )
        
        if not requested_dept:
            return True  # No department restriction
        
        # Check user's role and department access
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if not active_role:
            return False
        
        # Admin, Manager, and Production Head have access to all departments
        if active_role.role.name in ['admin', 'manager', 'production_head']:
            return True
        
        # Check if role can access the requested department
        return active_role.role.can_access_department(requested_dept)


class ProcessSupervisorPermission(BasePermission):
    """
    Permission for process supervisors to access their assigned processes
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin, Manager, and Production Head have full access
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if active_role and active_role.role.name in ['admin', 'manager', 'production_head']:
            return True
        
        # Check if user is a supervisor with process assignments
        return request.user.process_supervisor_assignments.filter(is_active=True).exists()


class NetworkRestrictionPermission(BasePermission):
    """
    Permission based on network/IP restrictions
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Skip for superusers
        if request.user.is_superuser:
            return True
        
        # Check IP restrictions
        if hasattr(request.user, 'profile') and request.user.profile.allowed_ip_ranges:
            client_ip = self.get_client_ip(request)
            return self.is_ip_allowed(client_ip, request.user.profile.allowed_ip_ranges)
        
        return True  # No restrictions
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_allowed(self, client_ip, allowed_ranges):
        """Check if client IP is in allowed ranges"""
        import ipaddress
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            for ip_range in allowed_ranges:
                if client_ip_obj in ipaddress.ip_network(ip_range, strict=False):
                    return True
            return False
        except:
            return False


class OperatorEngagementPermission(BasePermission):
    """
    Permission to check operator engagement status
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin, Manager, and Production Head can always manage engagements
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if active_role and active_role.role.name in ['admin', 'manager', 'production_head']:
            return True
        
        # Supervisors can manage in their department
        if active_role and active_role.role.name == 'supervisor':
            return request.user.process_supervisor_assignments.filter(is_active=True).exists()
        
        return False


class ShiftBasedPermission(BasePermission):
    """
    Permission based on shift timings
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin, Manager, and Production Head have access anytime
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        if active_role and active_role.role.name in ['admin', 'manager', 'production_head']:
            return True
        
        # Check if user is in their assigned shift
        if hasattr(request.user, 'profile') and request.user.profile.shift:
            return self.is_in_shift(request.user.profile.shift)
        
        return True  # No shift restrictions
    
    def is_in_shift(self, shift):
        """Check if current time is within shift hours"""
        from datetime import datetime, time
        
        now = datetime.now().time()
        
        shift_times = {
            'I': (time(9, 0), time(17, 0)),    # 9AM-5PM
            'II': (time(17, 0), time(2, 0)),   # 5PM-2AM (next day)
            'III': (time(2, 0), time(9, 0))    # 2AM-9AM
        }
        
        if shift not in shift_times:
            return True
        
        start_time, end_time = shift_times[shift]
        
        # Handle overnight shifts
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time


# Combined permissions for common use cases
class MSPERPBasePermission(BasePermission):
    """
    Base permission combining network and shift restrictions
    """
    def has_permission(self, request, view):
        # Check authentication
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check network restrictions
        network_perm = NetworkRestrictionPermission()
        if not network_perm.has_permission(request, view):
            return False
        
        # Check shift restrictions for non-admin users
        shift_perm = ShiftBasedPermission()
        if not shift_perm.has_permission(request, view):
            return False
        
        return True


class AdminOnlyPermission(MSPERPBasePermission):
    """
    Admin only with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'admin'


class ManagerOnlyPermission(MSPERPBasePermission):
    """
    Manager only with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'manager'


class SupervisorOnlyPermission(MSPERPBasePermission):
    """
    Supervisor only with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'supervisor'


class ProductionHeadPermission(MSPERPBasePermission):
    """
    Production Head permission with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'production_head'


class RMStorePermission(MSPERPBasePermission):
    """
    RM Store permission with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'rm_store'


class FGStorePermission(MSPERPBasePermission):
    """
    FG Store permission with base restrictions
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
        return active_role and active_role.role.name == 'fg_store'
