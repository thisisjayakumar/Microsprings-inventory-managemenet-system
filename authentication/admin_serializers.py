"""
Admin Dashboard Serializers
Optimized serializers for admin dashboard with comprehensive user and role management
"""
from rest_framework import serializers
from django.db import transaction
from .models import CustomUser, UserProfile, Role, UserRole
from .serializers import RoleSerializer


class AdminUserListSerializer(serializers.ModelSerializer):
    """
    Compact serializer for admin dashboard user list
    Shows all essential information in one place
    """
    full_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='profile.employee_id', read_only=True)
    department = serializers.CharField(source='profile.department', read_only=True)
    department_display = serializers.CharField(source='profile.get_department_display', read_only=True)
    designation = serializers.CharField(source='profile.designation', read_only=True)
    shift = serializers.CharField(source='profile.shift', read_only=True)
    shift_display = serializers.CharField(source='profile.get_shift_display', read_only=True)
    
    # Roles
    roles = serializers.SerializerMethodField()
    primary_role = serializers.SerializerMethodField()
    
    # Status
    is_engaged = serializers.BooleanField(source='profile.is_engaged', read_only=True)
    profile_is_active = serializers.BooleanField(source='profile.is_active', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'full_name', 'employee_id',
            'department', 'department_display', 'designation',
            'shift', 'shift_display', 'is_active', 'profile_is_active',
            'is_engaged', 'roles', 'primary_role', 'date_joined'
        ]
    
    def get_roles(self, obj):
        """Get all active roles"""
        active_roles = obj.user_roles.filter(is_active=True)
        return [
            {
                'id': ur.role.id,
                'name': ur.role.name,
                'name_display': ur.role.get_name_display(),
                'assigned_at': ur.assigned_at,
                'assigned_by': ur.assigned_by.full_name if ur.assigned_by else None
            }
            for ur in active_roles
        ]
    
    def get_primary_role(self, obj):
        """Get primary role (highest hierarchy)"""
        active_role = obj.user_roles.filter(is_active=True).select_related('role').first()
        if active_role:
            return {
                'id': active_role.role.id,
                'name': active_role.role.name,
                'display': active_role.role.get_name_display()
            }
        return None


class AdminUserCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating users from admin dashboard
    """
    password = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)
    
    # Profile fields
    employee_id = serializers.CharField(max_length=20)
    designation = serializers.CharField(max_length=100)
    department = serializers.ChoiceField(choices=UserProfile.DEPARTMENT_CHOICES)
    shift = serializers.ChoiceField(choices=UserProfile.SHIFT_CHOICES, required=False, allow_null=True)
    date_of_joining = serializers.DateField()
    profile_phone_number = serializers.CharField(max_length=15, required=False)
    allowed_ip_ranges = serializers.ListField(child=serializers.CharField(), required=False)
    
    # Role assignment
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of role IDs to assign"
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'phone_number',
            'is_active', 'password', 'password_confirm',
            'employee_id', 'designation', 'department', 'shift', 'date_of_joining',
            'profile_phone_number', 'allowed_ip_ranges', 'role_ids'
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        # Password validation for create
        if self.instance is None:  # Creating new user
            if 'password' not in attrs or 'password_confirm' not in attrs:
                raise serializers.ValidationError("Password and password confirmation are required")
            if attrs['password'] != attrs['password_confirm']:
                raise serializers.ValidationError("Passwords don't match")
        else:  # Updating existing user
            if 'password' in attrs or 'password_confirm' in attrs:
                if attrs.get('password') != attrs.get('password_confirm'):
                    raise serializers.ValidationError("Passwords don't match")
        
        # Check employee_id uniqueness
        employee_id = attrs.get('employee_id')
        if employee_id:
            existing = UserProfile.objects.filter(employee_id=employee_id)
            if self.instance:
                existing = existing.exclude(user=self.instance)
            if existing.exists():
                raise serializers.ValidationError({"employee_id": "Employee ID already exists"})
        
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
            'phone_number': validated_data.pop('profile_phone_number', ''),
            'allowed_ip_ranges': validated_data.pop('allowed_ip_ranges', []),
        }
        role_ids = validated_data.pop('role_ids', [])
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        
        # Create user
        user = CustomUser.objects.create_user(password=password, **validated_data)
        
        # Create profile
        UserProfile.objects.create(user=user, **profile_data)
        
        # Assign roles
        if role_ids:
            roles = Role.objects.filter(id__in=role_ids)
            role_assignments = [
                UserRole(user=user, role=role, assigned_by=self.context.get('request').user)
                for role in roles
            ]
            UserRole.objects.bulk_create(role_assignments)
        
        return user
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Extract profile and role data
        profile_data = {}
        profile_fields = ['employee_id', 'designation', 'department', 'shift', 
                         'date_of_joining', 'profile_phone_number', 'allowed_ip_ranges']
        
        for field in profile_fields:
            if field in validated_data:
                if field == 'profile_phone_number':
                    profile_data['phone_number'] = validated_data.pop(field)
                else:
                    profile_data[field] = validated_data.pop(field)
        
        role_ids = validated_data.pop('role_ids', None)
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        
        # Update user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        
        # Update profile
        if profile_data:
            for attr, value in profile_data.items():
                setattr(instance.profile, attr, value)
            instance.profile.save()
        
        # Update roles
        if role_ids is not None:
            # Deactivate existing roles
            UserRole.objects.filter(user=instance, is_active=True).update(is_active=False)
            
            # Assign new roles
            roles = Role.objects.filter(id__in=role_ids)
            for role in roles:
                UserRole.objects.update_or_create(
                    user=instance,
                    role=role,
                    defaults={
                        'is_active': True,
                        'assigned_by': self.context.get('request').user
                    }
                )
        
        return instance


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating roles from admin dashboard
    """
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'hierarchy_level',
            'permissions', 'restricted_departments'
        ]
        read_only_fields = ['id']
    
    def validate_name(self, value):
        """Validate role name exists in choices"""
        valid_names = [choice[0] for choice in Role.ROLE_HIERARCHY]
        if value not in valid_names:
            raise serializers.ValidationError(f"Invalid role name. Must be one of: {', '.join(valid_names)}")
        return value


class AdminDashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for admin dashboard statistics
    """
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField()
    users_by_role = serializers.DictField()
    users_by_department = serializers.DictField()
    engaged_users = serializers.IntegerField()
    available_users = serializers.IntegerField()
    total_roles = serializers.IntegerField()
    active_sessions = serializers.IntegerField()


class BulkUserActionSerializer(serializers.Serializer):
    """
    Serializer for bulk user actions
    """
    user_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=[
        ('activate', 'Activate'),
        ('deactivate', 'Deactivate'),
        ('assign_role', 'Assign Role'),
        ('change_department', 'Change Department')
    ])
    
    # Optional fields for specific actions
    role_id = serializers.IntegerField(required=False)
    department = serializers.ChoiceField(choices=UserProfile.DEPARTMENT_CHOICES, required=False)
    
    def validate(self, attrs):
        action = attrs['action']
        
        if action == 'assign_role' and 'role_id' not in attrs:
            raise serializers.ValidationError("role_id is required for assign_role action")
        
        if action == 'change_department' and 'department' not in attrs:
            raise serializers.ValidationError("department is required for change_department action")
        
        return attrs


class UserRoleManagementSerializer(serializers.Serializer):
    """
    Serializer for managing user roles
    """
    user_id = serializers.IntegerField()
    role_ids = serializers.ListField(child=serializers.IntegerField())
    replace_existing = serializers.BooleanField(default=True)

