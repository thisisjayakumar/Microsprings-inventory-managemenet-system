"""
Raw Material Allocation Service
Handles RM reservation, swapping, and locking for Manufacturing Orders
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from manufacturing.models import (
    ManufacturingOrder, RawMaterialAllocation, RMAllocationHistory
)
from inventory.models import RawMaterial, RMStockBalanceHeat


class RMAllocationService:
    """
    Service for managing raw material allocations for Manufacturing Orders
    """
    
    @staticmethod
    def allocate_rm_for_mo(mo, allocated_by_user):
        with transaction.atomic():
            allocations = []
            
            # Get product's raw material requirements
            if not mo.product_code or not mo.product_code.material:
                raise ValidationError("Product must have associated raw material")
            
            raw_material = mo.product_code.material
            
            # Calculate required quantity
            required_quantity_kg = Decimal(str(mo.rm_required_kg))
            
            if required_quantity_kg <= 0:
                raise ValidationError("Required RM quantity must be greater than 0")
            
            # Check if stock is available
            stock_balance = RMStockBalanceHeat.objects.filter(
                raw_material=raw_material
            ).first()
            
            if not stock_balance or stock_balance.total_available_quantity_kg < required_quantity_kg:
                raise ValidationError(
                    f"Insufficient stock for {raw_material.material_code}. "
                    f"Required: {required_quantity_kg}kg, "
                    f"Available: {stock_balance.total_available_quantity_kg if stock_balance else 0}kg"
                )
            
            # Create allocation (reserved status - not locked yet)
            allocation = RawMaterialAllocation.objects.create(
                mo=mo,
                raw_material=raw_material,
                allocated_quantity_kg=required_quantity_kg,
                status='reserved',
                can_be_swapped=True,
                allocated_by=allocated_by_user,
                notes=f"Initial allocation for MO {mo.mo_id}"
            )
            
            # Create history record
            RMAllocationHistory.objects.create(
                allocation=allocation,
                action='reserved',
                from_mo=None,
                to_mo=mo,
                quantity_kg=required_quantity_kg,
                performed_by=allocated_by_user,
                reason="Initial RM allocation for MO creation"
            )
            
            allocations.append(allocation)
            
            return allocations
    
    @staticmethod
    def find_swappable_allocations(target_mo):
        """
        Find RM allocations that can be swapped to the target MO
        Based on:
        1. Same raw material required
        2. Lower priority than target MO
        3. Not locked (MO not yet approved)
        
        Args:
            target_mo: ManufacturingOrder that needs RM
            
        Returns:
            QuerySet of RawMaterialAllocation instances that can be swapped
        """
        if not target_mo.product_code or not target_mo.product_code.material:
            return RawMaterialAllocation.objects.none()
        
        required_material = target_mo.product_code.material
        required_quantity = Decimal(str(target_mo.rm_required_kg))
        
        # Priority ordering
        priority_order = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}
        target_priority_value = priority_order.get(target_mo.priority, 0)
        
        # Find all allocations with lower priority, same material, and can be swapped
        lower_priority_statuses = [
            key for key, value in priority_order.items() 
            if value < target_priority_value
        ]
        
        swappable_allocations = RawMaterialAllocation.objects.filter(
            raw_material=required_material,
            status='reserved',
            can_be_swapped=True,
            mo__status='on_hold',  # MO not yet approved
            mo__priority__in=lower_priority_statuses
        ).select_related('mo', 'raw_material').order_by(
            'mo__priority',  # Lowest priority first
            'allocated_at'  # Oldest first
        )
        
        return swappable_allocations
    
    @staticmethod
    def auto_swap_allocations(target_mo, requested_by_user):
        """
        Automatically swap RM allocations from lower priority MOs to target MO
        
        Args:
            target_mo: ManufacturingOrder that needs RM (higher priority)
            requested_by_user: User requesting the swap
            
        Returns:
            dict with swap results
        """
        with transaction.atomic():
            swappable = RMAllocationService.find_swappable_allocations(target_mo)
            
            if not swappable.exists():
                return {
                    'success': False,
                    'message': 'No swappable allocations found',
                    'swapped_count': 0
                }
            
            required_quantity = Decimal(str(target_mo.rm_required_kg))
            swapped_allocations = []
            total_swapped_quantity = Decimal('0')
            
            # Swap allocations until we have enough
            for allocation in swappable:
                if total_swapped_quantity >= required_quantity:
                    break
                
                success, message = allocation.swap_to_mo(
                    target_mo=target_mo,
                    swapped_by_user=requested_by_user,
                    reason=f"Auto-swapped due to higher priority MO {target_mo.mo_id}"
                )
                
                if success:
                    swapped_allocations.append(allocation)
                    total_swapped_quantity += allocation.allocated_quantity_kg
                    
                    # Create history record
                    RMAllocationHistory.objects.create(
                        allocation=allocation,
                        action='swapped',
                        from_mo=allocation.mo,
                        to_mo=target_mo,
                        quantity_kg=allocation.allocated_quantity_kg,
                        performed_by=requested_by_user,
                        reason=f"Auto-swapped to higher priority MO {target_mo.mo_id}"
                    )
            
            if total_swapped_quantity >= required_quantity:
                return {
                    'success': True,
                    'message': f'Successfully swapped {len(swapped_allocations)} allocations',
                    'swapped_count': len(swapped_allocations),
                    'total_quantity_kg': float(total_swapped_quantity),
                    'swapped_from_mos': [alloc.mo.mo_id for alloc in swapped_allocations]
                }
            else:
                return {
                    'success': False,
                    'message': f'Insufficient swappable quantity. Required: {required_quantity}kg, Available: {total_swapped_quantity}kg',
                    'swapped_count': len(swapped_allocations),
                    'total_quantity_kg': float(total_swapped_quantity),
                    'required_quantity_kg': float(required_quantity)
                }
    
    @staticmethod
    def lock_allocations_for_mo(mo, locked_by_user):
        """
        Lock all RM allocations for an MO (when MO is approved)
        This deducts the RM from available stock
        
        Args:
            mo: ManufacturingOrder being approved
            locked_by_user: User approving the MO
            
        Returns:
            dict with lock results
        """
        with transaction.atomic():
            allocations = RawMaterialAllocation.objects.filter(
                mo=mo,
                status='reserved'
            ).select_related('raw_material')
            
            if not allocations.exists():
                return {
                    'success': False,
                    'message': 'No reserved allocations found for this MO',
                    'locked_count': 0
                }
            
            locked_count = 0
            for allocation in allocations:
                success = allocation.lock_allocation(locked_by_user)
                if success:
                    locked_count += 1
                    
                    # Create history record
                    RMAllocationHistory.objects.create(
                        allocation=allocation,
                        action='locked',
                        from_mo=None,
                        to_mo=mo,
                        quantity_kg=allocation.allocated_quantity_kg,
                        performed_by=locked_by_user,
                        reason=f"MO {mo.mo_id} approved - allocation locked"
                    )
            
            return {
                'success': True,
                'message': f'Locked {locked_count} allocations for MO {mo.mo_id}',
                'locked_count': locked_count
            }
    
    @staticmethod
    def release_allocations_for_mo(mo, released_by_user, reason=""):
        """
        Release RM allocations back to stock (when MO is cancelled)
        
        Args:
            mo: ManufacturingOrder being cancelled
            released_by_user: User cancelling the MO
            reason: Reason for release
            
        Returns:
            dict with release results
        """
        with transaction.atomic():
            allocations = RawMaterialAllocation.objects.filter(
                mo=mo,
                status__in=['reserved', 'locked']
            ).select_related('raw_material')
            
            if not allocations.exists():
                return {
                    'success': False,
                    'message': 'No allocations found for this MO',
                    'released_count': 0
                }
            
            released_count = 0
            for allocation in allocations:
                success = allocation.release_allocation()
                if success:
                    released_count += 1
                    
                    # Create history record
                    RMAllocationHistory.objects.create(
                        allocation=allocation,
                        action='released',
                        from_mo=mo,
                        to_mo=None,
                        quantity_kg=allocation.allocated_quantity_kg,
                        performed_by=released_by_user,
                        reason=reason or f"MO {mo.mo_id} cancelled - allocation released"
                    )
            
            return {
                'success': True,
                'message': f'Released {released_count} allocations for MO {mo.mo_id}',
                'released_count': released_count
            }
    
    @staticmethod
    def get_allocation_summary_for_mo(mo):
        """
        Get summary of RM allocations for an MO
        
        Args:
            mo: ManufacturingOrder instance
            
        Returns:
            dict with allocation summary
        """
        allocations = RawMaterialAllocation.objects.filter(
            mo=mo
        ).select_related('raw_material', 'swapped_to_mo')
        
        summary = {
            'mo_id': mo.mo_id,
            'mo_priority': mo.priority,
            'mo_status': mo.status,
            'required_rm_kg': float(mo.rm_required_kg),
            'allocations': []
        }
        
        total_reserved = Decimal('0')
        total_locked = Decimal('0')
        total_swapped = Decimal('0')
        
        for allocation in allocations:
            alloc_data = {
                'id': allocation.id,
                'raw_material': allocation.raw_material.material_code,
                'quantity_kg': float(allocation.allocated_quantity_kg),
                'status': allocation.status,
                'can_be_swapped': allocation.can_be_swapped,
                'allocated_at': allocation.allocated_at.isoformat(),
            }
            
            if allocation.status == 'reserved':
                total_reserved += allocation.allocated_quantity_kg
            elif allocation.status == 'locked':
                total_locked += allocation.allocated_quantity_kg
            elif allocation.status == 'swapped':
                total_swapped += allocation.allocated_quantity_kg
                alloc_data['swapped_to_mo'] = allocation.swapped_to_mo.mo_id if allocation.swapped_to_mo else None
            
            summary['allocations'].append(alloc_data)
        
        summary['total_reserved_kg'] = float(total_reserved)
        summary['total_locked_kg'] = float(total_locked)
        summary['total_swapped_kg'] = float(total_swapped)
        summary['is_fully_allocated'] = (total_reserved + total_locked) >= Decimal(str(mo.rm_required_kg))
        
        return summary
    
    @staticmethod
    def check_rm_availability_for_mo(mo):
        """
        Check if RM is available for an MO
        Considers:
        1. Currently allocated RM (reserved/locked)
        2. Potential swappable RM from lower priority MOs
        
        Args:
            mo: ManufacturingOrder instance
            
        Returns:
            dict with availability status
        """
        if not mo.product_code or not mo.product_code.material:
            return {
                'available': False,
                'message': 'Product has no associated raw material'
            }
        
        raw_material = mo.product_code.material
        required_quantity = Decimal(str(mo.rm_required_kg))
        
        # Check current allocations
        current_allocations = RawMaterialAllocation.objects.filter(
            mo=mo,
            status__in=['reserved', 'locked']
        ).aggregate(
            total=models.Sum('allocated_quantity_kg')
        )
        
        current_allocated = Decimal(str(current_allocations['total'] or 0))
        
        # Check stock balance
        stock_balance = RMStockBalanceHeat.objects.filter(
            raw_material=raw_material
        ).first()
        
        available_in_stock = Decimal(str(stock_balance.total_available_quantity_kg if stock_balance else 0))
        
        # Check swappable allocations
        swappable_allocations = RMAllocationService.find_swappable_allocations(mo)
        swappable_quantity = sum(
            alloc.allocated_quantity_kg for alloc in swappable_allocations
        )
        
        total_available = current_allocated + available_in_stock + swappable_quantity
        
        return {
            'available': total_available >= required_quantity,
            'required_kg': float(required_quantity),
            'current_allocated_kg': float(current_allocated),
            'available_in_stock_kg': float(available_in_stock),
            'swappable_kg': float(swappable_quantity),
            'total_available_kg': float(total_available),
            'shortage_kg': float(max(0, required_quantity - total_available)),
            'can_swap': swappable_quantity > 0,
            'swappable_from_mos': [alloc.mo.mo_id for alloc in swappable_allocations[:5]]  # Show first 5
        }


# Import at the end to avoid circular imports
from django.db import models

