from django.db import models
from django.core.validators import MinValueValidator
from authentication.models import CustomUser
from utils.enums import PatrolDutyStatusChoices, PatrolUploadStatusChoices, ShiftChoices
from django.utils import timezone
from datetime import timedelta


class PatrolDuty(models.Model):
    """
    Patrol duty assignments created by Production Head
    """
    patrol_user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='patrol_duties',
        help_text='Patrol user assigned to this duty'
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_patrol_duties',
        help_text='Production Head who created this duty'
    )
    
    # Process monitoring
    process_names = models.JSONField(
        default=list,
        help_text='List of process names to be monitored'
    )
    
    # Frequency and timing
    frequency_hours = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text='Hours between QC uploads (e.g., 1, 2, or 3 hours)'
    )
    shift_start_time = models.TimeField(help_text='Shift start time')
    shift_end_time = models.TimeField(help_text='Shift end time')
    shift_type = models.CharField(
        max_length=10,
        choices=ShiftChoices.choices,
        null=True,
        blank=True,
        help_text='Shift type (I, II, III)'
    )
    
    # Date range
    start_date = models.DateField(help_text='Duty start date')
    end_date = models.DateField(help_text='Duty end date')
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=PatrolDutyStatusChoices.choices,
        default='active'
    )
    remarks = models.TextField(blank=True, null=True, help_text='Optional notes')
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Patrol Duty'
        verbose_name_plural = 'Patrol Duties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patrol_user', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"Patrol Duty - {self.patrol_user.full_name} ({self.start_date} to {self.end_date})"
    
    @property
    def is_active(self):
        """Check if duty is currently active"""
        today = timezone.now().date()
        return (
            self.status == 'active' and 
            self.start_date <= today <= self.end_date
        )
    
    @property
    def is_ending_soon(self):
        """Check if duty is ending within 8 hours (for alerts)"""
        if self.status != 'active':
            return False
        
        now = timezone.now()
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(self.end_date, self.shift_end_time)
        )
        time_remaining = end_datetime - now
        return timedelta(0) < time_remaining <= timedelta(hours=8)
    
    def get_expected_upload_slots(self, date=None):
        """
        Generate expected upload time slots for a given date
        """
        if date is None:
            date = timezone.now().date()
        
        from datetime import datetime, time
        slots = []
        
        # Start from shift start time
        current_time = timezone.datetime.combine(date, self.shift_start_time)
        end_time = timezone.datetime.combine(date, self.shift_end_time)
        
        # Handle overnight shifts
        if self.shift_end_time < self.shift_start_time:
            end_time += timedelta(days=1)
        
        # Generate slots based on frequency
        while current_time <= end_time:
            slots.append(current_time.time())
            current_time += timedelta(hours=self.frequency_hours)
        
        return slots
    
    def auto_complete_if_ended(self):
        """
        Auto-complete duty if end date/time has passed
        """
        now = timezone.now()
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(self.end_date, self.shift_end_time)
        )
        
        if now > end_datetime and self.status == 'active':
            self.status = 'completed'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False


class PatrolUpload(models.Model):
    """
    QC image uploads by patrol users for specific time slots
    """
    duty = models.ForeignKey(
        PatrolDuty,
        on_delete=models.CASCADE,
        related_name='uploads'
    )
    process_name = models.CharField(max_length=100, help_text='Process being checked')
    
    # Time slot information
    scheduled_date = models.DateField(help_text='Date for this QC check')
    scheduled_time = models.TimeField(help_text='Scheduled time slot')
    
    # Upload details
    qc_image = models.ImageField(
        upload_to='patrol_qc_images/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='QC sheet image'
    )
    upload_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual upload time'
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=PatrolUploadStatusChoices.choices,
        default='pending'
    )
    patrol_remarks = models.TextField(
        blank=True,
        null=True,
        help_text='Patrol user remarks (e.g., "All readings normal")'
    )
    
    # Reupload tracking
    is_reuploaded = models.BooleanField(default=False)
    first_upload_time = models.DateTimeField(null=True, blank=True)
    reupload_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='10 minutes after first upload'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Patrol Upload'
        verbose_name_plural = 'Patrol Uploads'
        ordering = ['-scheduled_date', '-scheduled_time']
        unique_together = ['duty', 'process_name', 'scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['duty', 'status']),
            models.Index(fields=['scheduled_date', 'scheduled_time']),
        ]
    
    def __str__(self):
        return f"{self.process_name} - {self.scheduled_date} {self.scheduled_time} ({self.status})"
    
    @property
    def is_upload_window_open(self):
        """
        Check if current time is within the allowed upload window
        Window: 15 minutes before to 30 minutes after scheduled time
        """
        now = timezone.now()
        scheduled_datetime = timezone.make_aware(
            timezone.datetime.combine(self.scheduled_date, self.scheduled_time)
        )
        
        window_start = scheduled_datetime - timedelta(minutes=15)
        window_end = scheduled_datetime + timedelta(minutes=30)
        
        return window_start <= now <= window_end
    
    @property
    def can_reupload(self):
        """
        Check if user can still reupload (within 10 minutes of first upload)
        """
        if not self.first_upload_time or not self.reupload_deadline:
            return False
        
        now = timezone.now()
        return now <= self.reupload_deadline and self.status == 'submitted'
    
    @property
    def is_locked(self):
        """
        Check if upload is locked (cannot be modified)
        """
        if self.status in ['missed']:
            return True
        
        if self.status == 'submitted' and not self.can_reupload:
            return True
        
        return False
    
    def mark_as_missed(self):
        """
        Mark upload as missed if not submitted within window
        """
        if self.status == 'pending' and not self.is_upload_window_open:
            self.status = 'missed'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def submit_upload(self, image, remarks=''):
        """
        Submit QC image upload
        """
        now = timezone.now()
        
        # First time upload
        if not self.first_upload_time:
            self.qc_image = image
            self.patrol_remarks = remarks
            self.upload_timestamp = now
            self.first_upload_time = now
            self.reupload_deadline = now + timedelta(minutes=10)
            self.status = 'submitted'
            self.save()
            return True
        
        # Reupload within 10-minute window
        elif self.can_reupload:
            self.qc_image = image
            self.patrol_remarks = remarks
            self.upload_timestamp = now
            self.is_reuploaded = True
            self.status = 'reuploaded'
            self.save()
            return True
        
        return False


class PatrolAlert(models.Model):
    """
    Alerts for patrol management (duty ending soon, missed uploads, etc.)
    """
    duty = models.ForeignKey(
        PatrolDuty,
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True
    )
    upload = models.ForeignKey(
        PatrolUpload,
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True
    )
    
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('duty_assigned', 'Duty Assigned'),
            ('duty_ending_4hr', 'Duty Ending in 4 Hours'),
            ('duty_ending_8hr', 'Duty Ending in 8 Hours'),
            ('upload_missed', 'Upload Missed'),
            ('duty_completed', 'Duty Completed'),
        ]
    )
    
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='patrol_alerts',
        help_text='User who should receive this alert'
    )
    
    message = models.TextField(help_text='Alert message')
    is_read = models.BooleanField(default=False)
    is_action_taken = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Patrol Alert'
        verbose_name_plural = 'Patrol Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.recipient.full_name}"

