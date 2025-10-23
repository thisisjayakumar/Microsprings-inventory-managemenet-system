"""
Admin Dashboard Views
Comprehensive user and role management for administrators
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Prefetch
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError

from .models import CustomUser, UserProfile, Role, UserRole, LoginSession
from .admin_serializers import (
    AdminUserListSerializer, AdminUserCreateUpdateSerializer,
    RoleCreateUpdateSerializer, AdminDashboardStatsSerializer,
    BulkUserActionSerializer, UserRoleManagementSerializer, RoleSerializer
)
from .permissions import IsAdminOrManager


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """
    Comprehensive user management for admin dashboard
    All CRUD operations in one place
    """
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'profile__department', 'profile__shift', 'profile__is_engaged']
    search_fields = ['first_name', 'last_name', 'email', 'profile__employee_id', 'username']
    ordering_fields = ['date_joined', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Optimized queryset with all relations"""
        return CustomUser.objects.select_related(
            'profile'
        ).prefetch_related(
            Prefetch(
                'user_roles',
                queryset=UserRole.objects.filter(is_active=True).select_related('role', 'assigned_by')
            )
        ).annotate(
            role_count=Count('user_roles', filter=Q(user_roles__is_active=True))
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AdminUserListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AdminUserCreateUpdateSerializer
        return AdminUserListSerializer
    
    def perform_create(self, serializer):
        """Create user with audit trail"""
        serializer.save()
    
    def perform_update(self, serializer):
        """Update user with audit trail"""
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete user with proper error handling for protected foreign keys
        """
        user = self.get_object()
        
        try:
            user_name = user.get_full_name() or user.username
            user.delete()
            return Response({
                'message': f'User {user_name} has been deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        
        except ProtectedError as e:
            # Parse the protected error to extract model information
            protected_objects = e.protected_objects
            model_names = set()
            
            for obj in protected_objects:
                model_name = obj._meta.verbose_name_plural or obj._meta.model_name
                model_names.add(model_name)
            
            models_list = ', '.join(model_names)
            
            return Response({
                'error': f'Cannot delete user {user_name}',
                'detail': f'This user is referenced in the following records: {models_list}',
                'suggestion': 'Consider deactivating the user instead of deleting them.',
                'action': 'deactivate',
                'protected_models': list(model_names)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'error': 'Failed to delete user',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Perform bulk actions on multiple users
        """
        serializer = BulkUserActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_ids = serializer.validated_data['user_ids']
        action_type = serializer.validated_data['action']
        
        try:
            with transaction.atomic():
                users = CustomUser.objects.filter(id__in=user_ids)
                
                if action_type == 'activate':
                    users.update(is_active=True)
                    UserProfile.objects.filter(user__in=users).update(is_active=True)
                    message = f'Activated {users.count()} users'
                
                elif action_type == 'deactivate':
                    users.update(is_active=False)
                    UserProfile.objects.filter(user__in=users).update(is_active=False)
                    message = f'Deactivated {users.count()} users'
                
                elif action_type == 'assign_role':
                    role_id = serializer.validated_data['role_id']
                    role = Role.objects.get(id=role_id)
                    
                    # Deactivate existing roles
                    UserRole.objects.filter(
                        user__in=users,
                        is_active=True
                    ).update(is_active=False)
                    
                    # Create new role assignments
                    role_assignments = [
                        UserRole(user=user, role=role, assigned_by=request.user)
                        for user in users
                    ]
                    UserRole.objects.bulk_create(role_assignments)
                    message = f'Assigned role {role.get_name_display()} to {users.count()} users'
                
                elif action_type == 'change_department':
                    department = serializer.validated_data['department']
                    UserProfile.objects.filter(user__in=users).update(department=department)
                    dept_display = dict(UserProfile.DEPARTMENT_CHOICES).get(department, department)
                    message = f'Changed department to {dept_display} for {users.count()} users'
                
                return Response({
                    'message': message,
                    'affected_users': users.count()
                })
        
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def manage_roles(self, request, pk=None):
        """
        Manage roles for a specific user
        """
        user = self.get_object()
        serializer = UserRoleManagementSerializer(data={
            'user_id': user.id,
            **request.data
        })
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        role_ids = serializer.validated_data['role_ids']
        replace_existing = serializer.validated_data['replace_existing']
        
        try:
            with transaction.atomic():
                if replace_existing:
                    # Deactivate all existing roles
                    UserRole.objects.filter(user=user, is_active=True).update(is_active=False)
                
                # Assign new roles
                roles = Role.objects.filter(id__in=role_ids)
                for role in roles:
                    UserRole.objects.update_or_create(
                        user=user,
                        role=role,
                        defaults={
                            'is_active': True,
                            'assigned_by': request.user
                        }
                    )
                
                # Return updated user
                user_serializer = AdminUserListSerializer(user)
                return Response({
                    'message': f'Roles updated successfully for {user.full_name}',
                    'user': user_serializer.data
                })
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """
        Reset user password (admin only)
        """
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response({'error': 'new_password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate password
            validate_password(new_password, user)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            return Response({'message': f'Password reset successfully for {user.full_name}'})
        
        except DjangoValidationError as e:
            return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle user active status
        """
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        # Also update profile
        if hasattr(user, 'profile'):
            user.profile.is_active = user.is_active
            user.profile.save()
        
        status_text = 'activated' if user.is_active else 'deactivated'
        return Response({
            'message': f'User {user.full_name} has been {status_text}',
            'is_active': user.is_active
        })


class AdminRoleManagementViewSet(viewsets.ModelViewSet):
    """
    Full CRUD operations for roles
    """
    queryset = Role.objects.all().order_by('hierarchy_level')
    serializer_class = RoleCreateUpdateSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['hierarchy_level', 'name']
    ordering = ['hierarchy_level']
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of roles with assigned users"""
        role = self.get_object()
        
        # Check if role has active assignments
        active_assignments = UserRole.objects.filter(role=role, is_active=True).count()
        if active_assignments > 0:
            return Response({
                'error': f'Cannot delete role with {active_assignments} active user assignments. Deactivate users first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Get all users assigned to this role
        """
        role = self.get_object()
        users = CustomUser.objects.filter(
            user_roles__role=role,
            user_roles__is_active=True
        ).select_related('profile').prefetch_related('user_roles')
        
        serializer = AdminUserListSerializer(users, many=True)
        return Response({
            'role': RoleSerializer(role).data,
            'user_count': users.count(),
            'users': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """
        Get role hierarchy with user counts
        """
        roles = self.get_queryset().annotate(
            active_users=Count('role_users', filter=Q(role_users__is_active=True))
        )
        
        data = [
            {
                'id': role.id,
                'name': role.name,
                'name_display': role.get_name_display(),
                'hierarchy_level': role.hierarchy_level,
                'active_users': role.active_users,
                'description': role.description
            }
            for role in roles
        ]
        
        return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminOrManager])
def admin_dashboard_stats(request):
    """
    Get comprehensive statistics for admin dashboard
    """
    # User statistics
    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    engaged_users = CustomUser.objects.filter(profile__is_engaged=True).count()
    available_users = CustomUser.objects.filter(
        profile__is_engaged=False,
        is_active=True
    ).count()
    
    # Users by role
    users_by_role = {}
    for role in Role.objects.all():
        count = UserRole.objects.filter(role=role, is_active=True).count()
        users_by_role[role.get_name_display()] = count
    
    # Users by department
    users_by_department = {}
    for dept_code, dept_name in UserProfile.DEPARTMENT_CHOICES:
        count = UserProfile.objects.filter(department=dept_code, is_active=True).count()
        users_by_department[dept_name] = count
    
    # Role statistics
    total_roles = Role.objects.count()
    
    # Session statistics
    active_sessions = LoginSession.objects.filter(is_active=True).count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'users_by_role': users_by_role,
        'users_by_department': users_by_department,
        'engaged_users': engaged_users,
        'available_users': available_users,
        'total_roles': total_roles,
        'active_sessions': active_sessions
    }
    
    serializer = AdminDashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminOrManager])
def users_with_multiple_roles(request):
    """
    Get users with multiple active roles
    """
    users = CustomUser.objects.annotate(
        role_count=Count('user_roles', filter=Q(user_roles__is_active=True))
    ).filter(role_count__gt=1).select_related('profile').prefetch_related('user_roles')
    
    serializer = AdminUserListSerializer(users, many=True)
    return Response({
        'count': users.count(),
        'users': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminOrManager])
def users_without_roles(request):
    """
    Get users without any active roles
    """
    users = CustomUser.objects.annotate(
        role_count=Count('user_roles', filter=Q(user_roles__is_active=True))
    ).filter(role_count=0).select_related('profile')
    
    serializer = AdminUserListSerializer(users, many=True)
    return Response({
        'count': users.count(),
        'users': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def sync_user_profile_status(request):
    """
    Sync user.is_active with profile.is_active for all users
    """
    try:
        with transaction.atomic():
            # Update profiles to match user is_active status
            updated = 0
            for user in CustomUser.objects.select_related('profile'):
                if hasattr(user, 'profile'):
                    if user.profile.is_active != user.is_active:
                        user.profile.is_active = user.is_active
                        user.profile.save()
                        updated += 1
            
            return Response({
                'message': f'Synced {updated} user profiles',
                'updated_count': updated
            })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminOrManager])
def department_summary(request):
    """
    Get summary of users by department with role breakdown
    """
    department_data = []
    
    for dept_code, dept_name in UserProfile.DEPARTMENT_CHOICES:
        users = CustomUser.objects.filter(
            profile__department=dept_code,
            is_active=True
        ).prefetch_related('user_roles__role')
        
        role_breakdown = {}
        for user in users:
            for user_role in user.user_roles.filter(is_active=True):
                role_name = user_role.role.get_name_display()
                role_breakdown[role_name] = role_breakdown.get(role_name, 0) + 1
        
        department_data.append({
            'department': dept_name,
            'department_code': dept_code,
            'total_users': users.count(),
            'engaged_users': users.filter(profile__is_engaged=True).count(),
            'available_users': users.filter(profile__is_engaged=False).count(),
            'role_breakdown': role_breakdown
        })
    
    return Response(department_data)


@api_view(['GET'])
@permission_classes([IsAdminOrManager])
def role_permissions_matrix(request):
    """
    Get a matrix of all roles and their permissions
    """
    roles = Role.objects.all().order_by('hierarchy_level')
    
    matrix = [
        {
            'id': role.id,
            'name': role.get_name_display(),
            'hierarchy_level': role.hierarchy_level,
            'permissions': role.permissions or {},
            'restricted_departments': role.restricted_departments or [],
            'active_users': UserRole.objects.filter(role=role, is_active=True).count()
        }
        for role in roles
    ]
    
    return Response(matrix)

