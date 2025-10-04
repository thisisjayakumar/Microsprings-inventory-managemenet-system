from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Alert, AlertRule, NotificationLog
from .serializers import AlertSerializer, AlertRuleSerializer, NotificationLogSerializer


class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alerts and notifications
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AlertSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'severity', 'alert_rule', 'related_object_type']
    search_fields = ['title', 'message']
    ordering_fields = ['triggered_at', 'severity']
    ordering = ['-triggered_at']

    def get_queryset(self):
        """Get alerts for current user based on their role"""
        user = self.request.user
        
        # Get alerts where user is explicitly added as recipient
        user_alerts = Alert.objects.filter(alert_rule__recipient_users=user)
        
        # Get alerts for user's roles
        user_roles = user.user_roles.values_list('role', flat=True)
        role_alerts = Alert.objects.filter(alert_rule__recipient_roles__in=user_roles)
        
        # Combine and return unique alerts
        return (user_alerts | role_alerts).distinct().select_related('alert_rule')

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """Get current user's active notifications"""
        alerts = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            'count': alerts.count(),
            'notifications': serializer.data
        })

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        
        if alert.status != 'active':
            return Response(
                {'error': 'Only active alerts can be acknowledged'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.status = 'acknowledged'
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response({
            'message': 'Alert acknowledged successfully',
            'alert': serializer.data
        })

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an alert"""
        alert = self.get_object()
        
        alert.status = 'dismissed'
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response({
            'message': 'Alert dismissed successfully',
            'alert': serializer.data
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications for current user"""
        count = self.get_queryset().filter(status='active').count()
        return Response({'unread_count': count})


class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alert rules (Admin only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AlertRuleSerializer
    queryset = AlertRule.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['alert_type', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        """Only allow managers to view/edit alert rules"""
        if self.request.user.user_roles.filter(role__name='manager').exists():
            return AlertRule.objects.all()
        return AlertRule.objects.none()


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notification delivery logs
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationLogSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['method', 'delivery_status']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']

    def get_queryset(self):
        """Get notification logs for current user"""
        return NotificationLog.objects.filter(recipient=self.request.user).select_related('alert')