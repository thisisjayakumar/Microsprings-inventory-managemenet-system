"""
Workflow Models
"""
from django.db import models
from django.contrib.auth import get_user_model

from utils.enums import (
    MOApprovalWorkflowStatusChoices,
    ProcessAssignmentStatusChoices,
    FGVerificationStatusChoices
)

User = get_user_model()


class MOApprovalWorkflow(models.Model):
    """Track MO approval workflow from creation to manager approval"""
    mo = models.OneToOneField(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='approval_workflow'
    )
    
    # Approval tracking
    status = models.CharField(max_length=30, choices=MOApprovalWorkflowStatusChoices.choices, default='pending_manager_approval')
    
    # Manager approval
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_mo_workflows')
    manager_approval_notes = models.TextField(blank=True)
    
    # RM Store allocation
    rm_store_allocated_at = models.DateTimeField(null=True, blank=True)
    rm_store_allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rm_allocated_mo_workflows')
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
    """Track process assignments by Production Head to operators"""
    mo_process_execution = models.ForeignKey(
        'manufacturing.MOProcessExecution',
        on_delete=models.CASCADE,
        related_name='process_assignments'
    )
    
    # Assignment details
    assigned_operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_processes')
    assigned_supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_process_assignments')
    
    # Assignment tracking
    status = models.CharField(max_length=20, choices=ProcessAssignmentStatusChoices.choices, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_process_assignments')
    
    # Acceptance tracking
    accepted_at = models.DateTimeField(null=True, blank=True)
    acceptance_notes = models.TextField(blank=True)
    
    # Reassignment tracking
    previous_operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_process_assignments')
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


class FinishedGoodsVerification(models.Model):
    """Track finished goods verification and quality check"""
    batch = models.OneToOneField(
        'manufacturing.Batch',
        on_delete=models.CASCADE,
        related_name='fg_verification'
    )
    
    # Verification details
    status = models.CharField(max_length=30, choices=FGVerificationStatusChoices.choices, default='pending_verification')
    
    # Quality check
    quality_checked_at = models.DateTimeField(null=True, blank=True)
    quality_checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='quality_checked_batches')
    quality_notes = models.TextField(blank=True)
    
    # Final verification
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_fg_batches')
    verification_notes = models.TextField(blank=True)
    
    # Dispatch tracking
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatched_batches')
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Finished Goods Verification'
        verbose_name_plural = 'Finished Goods Verifications'
    
    def __str__(self):
        return f"{self.batch.batch_id} - {self.get_status_display()}"
