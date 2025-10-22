# Enhanced Manufacturing Workflow Models
# Add these models to manufacturing/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class MOApprovalWorkflow(models.Model):
    """
    Track MO approval workflow from creation to manager approval
    """
    STATUS_CHOICES = [
        ('pending_manager_approval', 'Pending Manager Approval'),
        ('manager_approved', 'Manager Approved'),
        ('manager_rejected', 'Manager Rejected'),
        ('rm_allocation_pending', 'RM Allocation Pending'),
        ('rm_allocated', 'RM Allocated'),
        ('ready_for_production', 'Ready for Production'),
    ]
    
    mo = models.OneToOneField(
        ManufacturingOrder, 
        on_delete=models.CASCADE, 
        related_name='approval_workflow'
    )
    
    # Approval tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_manager_approval')
    
    # Manager approval
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_mo_workflows'
    )
    manager_approval_notes = models.TextField(blank=True)
    
    # RM Store allocation
    rm_store_allocated_at = models.DateTimeField(null=True, blank=True)
    rm_store_allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rm_allocated_mo_workflows'
    )
    rm_allocation_notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'MO Approval Workflow'
        verbose_name_plural = 'MO Approval Workflows'
    
    def __str__(self):
        return f"{self.mo.mo_id} - {self.get_status_display()}"


class ProcessAssignment(models.Model):
    """
    Track process assignments by Production Head to operators
    """
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted by Operator'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('reassigned', 'Reassigned'),
        ('cancelled', 'Cancelled'),
    ]
    
    mo_process_execution = models.ForeignKey(
        'MOProcessExecution',
        on_delete=models.CASCADE,
        related_name='process_assignments'
    )
    
    # Assignment details
    assigned_operator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='assigned_processes'
    )
    assigned_supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_process_assignments'
    )
    
    # Assignment tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_process_assignments'
    )
    
    # Acceptance tracking
    accepted_at = models.DateTimeField(null=True, blank=True)
    acceptance_notes = models.TextField(blank=True)
    
    # Reassignment tracking
    previous_operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='previous_process_assignments'
    )
    reassigned_at = models.DateTimeField(null=True, blank=True)
    reassignment_reason = models.TextField(blank=True)
    
    # Completion tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Process Assignment'
        verbose_name_plural = 'Process Assignments'
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.mo_process_execution.mo.mo_id} - {self.mo_process_execution.process.name} -> {self.assigned_operator.email}"


class BatchAllocation(models.Model):
    """
    Track batch allocation from RM Store to specific processes
    """
    STATUS_CHOICES = [
        ('allocated', 'Allocated'),
        ('in_transit', 'In Transit'),
        ('received', 'Received by Process'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
        ('returned', 'Returned to RM Store'),
    ]
    
    batch = models.ForeignKey(
        'Batch',
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    
    # Allocation details
    allocated_to_process = models.ForeignKey(
        'processes.Process',
        on_delete=models.CASCADE,
        related_name='batch_allocations'
    )
    allocated_to_operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='allocated_batches'
    )
    
    # Heat number allocation (for raw materials)
    heat_numbers = models.ManyToManyField(
        'inventory.HeatNumber',
        related_name='batch_allocations',
        blank=True,
        help_text="Heat numbers allocated to this batch"
    )
    
    # Allocation tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='allocated')
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_batch_allocations'
    )
    
    # Transfer tracking
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_batch_allocations'
    )
    
    # Location tracking
    current_location = models.CharField(max_length=100, blank=True)
    location_notes = models.TextField(blank=True)
    
    # Audit
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Batch Allocation'
        verbose_name_plural = 'Batch Allocations'
        ordering = ['-allocated_at']
    
    def __str__(self):
        return f"{self.batch.batch_id} -> {self.allocated_to_process.name}"


class ProcessExecutionLog(models.Model):
    """
    Detailed log of process execution by operators
    """
    ACTION_CHOICES = [
        ('started', 'Process Started'),
        ('paused', 'Process Paused'),
        ('resumed', 'Process Resumed'),
        ('completed', 'Process Completed'),
        ('quality_check', 'Quality Check'),
        ('issue_reported', 'Issue Reported'),
        ('material_requested', 'Material Requested'),
        ('tool_change', 'Tool Change'),
        ('maintenance', 'Maintenance'),
    ]
    
    batch_allocation = models.ForeignKey(
        BatchAllocation,
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    
    # Execution details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='process_execution_logs'
    )
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Details
    notes = models.TextField(blank=True)
    quantity_processed = models.PositiveIntegerField(null=True, blank=True)
    quality_status = models.CharField(max_length=20, blank=True)
    
    # Location
    location = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Process Execution Log'
        verbose_name_plural = 'Process Execution Logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.batch_allocation.batch.batch_id} - {self.get_action_display()} by {self.performed_by.email}"


class FinishedGoodsVerification(models.Model):
    """
    Track finished goods verification and quality check
    """
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('quality_check_passed', 'Quality Check Passed'),
        ('quality_check_failed', 'Quality Check Failed'),
        ('approved_for_dispatch', 'Approved for Dispatch'),
        ('dispatched', 'Dispatched'),
    ]
    
    batch = models.OneToOneField(
        'Batch',
        on_delete=models.CASCADE,
        related_name='fg_verification'
    )
    
    # Verification details
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_verification')
    
    # Quality check
    quality_checked_at = models.DateTimeField(null=True, blank=True)
    quality_checked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quality_checked_batches'
    )
    quality_notes = models.TextField(blank=True)
    
    # Final verification
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_fg_batches'
    )
    verification_notes = models.TextField(blank=True)
    
    # Dispatch tracking
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_batches'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Finished Goods Verification'
        verbose_name_plural = 'Finished Goods Verifications'
    
    def __str__(self):
        return f"{self.batch.batch_id} - {self.get_status_display()}"
