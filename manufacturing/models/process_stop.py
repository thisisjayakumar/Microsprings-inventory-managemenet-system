"""
Process Stop and Downtime Tracking Models
Handles temporary process stoppage with reason tracking and downtime calculation
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class ProcessStopReason(models.TextChoices):
    """Standard reasons for process stoppage"""
    MACHINE_BREAKDOWN = 'machine_breakdown', 'Machine Breakdown / Repair'
    POWER_CUT = 'power_cut', 'Power Cut'
    MAINTENANCE = 'maintenance', 'Maintenance'
    MATERIAL_SHORTAGE = 'material_shortage', 'Material Shortage'
    QUALITY_ISSUE = 'quality_issue', 'Quality Issue'
    OTHERS = 'others', 'Others'


class ProcessStop(models.Model):
    """
    Track process stoppages for manufacturing orders
    Includes stop/resume tracking with downtime calculation
    """
    # Relations
    batch = models.ForeignKey(
        'manufacturing.Batch',
        on_delete=models.CASCADE,
        related_name='process_stops'
    )
    mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='process_stops'
    )
    process_execution = models.ForeignKey(
        'manufacturing.MOProcessExecution',
        on_delete=models.CASCADE,
        related_name='process_stops'
    )
    
    # Stop details
    stopped_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='process_stops_created'
    )
    stop_reason = models.CharField(
        max_length=30,
        choices=ProcessStopReason.choices
    )
    stop_reason_detail = models.TextField(
        blank=True,
        help_text="Additional details for 'Others' or elaboration on standard reasons"
    )
    stopped_at = models.DateTimeField(auto_now_add=True)
    
    # Resume details
    is_resumed = models.BooleanField(default=False)
    resumed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='process_stops_resumed'
    )
    resumed_at = models.DateTimeField(null=True, blank=True)
    resume_notes = models.TextField(blank=True)
    
    # Downtime calculation
    downtime_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Calculated downtime in minutes"
    )
    
    # Notifications sent
    notification_sent_to_ph = models.BooleanField(default=False)
    notification_sent_to_manager = models.BooleanField(default=False)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-stopped_at']
        indexes = [
            models.Index(fields=['batch', 'is_resumed']),
            models.Index(fields=['mo', 'stopped_at']),
            models.Index(fields=['process_execution', '-stopped_at']),
        ]
    
    def __str__(self):
        status = "Resumed" if self.is_resumed else "Stopped"
        return f"{self.batch.batch_id} - {self.process_execution.process.name} [{status}]"
    
    def clean(self):
        """Validate process stop data"""
        if self.is_resumed and not self.resumed_at:
            raise ValidationError("resumed_at must be set when is_resumed is True")
        
        if self.is_resumed and self.resumed_at and self.resumed_at < self.stopped_at:
            raise ValidationError("resumed_at cannot be before stopped_at")
    
    def resume_process(self, resumed_by_user, notes=''):
        """
        Resume the stopped process
        Calculates downtime and updates status
        """
        if self.is_resumed:
            raise ValidationError("Process is already resumed")
        
        self.is_resumed = True
        self.resumed_by = resumed_by_user
        self.resumed_at = timezone.now()
        self.resume_notes = notes
        
        # Calculate downtime
        if self.stopped_at and self.resumed_at:
            delta = self.resumed_at - self.stopped_at
            self.downtime_minutes = int(delta.total_seconds() / 60)
        
        self.save()
        
        # Update process execution status back to in_progress
        if self.process_execution.status == 'stopped':
            self.process_execution.status = 'in_progress'
            self.process_execution.save()
        
        return self.downtime_minutes
    
    @property
    def current_downtime_minutes(self):
        """Calculate current downtime even if not resumed yet"""
        if self.is_resumed:
            return self.downtime_minutes
        
        if self.stopped_at:
            delta = timezone.now() - self.stopped_at
            return int(delta.total_seconds() / 60)
        
        return 0
    
    @property
    def stop_duration_display(self):
        """Human-readable duration"""
        minutes = self.current_downtime_minutes
        hours = minutes // 60
        mins = minutes % 60
        
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"


class ProcessDowntimeSummary(models.Model):
    """
    Aggregated downtime summary per process per day
    Used for analytics and reporting
    """
    date = models.DateField()
    process = models.ForeignKey(
        'processes.Process',
        on_delete=models.CASCADE,
        related_name='downtime_summaries'
    )
    
    # Aggregated metrics
    total_stops = models.PositiveIntegerField(default=0)
    total_downtime_minutes = models.PositiveIntegerField(default=0)
    
    # Breakdown by reason
    breakdown_machine = models.PositiveIntegerField(default=0)
    breakdown_power = models.PositiveIntegerField(default=0)
    breakdown_maintenance = models.PositiveIntegerField(default=0)
    breakdown_material = models.PositiveIntegerField(default=0)
    breakdown_quality = models.PositiveIntegerField(default=0)
    breakdown_others = models.PositiveIntegerField(default=0)
    
    # Audit
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date', 'process']
        ordering = ['-date', 'process__name']
        indexes = [
            models.Index(fields=['date', 'process']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.process.name} ({self.total_downtime_minutes}m)"
    
    @classmethod
    def update_summary(cls, date, process):
        """Update or create downtime summary for a specific date and process"""
        from django.db.models import Sum, Count
        
        stops = ProcessStop.objects.filter(
            process_execution__process=process,
            stopped_at__date=date,
            is_resumed=True  # Only count completed stop-resume cycles
        )
        
        summary, created = cls.objects.get_or_create(
            date=date,
            process=process
        )
        
        summary.total_stops = stops.count()
        summary.total_downtime_minutes = stops.aggregate(
            total=Sum('downtime_minutes')
        )['total'] or 0
        
        # Breakdown by reason
        summary.breakdown_machine = stops.filter(
            stop_reason='machine_breakdown'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.breakdown_power = stops.filter(
            stop_reason='power_cut'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.breakdown_maintenance = stops.filter(
            stop_reason='maintenance'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.breakdown_material = stops.filter(
            stop_reason='material_shortage'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.breakdown_quality = stops.filter(
            stop_reason='quality_issue'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.breakdown_others = stops.filter(
            stop_reason='others'
        ).aggregate(total=Sum('downtime_minutes'))['total'] or 0
        
        summary.save()
        
        return summary

