from django.db import models
from django.contrib.auth import get_user_model
from utils.enums import ReportTypeChoices, ScheduleTypeChoices

User = get_user_model()


class ReportTemplate(models.Model):
    """
    Configurable report templates
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    report_type = models.CharField(max_length=20, choices=ReportTypeChoices.choices)
    
    # Query definition
    data_source_query = models.TextField()  # SQL or Django ORM query
    parameters = models.JSONField(default=dict)  # User-configurable parameters
    
    # Visualization
    chart_config = models.JSONField(default=dict)
    
    # Access
    accessible_roles = models.ManyToManyField('authentication.Role', related_name='report_templates')
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_reports')

    class Meta:
        verbose_name = 'Report Template'
        verbose_name_plural = 'Report Templates'

    def __str__(self):
        return f"{self.name} - {self.report_type}"


class ScheduledReport(models.Model):
    """
    Automated report scheduling
    """
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='scheduled_reports')
    name = models.CharField(max_length=100)
    
    # Schedule
    schedule_type = models.CharField(max_length=20, choices=ScheduleTypeChoices.choices)
    cron_expression = models.CharField(max_length=100, blank=True)
    
    # Parameters
    parameter_values = models.JSONField(default=dict)
    
    # Recipients
    recipients = models.ManyToManyField(User, related_name='scheduled_reports')
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Scheduled Report'
        verbose_name_plural = 'Scheduled Reports'

    def __str__(self):
        return f"{self.name} - {self.schedule_type}"