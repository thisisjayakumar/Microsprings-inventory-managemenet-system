from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from .models import (
    CustomUser, UserProfile, Role, UserRole, 
    ProcessSupervisor, OperatorEngagement, LoginSession
)
from utils.enums import DepartmentChoices, ShiftChoices, RoleHierarchyChoices


class RoleSerializer(serializers.ModelSerializer):
    """
    Optimized Role serializer
    """
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'name_display', 'description', 'hierarchy_level', 
                 'permissions', 'restricted_departments']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Optimized UserProfile serializer with department and shift info
    """
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'employee_id', 'designation', 'department', 'department_display',
            'shift', 'shift_display', 'date_of_joining', 'phone_number',
            'is_active', 'is_engaged', 'allowed_ip_ranges'
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Optimized UserRole serializer with role details
    """
    role_details = RoleSerializer(source='role', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'role', 'role_details', 'assigned_by', 'assigned_by_name', 
                 'assigned_at', 'is_active']
        read_only_fields = ['id', 'assigned_at']


class ProcessSupervisorSerializer(serializers.ModelSerializer):
    """
    Process supervisor assignment serializer
    """
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    
    class Meta:
        model = ProcessSupervisor
        fields = ['id', 'supervisor', 'supervisor_name', 'process_names', 
                 'department', 'department_display', 'is_active']
        read_only_fields = ['id']


class OperatorEngagementSerializer(serializers.ModelSerializer):
    """
    Operator engagement tracking serializer
    """
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = OperatorEngagement
        fields = ['id', 'operator', 'operator_name', 'batch_id', 'process_step',
                 'machine_id', 'start_time', 'estimated_end_time', 'duration_minutes']
        read_only_fields = ['id', 'start_time']
    
    def get_duration_minutes(self, obj):
        """Calculate engagement duration in minutes"""
        if obj.start_time:
            end_time = obj.estimated_end_time or timezone.now()
            return int((end_time - obj.start_time).total_seconds() / 60)
        return 0


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive user serializer with optimized queries
    """
    full_name = serializers.ReadOnlyField()
    profile = UserProfileSerializer(read_only=True)
    user_roles = UserRoleSerializer(many=True, read_only=True)
    current_engagement = OperatorEngagementSerializer(read_only=True)
    process_supervisor_assignments = ProcessSupervisorSerializer(many=True, read_only=True)
    
    # Computed fields
    primary_role = serializers.SerializerMethodField()
    can_supervise = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'is_active', 'date_joined', 'updated_at',
            'profile', 'user_roles', 'current_engagement', 'process_supervisor_assignments',
            'primary_role', 'can_supervise', 'is_available'
        ]
        read_only_fields = ['id', 'username', 'date_joined', 'updated_at']
    
    def get_primary_role(self, obj):
        """Get the highest priority active role"""
        active_role = obj.user_roles.filter(is_active=True).select_related('role').first()
        return RoleSerializer(active_role.role).data if active_role else None
    
    def get_can_supervise(self, obj):
        """Check if user can supervise processes"""
        return obj.process_supervisor_assignments.filter(is_active=True).exists()
    
    def get_is_available(self, obj):
        """Check if operator is available for assignment"""
        return not hasattr(obj, 'current_engagement') or not obj.profile.is_engaged


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Enhanced user registration with profile creation
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    # Profile fields
    employee_id = serializers.CharField(max_length=20)
    designation = serializers.CharField(max_length=100)
    department = serializers.ChoiceField(choices=DepartmentChoices.choices)
    shift = serializers.ChoiceField(choices=ShiftChoices.choices, required=False)
    date_of_joining = serializers.DateField()
    
    # Role assignment
    role_name = serializers.ChoiceField(choices=RoleHierarchyChoices.choices)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone_number',
            'password', 'password_confirm', 'employee_id', 'designation',
            'department', 'shift', 'date_of_joining', 'role_name'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Check employee_id uniqueness
        if UserProfile.objects.filter(employee_id=attrs['employee_id']).exists():
            raise serializers.ValidationError("Employee ID already exists")
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        # Extract profile and role data
        profile_data = {
            'employee_id': validated_data.pop('employee_id'),
            'designation': validated_data.pop('designation'),
            'department': validated_data.pop('department'),
            'shift': validated_data.pop('shift', None),
            'date_of_joining': validated_data.pop('date_of_joining'),
        }
        role_name = validated_data.pop('role_name')
        validated_data.pop('password_confirm')
        
        # Create user
        user = CustomUser.objects.create_user(**validated_data)
        
        # Create profile
        UserProfile.objects.create(user=user, **profile_data)
        
        # Assign role
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role, assigned_by=None)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Enhanced login serializer with IP tracking
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        request = self.context.get('request')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            # Network restriction check
            if hasattr(user, 'profile') and user.profile.allowed_ip_ranges:
                client_ip = self.get_client_ip(request)
                if not self.is_ip_allowed(client_ip, user.profile.allowed_ip_ranges):
                    raise serializers.ValidationError('Access denied from this network')
            
            attrs['user'] = user
            attrs['client_ip'] = self.get_client_ip(request)
            attrs['user_agent'] = request.META.get('HTTP_USER_AGENT', '') if request else ''
        else:
            raise serializers.ValidationError('Must include email and password')
        return attrs
    
    def get_client_ip(self, request):
        """Get client IP address"""
        if not request:
            return '127.0.0.1'
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


class ChangePasswordSerializer(serializers.Serializer):
    """
    Enhanced password change serializer
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for user lists with minimal data
    """
    full_name = serializers.ReadOnlyField()
    department = serializers.CharField(source='profile.department', read_only=True)
    department_display = serializers.CharField(source='profile.get_department_display', read_only=True)
    employee_id = serializers.CharField(source='profile.employee_id', read_only=True)
    primary_role = serializers.SerializerMethodField()
    is_engaged = serializers.BooleanField(source='profile.is_engaged', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'full_name', 'email', 'employee_id', 'department', 
            'department_display', 'primary_role', 'is_active', 'is_engaged'
        ]
    
    def get_primary_role(self, obj):
        """Get primary role name only"""
        active_role = obj.user_roles.filter(is_active=True).select_related('role').first()
        return active_role.role.get_name_display() if active_role else None


class LoginSessionSerializer(serializers.ModelSerializer):
    """
    Login session tracking serializer
    """
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = LoginSession
        fields = ['id', 'user', 'user_name', 'ip_address', 'login_time', 
                 'logout_time', 'duration_minutes', 'is_active']
        read_only_fields = ['id', 'login_time']
    
    def get_duration_minutes(self, obj):
        """Calculate session duration"""
        if obj.logout_time:
            return int((obj.logout_time - obj.login_time).total_seconds() / 60)
        elif obj.is_active:
            return int((timezone.now() - obj.login_time).total_seconds() / 60)
        return 0


# Bulk operation serializers
class BulkUserRoleAssignmentSerializer(serializers.Serializer):
    """
    Bulk role assignment serializer
    """
    user_ids = serializers.ListField(child=serializers.IntegerField())
    role_id = serializers.IntegerField()
    
    def validate_role_id(self, value):
        if not Role.objects.filter(id=value).exists():
            raise serializers.ValidationError("Role does not exist")
        return value
    
    def validate_user_ids(self, value):
        existing_users = CustomUser.objects.filter(id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Some users do not exist")
        return value


class AvailableOperatorsSerializer(serializers.ModelSerializer):
    """
    Serializer for available operators (not engaged)
    """
    full_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='profile.employee_id', read_only=True)
    department = serializers.CharField(source='profile.department', read_only=True)
    shift = serializers.CharField(source='profile.shift', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'full_name', 'employee_id', 'department', 'shift']