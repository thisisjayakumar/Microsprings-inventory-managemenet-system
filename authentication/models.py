from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(models.Model):
    """
    Extended user profile information for MSP-ERP
    """
    DEPARTMENT_CHOICES = [
        ('rm_store', 'RM Store'),
        ('coiling', 'Coiling'),
        ('tempering', 'Tempering'),
        ('plating', 'Plating'),
        ('packing', 'Packing'),
        ('fg_store', 'FG Store'),
        ('quality', 'Quality Control'),
        ('maintenance', 'Maintenance'),
        ('admin', 'Administration')
    ]
    
    SHIFT_CHOICES = [
        ('I', '9AM-5PM (Shift I)'),
        ('II', '5PM-2AM (Shift II)'),
        ('III', '2AM-9AM (Shift III)')
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, null=True, blank=True)
    date_of_joining = models.DateField()
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    is_engaged = models.BooleanField(default=False, help_text="Currently assigned to a process")
    
    # Network access control
    allowed_ip_ranges = models.JSONField(default=list, help_text="Allowed IP ranges for network restriction")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.full_name} - {self.employee_id}"


class Role(models.Model):
    """
    Hierarchical role-based access control for MSP-ERP
    """
    ROLE_HIERARCHY = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('supervisor', 'Supervisor'),
        ('store_manager', 'Store Manager'),
        ('operator', 'Operator')
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_HIERARCHY, unique=True)
    description = models.TextField()
    hierarchy_level = models.IntegerField(default=5, help_text="Lower number = higher authority")
    permissions = models.JSONField(default=dict)  # Module-specific permissions
    
    # Department restrictions
    restricted_departments = models.JSONField(default=list, help_text="Departments this role can access")
    
    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['hierarchy_level']

    def __str__(self):
        return self.get_name_display()
    
    def can_access_department(self, department):
        """Check if role can access specific department"""
        if not self.restricted_departments:
            return True  # No restrictions
        return department in self.restricted_departments


class UserRole(models.Model):
    """
    User role assignments with audit trail
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='roles_assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'role']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f"{self.user.full_name} - {self.role.name}"


class ProcessSupervisor(models.Model):
    """
    Process-specific supervisor assignments
    """
    supervisor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='process_supervisor_assignments')
    process_names = models.JSONField(default=list, help_text="List of process names this supervisor handles")
    department = models.CharField(max_length=20, choices=UserProfile.DEPARTMENT_CHOICES)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['supervisor', 'department']
        verbose_name = 'Process Supervisor'
        verbose_name_plural = 'Process Supervisors'
    
    def __str__(self):
        return f"{self.supervisor.full_name} - {self.get_department_display()}"


class OperatorEngagement(models.Model):
    """
    Track operator engagement to prevent double assignment
    """
    operator = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='current_engagement')
    batch_id = models.CharField(max_length=20, null=True, blank=True)
    process_step = models.CharField(max_length=100, null=True, blank=True)
    machine_id = models.CharField(max_length=20, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    estimated_end_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Operator Engagement'
        verbose_name_plural = 'Operator Engagements'
    
    def __str__(self):
        return f"{self.operator.full_name} - {self.batch_id or 'Available'}"


class LoginSession(models.Model):
    """
    Track user login sessions for network restriction
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='login_sessions')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Login Session'
        verbose_name_plural = 'Login Sessions'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"