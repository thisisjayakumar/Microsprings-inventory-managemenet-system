from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Alert, AlertRule, NotificationLog

User = get_user_model()


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for AlertRule model"""
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'trigger_condition', 'alert_type', 
            'notification_methods', 'is_active', 'recipient_roles', 
            'recipient_users'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model"""
    alert_rule_name = serializers.CharField(source='alert_rule.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    time_since_triggered = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_rule', 'alert_rule_name', 'title', 'message', 
            'severity', 'severity_display', 'related_object_type', 
            'related_object_id', 'status', 'status_display', 
            'triggered_at', 'acknowledged_at', 'acknowledged_by', 
            'acknowledged_by_name', 'time_since_triggered'
        ]
        read_only_fields = ['triggered_at', 'acknowledged_at', 'acknowledged_by']
    
    def get_time_since_triggered(self, obj):
        """Get human-readable time since alert was triggered"""
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        diff = now - obj.triggered_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for NotificationLog model"""
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    delivery_status_display = serializers.CharField(source='get_delivery_status_display', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'alert', 'alert_title', 'recipient', 'method', 
            'sent_at', 'delivery_status', 'delivery_status_display'
        ]
        read_only_fields = ['sent_at']
