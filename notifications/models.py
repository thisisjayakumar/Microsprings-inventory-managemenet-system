from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AlertRule(models.Model):
    """
    Configurable alert rules
    """
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('delay', 'Process Delay'),
        ('quality_fail', 'Quality Failure'),
        ('machine_down', 'Machine Breakdown'),
        ('custom', 'Custom Rule')
    ]
    
    name = models.CharField(max_length=100)
    trigger_condition = models.JSONField()  # Define conditions in JSON
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    
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
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed')
    ]
    
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    
    # Context
    related_object_type = models.CharField(max_length=20, null=True, blank=True)  # 'batch', 'mo', 'machine'
    related_object_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
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
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed')
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notification_logs')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    method = models.CharField(max_length=20)  # 'email', 'sms', 'in_app'
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'

    def __str__(self):
        return f"{self.alert.title} -> {self.recipient.email} via {self.method}"