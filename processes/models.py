from django.db import models
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import RawMaterial

User = get_user_model()


class Process(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SubProcess(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='subprocesses')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['process', 'name']

    def __str__(self):
        return f"{self.process.name} -> {self.name}"


class ProcessStep(models.Model):
    """
    Defines the sequence of process steps for manufacturing
    """
    step_name = models.CharField(max_length=100)
    step_code = models.CharField(max_length=255, unique=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='process_steps')
    subprocess = models.ForeignKey(
        SubProcess, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='process_steps'
    )
    sequence_order = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_order']
        unique_together = [['step_code', 'process']]

    def __str__(self):
        if self.subprocess:
            return f"{self.step_name} ({self.process.name} -> {self.subprocess.name})"
        return f"{self.step_name} ({self.process.name})"

    def clean(self):
        if self.subprocess and self.subprocess.process != self.process:
            raise ValidationError("Subprocess must belong to the selected process")

    @property
    def full_path(self):
        if self.subprocess:
            return f"{self.process.name} -> {self.subprocess.name} -> {self.step_name}"
        return f"{self.process.name} -> {self.step_name}"


class BOM(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('spring', 'Spring'),
        ('stamp', 'Stamp'),
    ]

    product_code = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    process_step = models.ForeignKey(
        ProcessStep, 
        on_delete=models.CASCADE,
        help_text="Specific process step with ordering"
    )
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, to_field='material_code', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_code','type']
        unique_together = [['product_code', 'process_step', 'material']]

    def __str__(self):
        return f"{self.product_code} ({self.type}) - {self.process_step.full_path}"

    @property
    def main_process(self):
        return self.process_step.process

    @property
    def subprocess(self):
        return self.process_step.subprocess

    def clean(self):
        # Add any BOM-specific validation here if needed
        super().clean()


class WorkCenterMaster(models.Model):
    """
    Work Center Master - Defines supervisor assignments for each work center (Process)
    Each work center has a default supervisor and backup supervisor
    """
    work_center = models.OneToOneField(
        Process, 
        on_delete=models.CASCADE, 
        related_name='work_center_master',
        help_text="Process that serves as work center"
    )
    
    # Supervisor assignments
    default_supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='default_work_centers',
        help_text="Main supervisor assigned to this work center"
    )
    backup_supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='backup_work_centers',
        help_text="Alternate supervisor for this work center"
    )
    
    # Check-in settings
    check_in_deadline = models.TimeField(
        default='09:15:00',
        help_text="Time by which supervisor should log in (e.g., 9:15 AM)"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Active work center")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_centers'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_work_centers'
    )
    
    class Meta:
        verbose_name = 'Work Center Master'
        verbose_name_plural = 'Work Center Masters'
        ordering = ['work_center__name']
    
    def __str__(self):
        return f"{self.work_center.name} - {self.default_supervisor.get_full_name()}"
    
    def clean(self):
        """Validate that default and backup supervisors are different"""
        if self.default_supervisor == self.backup_supervisor:
            raise ValidationError("Default and backup supervisors must be different users")
        
        # Validate that both users have supervisor role
        if not self.default_supervisor.user_roles.filter(role__name='supervisor', is_active=True).exists():
            raise ValidationError(f"{self.default_supervisor.get_full_name()} is not assigned as a supervisor")
        
        if not self.backup_supervisor.user_roles.filter(role__name='supervisor', is_active=True).exists():
            raise ValidationError(f"{self.backup_supervisor.get_full_name()} is not assigned as a supervisor")


class DailySupervisorStatus(models.Model):
    """
    Auto-generated daily record of supervisor status for each work center
    Tracks whether default supervisor is present and who is the active supervisor
    """
    date = models.DateField(help_text="Date of this status record")
    work_center = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name='daily_supervisor_status',
        help_text="Work center for this status"
    )
    default_supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='daily_default_supervisor_status',
        help_text="Default supervisor for this work center on this date"
    )
    is_present = models.BooleanField(
        default=False,
        help_text="Whether default supervisor logged in before deadline"
    )
    active_supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='daily_active_supervisor_status',
        help_text="Active supervisor for this work center today (default or backup)"
    )
    
    # Login tracking
    login_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time when default supervisor logged in"
    )
    check_in_deadline = models.TimeField(
        help_text="Deadline time for check-in on this date"
    )
    
    # Manual override
    manually_updated = models.BooleanField(
        default=False,
        help_text="Whether this record was manually updated by admin"
    )
    manually_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manually_updated_supervisor_status'
    )
    manually_updated_at = models.DateTimeField(null=True, blank=True)
    manual_update_reason = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Daily Supervisor Status'
        verbose_name_plural = 'Daily Supervisor Statuses'
        ordering = ['-date', 'work_center__name']
        unique_together = [['date', 'work_center']]
        indexes = [
            models.Index(fields=['date', 'work_center']),
            models.Index(fields=['date', 'is_present']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.work_center.name} - {self.active_supervisor.get_full_name()}"
    
    @property
    def status_color(self):
        """Returns color code for frontend display"""
        if self.is_present:
            return 'green'  # Default supervisor present
        else:
            return 'red'  # Backup supervisor active


class SupervisorActivityLog(models.Model):
    """
    Daily log of supervisor activity - tracks which supervisor handled which work center
    and how many MOs/operations they managed
    """
    date = models.DateField(help_text="Date of activity")
    work_center = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name='supervisor_activity_logs',
        help_text="Work center"
    )
    active_supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='supervisor_activity_logs',
        help_text="Supervisor who was active"
    )
    
    # Activity metrics
    mos_handled = models.PositiveIntegerField(
        default=0,
        help_text="Number of MOs handled"
    )
    total_operations = models.PositiveIntegerField(
        default=0,
        help_text="Total operations/process executions handled"
    )
    operations_completed = models.PositiveIntegerField(
        default=0,
        help_text="Operations completed"
    )
    operations_in_progress = models.PositiveIntegerField(
        default=0,
        help_text="Operations in progress"
    )
    
    # Additional tracking
    total_processing_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total processing time in minutes"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Supervisor Activity Log'
        verbose_name_plural = 'Supervisor Activity Logs'
        ordering = ['-date', 'work_center__name']
        unique_together = [['date', 'work_center', 'active_supervisor']]
        indexes = [
            models.Index(fields=['date', 'work_center']),
            models.Index(fields=['date', 'active_supervisor']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.work_center.name} - {self.active_supervisor.get_full_name()}"
