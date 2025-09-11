from django.contrib import admin
from .models import AlertRule, Alert, NotificationLog


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'alert_type', 'is_active')
    list_filter = ('alert_type', 'is_active')
    search_fields = ('name',)
    filter_horizontal = ('recipient_roles', 'recipient_users')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'status', 'triggered_at', 'acknowledged_by')
    list_filter = ('severity', 'status', 'triggered_at')
    search_fields = ('title', 'message', 'related_object_id')
    ordering = ('-triggered_at',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('alert', 'recipient', 'method', 'delivery_status', 'sent_at')
    list_filter = ('method', 'delivery_status', 'sent_at')
    search_fields = ('alert__title', 'recipient__email')
    ordering = ('-sent_at',)