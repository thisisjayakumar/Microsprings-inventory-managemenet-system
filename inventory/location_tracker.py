"""
Inventory Location Tracking System

This module provides utilities for tracking product, raw material, and batch movements
between locations with automatic inventory transaction creation.
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import ProductLocation, InventoryTransaction, Location
from .utils import generate_transaction_id

User = get_user_model()


class LocationTracker:
    """
    Central class for handling location movements and inventory transactions
    """
    
    @staticmethod
    def move_item(item_type, item_id, to_location_code, user, quantity=None, 
                  reference_type=None, reference_id=None, notes=""):
        """
        Move an item (product, raw_material, or batch) to a new location
        
        Args:
            item_type: 'product', 'raw_material', or 'batch'
            item_id: ID of the item to move
            to_location_code: Code of the destination location
            user: User performing the move
            quantity: Quantity to move (if None, moves all)
            reference_type: Type of reference (mo, po, process, etc.)
            reference_id: ID of the reference
            notes: Additional notes for the transaction
            
        Returns:
            dict: Result with success status and transaction details
        """
        try:
            with transaction.atomic():
                # Get destination location
                to_location = Location.objects.get(code=to_location_code)
                
                # Get current location record
                current_location_record = LocationTracker._get_current_location_record(
                    item_type, item_id
                )
                
                if not current_location_record:
                    return {
                        'success': False,
                        'error': f'{item_type} with ID {item_id} not found in any location'
                    }
                
                from_location = current_location_record.current_location
                available_quantity = current_location_record.quantity
                
                # Determine move quantity
                move_quantity = quantity if quantity is not None else available_quantity
                
                if move_quantity > available_quantity:
                    return {
                        'success': False,
                        'error': f'Insufficient quantity. Available: {available_quantity}, Requested: {move_quantity}'
                    }
                
                # Create inventory transaction
                transaction_id = generate_transaction_id('MOVE')
                inv_transaction = InventoryTransaction.objects.create(
                    transaction_id=transaction_id,
                    transaction_type='transfer',
                    product=current_location_record.product,
                    manufacturing_order=LocationTracker._get_mo_from_reference(reference_type, reference_id),
                    location_from=from_location,
                    location_to=to_location,
                    quantity=move_quantity,
                    transaction_datetime=timezone.now(),
                    created_by=user,
                    reference_type=reference_type,
                    reference_id=str(reference_id) if reference_id else None,
                    notes=notes
                )
                
                # Update current location record
                if move_quantity == available_quantity:
                    # Moving all quantity - update location
                    current_location_record.current_location = to_location
                    current_location_record.last_moved_by = user
                    current_location_record.last_transaction = inv_transaction
                    current_location_record.save()
                else:
                    # Partial move - reduce current quantity and create new location record
                    current_location_record.quantity -= move_quantity
                    current_location_record.save()
                    
                    # Check if destination location already has this item
                    existing_dest_record = LocationTracker._get_location_record(
                        item_type, item_id, to_location_code
                    )
                    
                    if existing_dest_record:
                        # Add to existing quantity
                        existing_dest_record.quantity += move_quantity
                        existing_dest_record.last_moved_by = user
                        existing_dest_record.last_transaction = inv_transaction
                        existing_dest_record.save()
                    else:
                        # Create new location record
                        LocationTracker._create_location_record(
                            item_type, item_id, to_location, move_quantity, user, inv_transaction
                        )
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'moved_quantity': move_quantity,
                    'from_location': from_location.location_name,
                    'to_location': to_location.location_name
                }
                
        except Location.DoesNotExist:
            return {
                'success': False,
                'error': f'Location with code {to_location_code} not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error moving item: {str(e)}'
            }
    
    @staticmethod
    def create_item_at_location(item_type, item_id, location_code, quantity, user,
                               reference_type=None, reference_id=None, notes=""):
        """
        Create/produce an item at a specific location (e.g., batch creation)
        
        Args:
            item_type: 'product', 'raw_material', or 'batch'
            item_id: ID of the item
            location_code: Code of the location where item is created
            quantity: Quantity created
            user: User performing the action
            reference_type: Type of reference
            reference_id: ID of the reference
            notes: Additional notes
            
        Returns:
            dict: Result with success status and transaction details
        """
        try:
            with transaction.atomic():
                location = Location.objects.get(code=location_code)
                
                # Create inventory transaction
                transaction_id = generate_transaction_id('PROD')
                inv_transaction = InventoryTransaction.objects.create(
                    transaction_id=transaction_id,
                    transaction_type='production',
                    product=LocationTracker._get_product_from_item(item_type, item_id),
                    manufacturing_order=LocationTracker._get_mo_from_reference(reference_type, reference_id),
                    location_from=None,
                    location_to=location,
                    quantity=quantity,
                    transaction_datetime=timezone.now(),
                    created_by=user,
                    reference_type=reference_type,
                    reference_id=str(reference_id) if reference_id else None,
                    notes=notes
                )
                
                # Check if item already exists at this location
                existing_record = LocationTracker._get_location_record(
                    item_type, item_id, location_code
                )
                
                if existing_record:
                    # Add to existing quantity
                    existing_record.quantity += quantity
                    existing_record.last_moved_by = user
                    existing_record.last_transaction = inv_transaction
                    existing_record.save()
                else:
                    # Create new location record
                    LocationTracker._create_location_record(
                        item_type, item_id, location, quantity, user, inv_transaction
                    )
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'created_quantity': quantity,
                    'location': location.location_name
                }
                
        except Location.DoesNotExist:
            return {
                'success': False,
                'error': f'Location with code {location_code} not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating item: {str(e)}'
            }
    
    @staticmethod
    def consume_item(item_type, item_id, quantity, user, reference_type=None, 
                    reference_id=None, notes=""):
        """
        Consume/use an item from its current location
        
        Args:
            item_type: 'product', 'raw_material', or 'batch'
            item_id: ID of the item
            quantity: Quantity to consume
            user: User performing the action
            reference_type: Type of reference
            reference_id: ID of the reference
            notes: Additional notes
            
        Returns:
            dict: Result with success status and transaction details
        """
        try:
            with transaction.atomic():
                # Get current location record
                current_location_record = LocationTracker._get_current_location_record(
                    item_type, item_id
                )
                
                if not current_location_record:
                    return {
                        'success': False,
                        'error': f'{item_type} with ID {item_id} not found in any location'
                    }
                
                if quantity > current_location_record.quantity:
                    return {
                        'success': False,
                        'error': f'Insufficient quantity. Available: {current_location_record.quantity}, Requested: {quantity}'
                    }
                
                # Create inventory transaction
                transaction_id = generate_transaction_id('CONS')
                inv_transaction = InventoryTransaction.objects.create(
                    transaction_id=transaction_id,
                    transaction_type='consumption',
                    product=current_location_record.product,
                    manufacturing_order=LocationTracker._get_mo_from_reference(reference_type, reference_id),
                    location_from=current_location_record.current_location,
                    location_to=None,
                    quantity=quantity,
                    transaction_datetime=timezone.now(),
                    created_by=user,
                    reference_type=reference_type,
                    reference_id=str(reference_id) if reference_id else None,
                    notes=notes
                )
                
                # Reduce quantity
                current_location_record.quantity -= quantity
                current_location_record.last_moved_by = user
                current_location_record.last_transaction = inv_transaction
                
                # Remove record if quantity becomes 0
                if current_location_record.quantity <= 0:
                    current_location_record.delete()
                else:
                    current_location_record.save()
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'consumed_quantity': quantity,
                    'location': current_location_record.current_location.location_name
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error consuming item: {str(e)}'
            }
    
    @staticmethod
    def get_item_location(item_type, item_id):
        """
        Get current location of an item
        
        Returns:
            dict: Location information or None if not found
        """
        location_record = LocationTracker._get_current_location_record(item_type, item_id)
        
        if location_record:
            return {
                'location_code': location_record.current_location.code,
                'location_name': location_record.current_location.location_name,
                'quantity': location_record.quantity,
                'last_moved_at': location_record.last_moved_at,
                'last_moved_by': location_record.last_moved_by.username if location_record.last_moved_by else None
            }
        
        return None
    
    # Helper methods
    @staticmethod
    def _get_current_location_record(item_type, item_id):
        """Get the current location record for an item"""
        filter_kwargs = {f'{item_type}__id': item_id}
        return ProductLocation.objects.filter(**filter_kwargs).first()
    
    @staticmethod
    def _get_location_record(item_type, item_id, location_code):
        """Get location record for an item at a specific location"""
        filter_kwargs = {
            f'{item_type}__id': item_id,
            'current_location__code': location_code
        }
        return ProductLocation.objects.filter(**filter_kwargs).first()
    
    @staticmethod
    def _create_location_record(item_type, item_id, location, quantity, user, transaction):
        """Create a new location record"""
        create_kwargs = {
            item_type: LocationTracker._get_item_object(item_type, item_id),
            'current_location': location,
            'quantity': quantity,
            'last_moved_by': user,
            'last_transaction': transaction
        }
        return ProductLocation.objects.create(**create_kwargs)
    
    @staticmethod
    def _get_item_object(item_type, item_id):
        """Get the actual item object"""
        if item_type == 'product':
            from products.models import Product
            return Product.objects.get(id=item_id)
        elif item_type == 'raw_material':
            from inventory.models import RawMaterial
            return RawMaterial.objects.get(id=item_id)
        elif item_type == 'batch':
            from manufacturing.models import Batch
            return Batch.objects.get(id=item_id)
        return None
    
    @staticmethod
    def _get_product_from_item(item_type, item_id):
        """Get product object if item is a product"""
        if item_type == 'product':
            from products.models import Product
            return Product.objects.get(id=item_id)
        return None
    
    @staticmethod
    def _get_mo_from_reference(reference_type, reference_id):
        """Get MO object from reference"""
        if reference_type == 'mo' and reference_id:
            from manufacturing.models import ManufacturingOrder
            return ManufacturingOrder.objects.get(id=reference_id)
        return None


# Location mapping for different process stages
PROCESS_LOCATION_MAPPING = {
    'coiling': 'COILING_ZONE',
    'tempering': 'TEMPERING_ZONE', 
    'plating': 'PLATING_ZONE',
    'packing': 'PACKING_ZONE',
    'quality': 'QC_ZONE',
    'rm_store': 'RM_STORE',
    'fg_store': 'FG_STORE'
}


class BatchLocationTracker:
    """
    Specialized tracker for batch movements through manufacturing processes
    """
    
    @staticmethod
    def move_batch_to_process(batch_id, process_name, user, reference_id=None):
        """
        Move a batch to the appropriate location for a process
        
        Args:
            batch_id: ID of the batch
            process_name: Name of the process
            user: User performing the move
            reference_id: Process execution ID
            
        Returns:
            dict: Result of the move operation
        """
        # Determine location based on process name
        location_code = BatchLocationTracker._get_location_for_process(process_name)
        
        notes = f"Batch moved to {process_name} process"
        
        return LocationTracker.move_item(
            item_type='batch',
            item_id=batch_id,
            to_location_code=location_code,
            user=user,
            reference_type='process',
            reference_id=reference_id,
            notes=notes
        )
    
    @staticmethod
    def complete_batch_process(batch_id, process_name, user, reference_id=None):
        """
        Handle batch completion in a process (may move to next location)
        
        Args:
            batch_id: ID of the batch
            process_name: Name of the process that was completed
            user: User completing the process
            reference_id: Process execution ID
            
        Returns:
            dict: Result of any location changes
        """
        # For now, batch stays in same location until next process starts
        # This can be enhanced to move to intermediate locations if needed
        
        return {
            'success': True,
            'message': f'Batch {batch_id} completed {process_name} process',
            'location_changed': False
        }
    
    @staticmethod
    def move_batch_to_packing(batch_id, user, mo_id=None):
        """
        Move completed batch to packing zone (mandatory step before FG store)
        
        Args:
            batch_id: ID of the batch
            user: User performing the move
            mo_id: Manufacturing Order ID
            
        Returns:
            dict: Result of the move operation
        """
        notes = f"Batch moved to packing zone - mandatory step before FG store"
        
        return LocationTracker.move_item(
            item_type='batch',
            item_id=batch_id,
            to_location_code='PACKING_ZONE',
            user=user,
            reference_type='mo',
            reference_id=mo_id,
            notes=notes
        )
    
    @staticmethod
    def move_batch_to_fg_store(batch_id, user, mo_id=None):
        """
        Move completed batch to FG store
        
        Args:
            batch_id: ID of the batch
            user: User performing the move
            mo_id: Manufacturing Order ID
            
        Returns:
            dict: Result of the move operation
        """
        notes = "Batch completed all processes, moved to FG store"
        
        return LocationTracker.move_item(
            item_type='batch',
            item_id=batch_id,
            to_location_code='FG_STORE',
            user=user,
            reference_type='mo',
            reference_id=mo_id,
            notes=notes
        )
    
    @staticmethod
    def _get_location_for_process(process_name):
        """
        Determine the appropriate location code for a process
        
        Args:
            process_name: Name of the process
            
        Returns:
            str: Location code
        """
        process_lower = process_name.lower()
        
        if 'coil' in process_lower:
            return 'COILING_ZONE'
        elif 'temper' in process_lower:
            return 'TEMPERING_ZONE'
        elif 'plat' in process_lower:
            return 'PLATING_ZONE'
        elif 'pack' in process_lower:
            return 'PACKING_ZONE'
        elif 'quality' in process_lower or 'qc' in process_lower:
            return 'QC_ZONE'
        else:
            # Default to production zone
            return 'PRODUCTION_ZONE'
