"""
Additional RM Request Models
Handles requests for additional raw materials when allocated RM is exceeded
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class AdditionalRMRequestStatusChoices(models.TextChoices):
    """Status choices for Additional RM Request"""
    PENDING = 'pending', 'Pending Approval'
    APPROVED = 'approved', 'Approved by Manager'
    REJECTED = 'rejected', 'Rejected'
    COMPLETED = 'completed', 'Completed - RM Fully Consumed'


class AdditionalRMRequest(models.Model):
    """
    Track requests for additional raw material when allocated RM is exceeded
    
    Workflow:
    1. RM Store creates request when released RM > allocated RM
    2. Request goes to both Production Head (view only) and Manager (approval)
    3. Manager approves/rejects
    4. If approved, MO.additional_rm_approved is updated
    5. RM Store can release up to new limit
    6. When last batch moves to next process + 30min delay, RM Store can mark as complete
    """
    
    # Request ID
    request_id = models.CharField(
        max_length=30, unique=True, editable=False,
        help_text="Auto-generated: ADD-RM-YYYYMMDD-XXXX"
    )
    
    # MO Reference
    mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='additional_rm_requests',
        help_text="Manufacturing Order requiring additional RM"
    )
    
    # Request Details
    original_allocated_rm_kg = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="Original RM allocated to MO (kg)"
    )
    rm_released_so_far_kg = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="RM released to production so far (kg)"
    )
    additional_rm_requested_kg = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="Additional RM being requested (kg)"
    )
    reason = models.TextField(help_text="Reason for requesting additional RM")
    
    # Batch that caused the excess
    excess_batch = models.ForeignKey(
        'manufacturing.Batch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='additional_rm_requests_caused',
        help_text="Batch that caused RM to exceed allocation"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=AdditionalRMRequestStatusChoices.choices,
        default=AdditionalRMRequestStatusChoices.PENDING
    )
    
    # Request Creator
    requested_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='additional_rm_requests_created',
        help_text="RM Store user who created the request"
    )
    requested_at = models.DateTimeField(auto_now_add=True, help_text="When the request was created")
    
    # Manager Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='additional_rm_requests_approved',
        help_text="Manager who approved the request"
    )
    approved_at = models.DateTimeField(null=True, blank=True, help_text="When the request was approved")
    approved_quantity_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        help_text="Quantity approved by manager (may differ from requested)"
    )
    approval_notes = models.TextField(blank=True, help_text="Manager's notes on approval/rejection")
    
    # Rejection
    rejected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='additional_rm_requests_rejected',
        help_text="Manager who rejected the request"
    )
    rejected_at = models.DateTimeField(null=True, blank=True, help_text="When the request was rejected")
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection")
    
    # Completion Tracking
    marked_complete_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='additional_rm_requests_completed',
        help_text="RM Store user who marked this as complete"
    )
    marked_complete_at = models.DateTimeField(null=True, blank=True, help_text="When the request was marked as complete")
    completion_notes = models.TextField(blank=True, help_text="Notes on completion")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Additional RM Request'
        verbose_name_plural = 'Additional RM Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mo', 'status']),
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['approved_at']),
        ]
    
    def __str__(self):
        return f"{self.request_id} - {self.mo.mo_id} - {self.additional_rm_requested_kg}kg"
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            
            last_request = AdditionalRMRequest.objects.filter(
                request_id__startswith=f'ADD-RM-{date_str}'
            ).order_by('-request_id').first()
            
            if last_request:
                last_num = int(last_request.request_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.request_id = f'ADD-RM-{date_str}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    def approve(self, manager_user, approved_quantity_kg, notes=''):
        """Approve the request and update MO"""
        if self.status != AdditionalRMRequestStatusChoices.PENDING:
            raise ValidationError(f"Cannot approve request in {self.status} status")
        
        self.status = AdditionalRMRequestStatusChoices.APPROVED
        self.approved_by = manager_user
        self.approved_at = timezone.now()
        self.approved_quantity_kg = Decimal(str(approved_quantity_kg))
        self.approval_notes = notes
        self.save()
        
        # Update MO with additional approved RM
        mo = self.mo
        if mo.additional_rm_approved_kg is None:
            mo.additional_rm_approved_kg = Decimal('0')
        
        mo.additional_rm_approved_kg += self.approved_quantity_kg
        mo.last_additional_rm_approval_at = timezone.now()
        mo.save()
        
        return self
    
    def reject(self, manager_user, reason):
        """Reject the request"""
        if self.status != AdditionalRMRequestStatusChoices.PENDING:
            raise ValidationError(f"Cannot reject request in {self.status} status")
        
        self.status = AdditionalRMRequestStatusChoices.REJECTED
        self.rejected_by = manager_user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        
        return self
    
    def mark_complete(self, rm_store_user, notes=''):
        """Mark request as complete (all additional RM consumed)"""
        if self.status != AdditionalRMRequestStatusChoices.APPROVED:
            raise ValidationError("Only approved requests can be marked complete")
        
        self.status = AdditionalRMRequestStatusChoices.COMPLETED
        self.marked_complete_by = rm_store_user
        self.marked_complete_at = timezone.now()
        self.completion_notes = notes
        self.save()
        
        return self
    
    @property
    def total_new_limit_kg(self):
        """Calculate total new RM limit if approved"""
        if self.status == AdditionalRMRequestStatusChoices.APPROVED:
            return self.original_allocated_rm_kg + self.approved_quantity_kg
        return self.original_allocated_rm_kg + self.additional_rm_requested_kg
    
    @property
    def can_mark_complete(self):
        """Check if request can be marked as complete"""
        if self.status != AdditionalRMRequestStatusChoices.APPROVED:
            return False
        
        if not self.excess_batch:
            return True
        
        batch = self.excess_batch
        if not batch.notes:
            return False
        
        import re
        from datetime import datetime, timedelta
        process_completions = re.findall(r'PROCESS_\d+_STATUS:completed;COMPLETED_AT:([^;]+);', batch.notes)
        
        if not process_completions:
            return False
        
        try:
            latest_completion_str = process_completions[-1]
            latest_completion = datetime.fromisoformat(latest_completion_str.replace('Z', '+00:00'))
            time_since_completion = timezone.now() - latest_completion
            return time_since_completion >= timedelta(minutes=30)
        except (ValueError, IndexError):
            return False

