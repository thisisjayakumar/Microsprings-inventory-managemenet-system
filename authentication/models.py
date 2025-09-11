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
    Extended user profile information
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    date_of_joining = models.DateField()
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    
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
    Role-based access control
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    permissions = models.JSONField(default=dict)  # Flexible permission system
    
    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


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