from django.db import models
from django.contrib.auth import get_user_model
from utils.enums import (
    NotificationAlertTypeChoices, SeverityChoices, AlertStatusChoices,
    DeliveryStatusChoices, WorkflowNotificationTypeChoices, PriorityChoices
)

User = get_user_model()


class AlertRule(models.Model):
    """
    Configurable alert rules
    """
    
    name = models.CharField(max_length=100)
    trigger_condition = models.JSONField()  # Define conditions in JSON
    alert_type = models.CharField(max_length=20, choices=NotificationAlertTypeChoices.choices)
    
    # Notification settings
    recipient_roles = models.ManyToManyField('authentication.Role', related_name='alert_rules')
    recipient_users = models.ManyToManyField(User, blank=True, related_name='alert_rules')
    notification_methods = models.JSONField(default=list)  # ['email', 'sms', 'in_app']
    
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'

    def __str__(self):
        return f"{self.name} - {self.alert_type}"


class Alert(models.Model):
    """
    Generated alerts
    """
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SeverityChoices.choices)
    
    # Context
    related_object_type = models.CharField(max_length=20, null=True, blank=True)  # 'batch', 'mo', 'machine'
    related_object_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=AlertStatusChoices.choices, default='active')
    
    # Timing
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')

    class Meta:
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'

    def __str__(self):
        return f"{self.title} - {self.severity}"


class NotificationLog(models.Model):
    """
    Track notification delivery
    """
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notification_logs')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    method = models.CharField(max_length=20)  # 'email', 'sms', 'in_app'
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, choices=DeliveryStatusChoices.choices, default='pending')

    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'

    def __str__(self):
        return f"{self.alert.title} -> {self.recipient.email} via {self.method}"


# Enhanced Workflow Notifications

class WorkflowNotification(models.Model):
    """
    Workflow-specific notifications for MO process assignments and updates
    """
    # Notification details
    notification_type = models.CharField(max_length=30, choices=WorkflowNotificationTypeChoices.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PriorityChoices.choices, default='medium')
    
    # Recipients
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='workflow_notifications'
    )
    
    # Related objects
    related_mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    related_batch = models.ForeignKey(
        'manufacturing.Batch',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    related_process_assignment = models.ForeignKey(
        'manufacturing.ProcessAssignment',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action tracking
    action_required = models.BooleanField(default=False)
    action_taken = models.BooleanField(default=False)
    action_taken_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_workflow_notifications'
    )
    
    class Meta:
        verbose_name = 'Workflow Notification'
        verbose_name_plural = 'Workflow Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.email}"


class NotificationTemplate(models.Model):
    """
    Templates for workflow notifications
    """
    notification_type = models.CharField(max_length=30, choices=WorkflowNotificationTypeChoices.choices, unique=True)
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    
    # Template variables documentation
    variables = models.JSONField(
        default=list,
        help_text="List of available variables for this template (e.g., ['mo_id', 'product_name', 'operator_name'])"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
    
    def __str__(self):
        return f"{self.get_notification_type_display()} Template"
