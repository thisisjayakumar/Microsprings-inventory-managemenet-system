from django.contrib import admin
from .models import PatrolDuty, PatrolUpload, PatrolAlert


@admin.register(PatrolDuty)
class PatrolDutyAdmin(admin.ModelAdmin):
    list_display = ['id', 'patrol_user', 'status', 'start_date', 'end_date', 'frequency_hours', 'created_by']
    list_filter = ['status', 'start_date', 'end_date', 'shift_type']
    search_fields = ['patrol_user__first_name', 'patrol_user__last_name', 'patrol_user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Assignment', {
            'fields': ('patrol_user', 'created_by', 'status')
        }),
        ('Processes', {
            'fields': ('process_names',)
        }),
        ('Timing', {
            'fields': ('frequency_hours', 'shift_start_time', 'shift_end_time', 'shift_type', 'start_date', 'end_date')
        }),
        ('Notes', {
            'fields': ('remarks',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatrolUpload)
class PatrolUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'duty', 'process_name', 'scheduled_date', 'scheduled_time', 'status', 'upload_timestamp']
    list_filter = ['status', 'scheduled_date', 'is_reuploaded']
    search_fields = ['duty__patrol_user__first_name', 'duty__patrol_user__last_name', 'process_name']
    readonly_fields = ['created_at', 'updated_at', 'first_upload_time', 'reupload_deadline']
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Duty & Process', {
            'fields': ('duty', 'process_name')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'scheduled_time')
        }),
        ('Upload', {
            'fields': ('qc_image', 'upload_timestamp', 'status', 'patrol_remarks')
        }),
        ('Reupload Tracking', {
            'fields': ('is_reuploaded', 'first_upload_time', 'reupload_deadline')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatrolAlert)
class PatrolAlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'alert_type', 'recipient', 'is_read', 'is_action_taken', 'created_at']
    list_filter = ['alert_type', 'is_read', 'is_action_taken', 'created_at']
    search_fields = ['recipient__first_name', 'recipient__last_name', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Details', {
            'fields': ('duty', 'upload', 'alert_type', 'message')
        }),
        ('Recipient', {
            'fields': ('recipient', 'is_read', 'is_action_taken')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

