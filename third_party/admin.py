from django.contrib import admin
from django.utils.html import format_html
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'vendor_type', 'gst_no', 'contact_no', 
        'contact_person', 'get_status', 'created_at'
    )
    list_filter = ('vendor_type', 'is_active', 'created_at')
    search_fields = ('name', 'gst_no', 'contact_person', 'contact_no')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'vendor_type', 'is_active')
        }),
        ('Legal & Contact Details', {
            'fields': ('gst_no', 'contact_no', 'email', 'contact_person')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status(self, obj):
        """Display active/inactive status with color coding"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">●</span> Active'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">●</span> Inactive'
            )
    
    get_status.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Custom actions
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vendor(s) marked as active.')
    make_active.short_description = "Mark selected vendors as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vendor(s) marked as inactive.')
    make_inactive.short_description = "Mark selected vendors as inactive"
