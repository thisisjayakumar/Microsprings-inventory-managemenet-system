from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile, Role, UserRole


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for CustomUser model
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile model
    """
    list_display = ('user', 'employee_id', 'designation', 'department', 'date_of_joining', 'is_active')
    list_filter = ('department', 'designation', 'is_active', 'date_of_joining')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id', 'designation')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Information', {'fields': ('user', 'employee_id')}),
        ('Professional Details', {'fields': ('designation', 'department', 'date_of_joining')}),
        ('Contact', {'fields': ('phone_number',)}),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Role model
    """
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserRole model
    """
    list_display = ('user', 'role', 'assigned_by', 'assigned_at', 'is_active')
    list_filter = ('role', 'is_active', 'assigned_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'role__name')
    ordering = ('-assigned_at',)