from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import WorkflowNotification

User = get_user_model()


class WorkflowNotificationSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowNotification model"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    mo_id = serializers.CharField(source='related_mo.mo_id', read_only=True)
    
    class Meta:
        model = WorkflowNotification
        fields = [
            'id', 'notification_type', 'notification_type_display', 'title', 'message',
            'priority', 'priority_display', 'recipient', 'recipient_name',
            'related_mo', 'mo_id', 'related_batch', 'related_process_assignment',
            'is_read', 'read_at', 'action_required', 'action_taken', 'action_taken_at',
            'created_at', 'created_by', 'created_by_name', 'time_ago'
        ]
        read_only_fields = ['created_at', 'read_at', 'action_taken_at']
    
    def get_time_ago(self, obj):
        """Get human-readable time since notification was created"""
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        diff = now - obj.created_at
        
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
