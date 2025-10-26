from rest_framework import status, generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.db.models import Q, Prefetch, Count, Case, When, BooleanField
from django.utils import timezone
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.conf import settings

from .models import (
    CustomUser, UserProfile, Role, UserRole, 
    ProcessSupervisor, OperatorEngagement, LoginSession
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserDetailSerializer,
    UserListSerializer, ChangePasswordSerializer, RoleSerializer,
    UserRoleSerializer, ProcessSupervisorSerializer, OperatorEngagementSerializer,
    LoginSessionSerializer, BulkUserRoleAssignmentSerializer, AvailableOperatorsSerializer
)
from .permissions import IsAdminOrManager, IsManagerOrAbove, IsSupervisorOrAbove
from utils.enums import DepartmentChoices


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Enhanced JWT token obtain view with session tracking
    """
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        csrf_token = get_token(request)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        client_ip = serializer.validated_data['client_ip']
        user_agent = serializer.validated_data['user_agent']
        
        # Create login session
        LoginSession.objects.create(
            user=user,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Get user details with optimized query
        user_data = self.get_user_details(user)
        
        response = JsonResponse({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
        
        # Set CSRF token in cookie
        response.set_cookie(
            'csrftoken',
            csrf_token,
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,  # Secure in production
            max_age=60 * 60 * 24 * 30  # 30 days
        )
        
        # Set JWT tokens in HTTP-only cookies if needed
        response.set_cookie(
            'access_token',
            str(refresh.access_token),
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,
            max_age=60 * 60  # 1 hour
        )
        
        response.set_cookie(
            'refresh_token',
            str(refresh),
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,
            max_age=60 * 60 * 24 * 30  # 30 days
        )
        
        return response
    
    def get_user_details(self, user):
        """Get optimized user details for login response"""
        user_with_relations = CustomUser.objects.select_related(
            'profile'
        ).prefetch_related(
            Prefetch('user_roles', queryset=UserRole.objects.filter(is_active=True).select_related('role')),
            'process_supervisor_assignments',
            'current_engagement'
        ).get(id=user.id)
        
        return UserDetailSerializer(user_with_relations).data


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def register_user(request):
    """
    Register a new user (Admin/Manager only)
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        with transaction.atomic():
            user = serializer.save()
            
            # Get user with relations for response
            user_with_relations = CustomUser.objects.select_related(
                'profile'
            ).prefetch_related(
                'user_roles__role'
            ).get(id=user.id)
            
            return Response({
                'message': 'User registered successfully',
                'user': UserDetailSerializer(user_with_relations).data
            }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Enhanced logout with session tracking
    """
    try:
        refresh_token = request.data.get('refresh')
        
        # Update login session
        LoginSession.objects.filter(
            user=request.user,
            is_active=True
        ).update(
            logout_time=timezone.now(),
            is_active=False
        )
        
        # Blacklist token if provided
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(ModelViewSet):
    """
    Comprehensive user management with optimized queries
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'profile__department', 'profile__shift', 'profile__is_engaged']
    search_fields = ['first_name', 'last_name', 'email', 'profile__employee_id']
    ordering_fields = ['date_joined', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Optimized queryset with proper prefetching"""
        return CustomUser.objects.select_related(
            'profile'
        ).prefetch_related(
            Prefetch(
                'user_roles',
                queryset=UserRole.objects.filter(is_active=True).select_related('role', 'assigned_by')
            ),
            'process_supervisor_assignments',
            'current_engagement'
        ).annotate(
            has_active_role=Count('user_roles', filter=Q(user_roles__is_active=True)),
            is_supervisor=Count('process_supervisor_assignments', filter=Q(process_supervisor_assignments__is_active=True))
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return UserListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return UserRegistrationSerializer
        return UserDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminOrManager]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsManagerOrAbove]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def available_operators(self, request):
        """Get available operators (not engaged)"""
        operators = self.get_queryset().filter(
            profile__is_engaged=False,
            user_roles__role__name='operator',
            user_roles__is_active=True,
            is_active=True
        ).distinct()
        
        serializer = AvailableOperatorsSerializer(operators, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def supervisors_by_department(self, request):
        """Get supervisors grouped by department"""
        department = request.query_params.get('department')
        
        queryset = self.get_queryset().filter(
            user_roles__role__name='supervisor',
            user_roles__is_active=True,
            is_active=True
        )
        
        if department:
            queryset = queryset.filter(profile__department=department)
        
        serializer = UserListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """Assign role to user"""
        user = self.get_object()
        role_id = request.data.get('role_id')
        
        try:
            role = Role.objects.get(id=role_id)
            
            # Deactivate existing roles
            UserRole.objects.filter(user=user, is_active=True).update(is_active=False)
            
            # Create new role assignment
            UserRole.objects.create(
                user=user,
                role=role,
                assigned_by=request.user
            )
            
            return Response({'message': 'Role assigned successfully'})
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def engage_operator(self, request, pk=None):
        """Engage operator in a process"""
        operator = self.get_object()
        
        if operator.profile.is_engaged:
            return Response({'error': 'Operator is already engaged'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OperatorEngagementSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                # Create engagement
                engagement = serializer.save(operator=operator)
                
                # Update profile
                operator.profile.is_engaged = True
                operator.profile.save()
                
                return Response(OperatorEngagementSerializer(engagement).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def release_operator(self, request, pk=None):
        """Release operator from current engagement"""
        operator = self.get_object()
        
        try:
            with transaction.atomic():
                # Delete engagement
                OperatorEngagement.objects.filter(operator=operator).delete()
                
                # Update profile
                operator.profile.is_engaged = False
                operator.profile.save()
                
                return Response({'message': 'Operator released successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RoleViewSet(ReadOnlyModelViewSet):
    """
    Role management (read-only for most users)
    """
    queryset = Role.objects.all().order_by('hierarchy_level')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get role hierarchy"""
        roles = self.get_queryset()
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)


class ProcessSupervisorViewSet(ModelViewSet):
    """
    Process supervisor management
    """
    serializer_class = ProcessSupervisorSerializer
    permission_classes = [IsManagerOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'is_active']
    
    def get_queryset(self):
        return ProcessSupervisor.objects.select_related(
            'supervisor', 'supervisor__profile'
        ).filter(is_active=True)


class OperatorEngagementViewSet(ReadOnlyModelViewSet):
    """
    Operator engagement tracking (read-only)
    """
    serializer_class = OperatorEngagementSerializer
    permission_classes = [IsSupervisorOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['batch_id', 'process_step', 'machine_id']
    
    def get_queryset(self):
        return OperatorEngagement.objects.select_related(
            'operator', 'operator__profile'
        )


class LoginSessionViewSet(ReadOnlyModelViewSet):
    """
    Login session tracking (Admin only)
    """
    serializer_class = LoginSessionSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'is_active']
    ordering = ['-login_time']
    
    def get_queryset(self):
        return LoginSession.objects.select_related('user')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Enhanced password change
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Update session auth hash to prevent logout
        update_session_auth_hash(request, user)
        
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get current user profile with optimized query
    """
    user = CustomUser.objects.select_related(
        'profile'
    ).prefetch_related(
        Prefetch('user_roles', queryset=UserRole.objects.filter(is_active=True).select_related('role')),
        'process_supervisor_assignments',
        'current_engagement'
    ).get(id=request.user.id)
    
    serializer = UserDetailSerializer(user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def bulk_role_assignment(request):
    """
    Bulk role assignment for multiple users
    """
    serializer = BulkUserRoleAssignmentSerializer(data=request.data)
    if serializer.is_valid():
        user_ids = serializer.validated_data['user_ids']
        role_id = serializer.validated_data['role_id']
        
        try:
            with transaction.atomic():
                role = Role.objects.get(id=role_id)
                
                # Deactivate existing roles for all users
                UserRole.objects.filter(
                    user_id__in=user_ids,
                    is_active=True
                ).update(is_active=False)
                
                # Create new role assignments
                role_assignments = [
                    UserRole(user_id=user_id, role=role, assigned_by=request.user)
                    for user_id in user_ids
                ]
                UserRole.objects.bulk_create(role_assignments)
                
                return Response({
                    'message': f'Role assigned to {len(user_ids)} users successfully'
                })
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics
    """
    cache_key = f'dashboard_stats_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    # Calculate stats based on user role
    user_role = request.user.user_roles.filter(is_active=True).first()
    
    if not user_role:
        return Response({'error': 'No active role found'}, status=status.HTTP_400_BAD_REQUEST)
    
    stats = {}
    
    if user_role.role.name in ['admin', 'manager']:
        stats = {
            'total_users': CustomUser.objects.filter(is_active=True).count(),
            'engaged_operators': CustomUser.objects.filter(
                profile__is_engaged=True,
                is_active=True
            ).count(),
            'available_operators': CustomUser.objects.filter(
                profile__is_engaged=False,
                user_roles__role__name='operator',
                user_roles__is_active=True,
                is_active=True
            ).count(),
            'active_sessions': LoginSession.objects.filter(is_active=True).count(),
            'departments': dict(DepartmentChoices.choices)
        }
    elif user_role.role.name == 'supervisor':
        # Supervisor-specific stats
        supervised_dept = request.user.profile.department
        stats = {
            'department': supervised_dept,
            'available_operators': CustomUser.objects.filter(
                profile__department=supervised_dept,
                profile__is_engaged=False,
                user_roles__role__name='operator',
                user_roles__is_active=True,
                is_active=True
            ).count(),
            'engaged_operators': CustomUser.objects.filter(
                profile__department=supervised_dept,
                profile__is_engaged=True,
                is_active=True
            ).count()
        }
    
    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Enhanced health check endpoint
    """
    return Response({
        'status': 'healthy',
        'message': 'Authentication service is running',
        'timestamp': timezone.now(),
        'version': '1.0.0'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_permissions(request):
    """
    Get current user permissions
    """
    user = request.user
    active_role = user.user_roles.filter(is_active=True).select_related('role').first()
    
    if not active_role:
        return Response({'permissions': {}})
    
    permissions = active_role.role.permissions
    
    # Add computed permissions
    permissions['can_supervise'] = user.process_supervisor_assignments.filter(is_active=True).exists()
    permissions['department_access'] = active_role.role.restricted_departments
    permissions['hierarchy_level'] = active_role.role.hierarchy_level
    
    return Response({'permissions': permissions})


# Network restriction middleware helper
@api_view(['POST'])
@permission_classes([IsAdminOrManager])
def update_ip_restrictions(request):
    """
    Update IP restrictions for a user
    """
    user_id = request.data.get('user_id')
    ip_ranges = request.data.get('ip_ranges', [])
    
    try:
        user = CustomUser.objects.get(id=user_id)
        user.profile.allowed_ip_ranges = ip_ranges
        user.profile.save()
        
        return Response({'message': 'IP restrictions updated successfully'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)