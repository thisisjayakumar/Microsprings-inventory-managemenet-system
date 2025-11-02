"""
Allocation Models
Raw Material Allocations, Batch Allocations, and Process Execution Logs
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from utils.enums import (
    RMAllocationStatusChoices,
    BatchAllocationStatusChoices,
    ProcessExecutionActionChoices
)

User = get_user_model()


class RawMaterialAllocation(models.Model):
    """
    Track raw material allocations/reservations for Manufacturing Orders
    Supports priority-based swapping before MO approval
    """
    # MO and RM references
    mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.CASCADE,
        related_name='rm_allocations',
        help_text="Manufacturing Order this allocation is for"
    )
    raw_material = models.ForeignKey(
        'inventory.RawMaterial',
        on_delete=models.PROTECT,
        related_name='mo_allocations',
        help_text="Raw material being allocated"
    )
    
    # Allocation details
    allocated_quantity_kg = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="Quantity of raw material allocated in KG"
    )
    
    # Status tracking
    status = models.CharField(max_length=20, choices=RMAllocationStatusChoices.choices, default='reserved')
    
    # Swapping tracking
    can_be_swapped = models.BooleanField(default=True, help_text="Can this allocation be swapped to higher priority MO?")
    swapped_to_mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rm_allocations_received',
        help_text="MO to which this allocation was swapped"
    )
    swapped_at = models.DateTimeField(null=True, blank=True)
    swapped_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rm_swaps_performed')
    swap_reason = models.TextField(blank=True)
    
    # Locking (on MO approval)
    locked_at = models.DateTimeField(null=True, blank=True, help_text="When this allocation was locked (MO approved)")
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rm_allocations_locked')
    
    # Allocation timestamps
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rm_allocations_created')
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Raw Material Allocation'
        verbose_name_plural = 'Raw Material Allocations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mo', 'status']),
            models.Index(fields=['raw_material', 'status']),
            models.Index(fields=['can_be_swapped']),
        ]
    
    def __str__(self):
        return f"{self.mo.mo_id} - {self.raw_material.material_code} ({self.allocated_quantity_kg}kg) - {self.status}"
    
    def lock_allocation(self, locked_by_user):
        """Lock this allocation (called when MO is approved)"""
        if self.status == 'locked':
            return False
        
        self.status = 'locked'
        self.can_be_swapped = False
        self.locked_at = timezone.now()
        self.locked_by = locked_by_user
        self.save()
        
        # Deduct from available stock
        from inventory.models import RMStockBalanceHeat
        stock_balance = RMStockBalanceHeat.objects.filter(raw_material=self.raw_material).first()
        
        if stock_balance:
            stock_balance.total_available_quantity_kg -= self.allocated_quantity_kg
            stock_balance.save()
        
        return True
    
    def swap_to_mo(self, target_mo, swapped_by_user, reason=""):
        """Swap this allocation to a higher priority MO"""
        if not self.can_be_swapped or self.status == 'locked':
            return False, "Allocation is locked and cannot be swapped"
        
        # Check priority
        priority_order = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}
        source_priority = priority_order.get(self.mo.priority, 0)
        target_priority = priority_order.get(target_mo.priority, 0)
        
        if target_priority <= source_priority:
            return False, f"Target MO priority ({target_mo.priority}) must be higher than source MO priority ({self.mo.priority})"
        
        # Perform swap
        old_mo = self.mo
        self.status = 'swapped'
        self.swapped_to_mo = target_mo
        self.swapped_at = timezone.now()
        self.swapped_by = swapped_by_user
        self.swap_reason = reason
        self.can_be_swapped = False
        self.save()
        
        # Create new allocation for target MO
        new_allocation = RawMaterialAllocation.objects.create(
            mo=target_mo,
            raw_material=self.raw_material,
            allocated_quantity_kg=self.allocated_quantity_kg,
            status='reserved',
            can_be_swapped=True,
            allocated_by=swapped_by_user,
            notes=f"Swapped from {old_mo.mo_id} due to higher priority"
        )
        
        return True, f"Allocation swapped from {old_mo.mo_id} to {target_mo.mo_id}"
    
    def release_allocation(self):
        """Release this allocation back to stock (e.g., when MO is cancelled)"""
        if self.status == 'locked':
            # Add back to available stock
            from inventory.models import RMStockBalanceHeat
            stock_balance = RMStockBalanceHeat.objects.filter(raw_material=self.raw_material).first()
            
            if stock_balance:
                stock_balance.total_available_quantity_kg += self.allocated_quantity_kg
                stock_balance.save()
        
        self.status = 'released'
        self.can_be_swapped = False
        self.save()
        
        return True


class RMAllocationHistory(models.Model):
    """Track history of RM allocation changes (swaps, locks, releases)"""
    allocation = models.ForeignKey(RawMaterialAllocation, on_delete=models.CASCADE, related_name='history')
    
    action = models.CharField(max_length=50, help_text="Action performed (reserved, swapped, locked, released)")
    from_mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rm_allocation_history_from'
    )
    to_mo = models.ForeignKey(
        'manufacturing.ManufacturingOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rm_allocation_history_to'
    )
    
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=3)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'RM Allocation History'
        verbose_name_plural = 'RM Allocation Histories'
        ordering = ['-performed_at']
    
    def __str__(self):
        return f"{self.action} - {self.allocation.mo.mo_id} ({self.performed_at})"


class BatchAllocation(models.Model):
    """Track batch allocation from RM Store to specific processes"""
    batch = models.ForeignKey('manufacturing.Batch', on_delete=models.CASCADE, related_name='allocations')
    
    # Allocation details
    allocated_to_process = models.ForeignKey('processes.Process', on_delete=models.CASCADE, related_name='batch_allocations')
    allocated_to_operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='allocated_batches')
    
    # Heat number allocation (for raw materials)
    heat_numbers = models.ManyToManyField(
        'inventory.HeatNumber',
        related_name='batch_allocations',
        blank=True,
        help_text="Heat numbers allocated to this batch"
    )
    
    # Allocation tracking
    status = models.CharField(max_length=20, choices=BatchAllocationStatusChoices.choices, default='allocated')
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_batch_allocations')
    
    # Transfer tracking
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_batch_allocations')
    
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
    """Detailed log of process execution by operators"""
    batch_allocation = models.ForeignKey(BatchAllocation, on_delete=models.CASCADE, related_name='execution_logs')
    
    # Execution details
    action = models.CharField(max_length=20, choices=ProcessExecutionActionChoices.choices)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='process_execution_logs')
    
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

