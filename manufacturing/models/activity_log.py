"""
Process Activity Logging Models
Comprehensive tracking of all supervisor and process events
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ActivityType(models.TextChoices):
    """Types of activities tracked"""
    # Process control
    PROCESS_STARTED = 'process_started', 'Process Started'
    PROCESS_COMPLETED = 'process_completed', 'Process Completed'
    PROCESS_STOPPED = 'process_stopped', 'Process Stopped'
    PROCESS_RESUMED = 'process_resumed', 'Process Resumed'
    
    # Batch operations
    BATCH_STARTED = 'batch_started', 'Batch Started'
    BATCH_COMPLETED = 'batch_completed', 'Batch Completed'
    
    # Verification
    BATCH_VERIFIED = 'batch_verified', 'Batch Verified'
    BATCH_REPORTED = 'batch_reported', 'Batch Reported'
    
    # Rework
    REWORK_CREATED = 'rework_created', 'Rework Created'
    REWORK_STARTED = 'rework_started', 'Rework Started'
    REWORK_COMPLETED = 'rework_completed', 'Rework Completed'
    
    # Final Inspection
    FI_PASSED = 'fi_passed', 'FI Passed'
    FI_REWORK_ASSIGNED = 'fi_rework_assigned', 'FI Rework Assigned'
    FI_REINSPECTION = 'fi_reinspection', 'FI Re-inspection'
    
    # Hold management
    HOLD_APPLIED = 'hold_applied', 'Hold Applied'
    HOLD_CLEARED = 'hold_cleared', 'Hold Cleared'
    
    # Supervisor assignment
    SUPERVISOR_ASSIGNED = 'supervisor_assigned', 'Supervisor Assigned'
    SUPERVISOR_CHANGED = 'supervisor_changed', 'Supervisor Changed'


class ProcessActivityLog(models.Model):
    """
    Comprehensive activity log for all process-related events
    Auto-logs every action for traceability and analytics
    """
    # Relations
    batch = models.ForeignKey(
        'manufacturing.Batch',
        on_delete=models.CASCADE,
        related_name='activity_logs',
        null=True,
        blank=True
    )
    mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    process = models.ForeignKey(
        'processes.Process',
        on_delete=models.PROTECT,
        related_name='activity_logs',
        null=True,
        blank=True
    )
    process_execution = models.ForeignKey(
        'manufacturing.MOProcessExecution',
        on_delete=models.CASCADE,
        related_name='activity_logs',
        null=True,
        blank=True
    )
    
    # Activity details
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='process_activities_performed'
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    
    # Quantity tracking
    ok_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="OK quantity (kg)"
    )
    scrap_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Scrap quantity (kg)"
    )
    rework_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Rework quantity (kg)"
    )
    
    # Additional data
    reason = models.TextField(
        blank=True,
        help_text="Reason for action (stop reason, report reason, etc.)"
    )
    remarks = models.TextField(
        blank=True,
        help_text="Additional remarks or notes"
    )
    
    # Metadata - flexible JSON for additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data in JSON format"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['batch', '-performed_at']),
            models.Index(fields=['mo', '-performed_at']),
            models.Index(fields=['process', '-performed_at']),
            models.Index(fields=['activity_type', '-performed_at']),
            models.Index(fields=['performed_by', '-performed_at']),
        ]
    
    def __str__(self):
        batch_text = f"{self.batch.batch_id}" if self.batch else f"{self.mo.mo_id}"
        return f"{batch_text} - {self.get_activity_type_display()} by {self.performed_by.get_full_name()}"
    
    @classmethod
    def log_process_start(cls, process_execution, batch, user):
        """Log process start"""
        return cls.objects.create(
            batch=batch,
            mo=process_execution.mo,
            process=process_execution.process,
            process_execution=process_execution,
            activity_type='process_started',
            performed_by=user,
            metadata={
                'process_name': process_execution.process.name,
                'planned_start': str(process_execution.planned_start_time) if process_execution.planned_start_time else None
            }
        )
    
    @classmethod
    def log_process_stop(cls, process_execution, batch, user, reason, reason_detail=''):
        """Log process stop"""
        return cls.objects.create(
            batch=batch,
            mo=process_execution.mo,
            process=process_execution.process,
            process_execution=process_execution,
            activity_type='process_stopped',
            performed_by=user,
            reason=f"{reason}: {reason_detail}" if reason_detail else reason,
            metadata={
                'process_name': process_execution.process.name,
                'stop_reason': reason,
                'stop_reason_detail': reason_detail
            }
        )
    
    @classmethod
    def log_process_resume(cls, process_execution, batch, user, downtime_minutes):
        """Log process resume"""
        return cls.objects.create(
            batch=batch,
            mo=process_execution.mo,
            process=process_execution.process,
            process_execution=process_execution,
            activity_type='process_resumed',
            performed_by=user,
            metadata={
                'process_name': process_execution.process.name,
                'downtime_minutes': downtime_minutes
            }
        )
    
    @classmethod
    def log_batch_completion(cls, completion_record, user):
        """Log batch process completion with quantities"""
        return cls.objects.create(
            batch=completion_record.batch,
            mo=completion_record.process_execution.mo,
            process=completion_record.process_execution.process,
            process_execution=completion_record.process_execution,
            activity_type='batch_completed',
            performed_by=user,
            ok_quantity_kg=completion_record.ok_quantity_kg,
            scrap_quantity_kg=completion_record.scrap_quantity_kg,
            rework_quantity_kg=completion_record.rework_quantity_kg,
            remarks=completion_record.completion_notes,
            metadata={
                'process_name': completion_record.process_execution.process.name,
                'rework_cycle': completion_record.rework_cycle_number,
                'ok_percentage': completion_record.ok_percentage,
                'scrap_percentage': completion_record.scrap_percentage,
                'rework_percentage': completion_record.rework_percentage
            }
        )
    
    @classmethod
    def log_batch_verification(cls, verification, user):
        """Log batch receipt verification"""
        return cls.objects.create(
            batch=verification.batch,
            mo=verification.process_execution.mo,
            process=verification.process_execution.process,
            process_execution=verification.process_execution,
            activity_type='batch_verified' if verification.action == 'verified' else 'batch_reported',
            performed_by=user,
            reason=verification.report_reason if verification.action == 'reported' else '',
            remarks=verification.report_details if verification.action == 'reported' else '',
            metadata={
                'expected_qty_kg': float(verification.expected_quantity_kg),
                'actual_qty_kg': float(verification.actual_quantity_kg) if verification.actual_quantity_kg else None,
                'variance_kg': float(verification.quantity_variance_kg),
                'action': verification.action
            }
        )
    
    @classmethod
    def log_rework_created(cls, rework_batch, user):
        """Log rework batch creation"""
        return cls.objects.create(
            batch=rework_batch.original_batch,
            mo=rework_batch.process_execution.mo,
            process=rework_batch.process_execution.process,
            process_execution=rework_batch.process_execution,
            activity_type='rework_created',
            performed_by=user,
            rework_quantity_kg=rework_batch.rework_quantity_kg,
            reason=rework_batch.defect_description,
            metadata={
                'rework_cycle': rework_batch.rework_cycle_number,
                'source': rework_batch.source
            }
        )
    
    @classmethod
    def log_fi_rework(cls, fi_rework, user):
        """Log FI rework assignment"""
        return cls.objects.create(
            batch=fi_rework.batch,
            mo=fi_rework.mo,
            process=fi_rework.defective_process,
            activity_type='fi_rework_assigned',
            performed_by=user,
            rework_quantity_kg=fi_rework.rework_quantity_kg,
            reason=fi_rework.defect_description,
            remarks=fi_rework.fi_notes,
            metadata={
                'defective_process': fi_rework.defective_process.name,
                'assigned_to': fi_rework.assigned_to_supervisor.get_full_name(),
                'rework_cycle_count': fi_rework.rework_cycle_count
            }
        )
    
    @classmethod
    def log_hold_action(cls, batch, mo, process, user, action, reason=''):
        """Log hold applied or cleared"""
        activity_type = 'hold_applied' if action == 'applied' else 'hold_cleared'
        return cls.objects.create(
            batch=batch,
            mo=mo,
            process=process,
            activity_type=activity_type,
            performed_by=user,
            reason=reason
        )


class BatchTraceabilityEvent(models.Model):
    """
    Simplified traceability events for timeline visualization
    Auto-generated from ProcessActivityLog for easier querying
    """
    batch = models.ForeignKey(
        'manufacturing.Batch',
        on_delete=models.CASCADE,
        related_name='traceability_events'
    )
    mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='traceability_events'
    )
    
    # Event details
    event_type = models.CharField(max_length=50)
    event_description = models.TextField()
    timestamp = models.DateTimeField()
    
    # Process context
    process_name = models.CharField(max_length=100, blank=True)
    supervisor_name = models.CharField(max_length=200, blank=True)
    
    # Quantities snapshot
    ok_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    scrap_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rework_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    rework_cycle = models.PositiveIntegerField(default=0)
    is_on_hold = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['batch', 'timestamp']),
            models.Index(fields=['mo', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.batch.batch_id} - {self.event_type} @ {self.timestamp}"
    
    @classmethod
    def create_from_activity_log(cls, activity_log):
        """Create traceability event from activity log"""
        return cls.objects.create(
            batch=activity_log.batch,
            mo=activity_log.mo,
            event_type=activity_log.activity_type,
            event_description=f"{activity_log.get_activity_type_display()} by {activity_log.performed_by.get_full_name()}",
            timestamp=activity_log.performed_at,
            process_name=activity_log.process.name if activity_log.process else '',
            supervisor_name=activity_log.performed_by.get_full_name(),
            ok_kg=activity_log.ok_quantity_kg,
            scrap_kg=activity_log.scrap_quantity_kg,
            rework_kg=activity_log.rework_quantity_kg,
            metadata=activity_log.metadata
        )

