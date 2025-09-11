import ipaddress
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, time
from .models import LoginSession


class NetworkRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware to enforce network/IP restrictions for MSP-ERP
    """
    
    def process_request(self, request):
        # Skip for unauthenticated users and certain endpoints
        if not request.user.is_authenticated:
            return None
        
        # Skip for superusers
        if request.user.is_superuser:
            return None
        
        # Skip for health check and auth endpoints
        skip_paths = ['/api/auth/health/', '/api/auth/logout/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Check IP restrictions
        if hasattr(request.user, 'profile') and request.user.profile.allowed_ip_ranges:
            client_ip = self.get_client_ip(request)
            
            if not self.is_ip_allowed(client_ip, request.user.profile.allowed_ip_ranges):
                return JsonResponse({
                    'error': 'Access denied from this network location',
                    'code': 'NETWORK_RESTRICTED'
                }, status=403)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_allowed(self, client_ip, allowed_ranges):
        """Check if client IP is in allowed ranges"""
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            for ip_range in allowed_ranges:
                if client_ip_obj in ipaddress.ip_network(ip_range, strict=False):
                    return True
            return False
        except:
            return False


class ShiftRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware to enforce shift-based access restrictions
    """
    
    def process_request(self, request):
        # Skip for unauthenticated users
        if not request.user.is_authenticated:
            return None
        
        # Skip for admin and manager roles
        cache_key = f'user_role_{request.user.id}'
        user_role = cache.get(cache_key)
        
        if not user_role:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            user_role = active_role.role.name if active_role else None
            cache.set(cache_key, user_role, 300)
        
        if user_role in ['admin', 'manager']:
            return None
        
        # Check shift restrictions for other roles
        if hasattr(request.user, 'profile') and request.user.profile.shift:
            if not self.is_in_shift(request.user.profile.shift):
                return JsonResponse({
                    'error': 'Access denied outside assigned shift hours',
                    'code': 'SHIFT_RESTRICTED',
                    'assigned_shift': request.user.profile.get_shift_display()
                }, status=403)
        
        return None
    
    def is_in_shift(self, shift):
        """Check if current time is within shift hours"""
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


class SessionTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track user sessions and prevent concurrent logins
    """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Skip for certain endpoints
        skip_paths = ['/api/auth/logout/', '/api/auth/health/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Check for active session
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Update last activity for current session
        LoginSession.objects.filter(
            user=request.user,
            ip_address=client_ip,
            is_active=True
        ).update(
            login_time=timezone.now()  # Update to track last activity
        )
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Middleware for role-based access control
    """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Add user role information to request for easy access
        cache_key = f'user_permissions_{request.user.id}'
        permissions = cache.get(cache_key)
        
        if not permissions:
            active_role = request.user.user_roles.filter(is_active=True).select_related('role').first()
            if active_role:
                permissions = {
                    'role_name': active_role.role.name,
                    'hierarchy_level': active_role.role.hierarchy_level,
                    'permissions': active_role.role.permissions,
                    'restricted_departments': active_role.role.restricted_departments,
                    'can_supervise': request.user.process_supervisor_assignments.filter(is_active=True).exists()
                }
                cache.set(cache_key, permissions, 300)
            else:
                permissions = {}
        
        # Attach permissions to request
        request.user_permissions = permissions
        
        return None


class DepartmentAccessMiddleware(MiddlewareMixin):
    """
    Middleware to check department-specific access
    """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Check if request is for department-specific data
        department = (
            request.GET.get('department') or
            request.POST.get('department') or
            getattr(request, 'department_required', None)
        )
        
        if not department:
            return None
        
        # Get user permissions
        permissions = getattr(request, 'user_permissions', {})
        
        # Admin and Manager have access to all departments
        if permissions.get('role_name') in ['admin', 'manager']:
            return None
        
        # Check department restrictions
        restricted_departments = permissions.get('restricted_departments', [])
        
        if restricted_departments and department not in restricted_departments:
            return JsonResponse({
                'error': f'Access denied to {department} department',
                'code': 'DEPARTMENT_RESTRICTED',
                'allowed_departments': restricted_departments
            }, status=403)
        
        return None


class OperatorEngagementMiddleware(MiddlewareMixin):
    """
    Middleware to check operator engagement status
    """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Only check for operators
        permissions = getattr(request, 'user_permissions', {})
        if permissions.get('role_name') != 'operator':
            return None
        
        # Skip for certain endpoints
        skip_paths = [
            '/api/auth/logout/',
            '/api/auth/health/',
            '/api/auth/profile/',
            '/api/auth/dashboard/'
        ]
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Check if operator is engaged and trying to access other processes
        if hasattr(request.user, 'current_engagement'):
            engagement = request.user.current_engagement
            
            # Check if trying to access different batch/process
            requested_batch = request.GET.get('batch_id') or request.POST.get('batch_id')
            
            if requested_batch and requested_batch != engagement.batch_id:
                return JsonResponse({
                    'error': 'Operator is currently engaged in another process',
                    'code': 'OPERATOR_ENGAGED',
                    'current_batch': engagement.batch_id,
                    'current_process': engagement.process_step
                }, status=409)
        
        return None


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware for API endpoints
    """
    
    def process_request(self, request):
        if not request.path.startswith('/api/'):
            return None
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Rate limit: 1000 requests per hour per client
        cache_key = f'rate_limit_{client_id}'
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= 1000:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'code': 'RATE_LIMITED'
            }, status=429)
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, 3600)  # 1 hour
        
        return None
    
    def get_client_identifier(self, request):
        """Get unique client identifier"""
        if request.user.is_authenticated:
            return f'user_{request.user.id}'
        
        # Use IP for unauthenticated requests
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return f'ip_{ip}'
