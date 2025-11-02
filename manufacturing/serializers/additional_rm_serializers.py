"""
Serializers for Additional RM Request functionality
"""

from rest_framework import serializers
from decimal import Decimal
from ..models.additional_rm import AdditionalRMRequest
from ..models import ManufacturingOrder, Batch
from authentication.serializers import UserBasicSerializer


class AdditionalRMRequestListSerializer(serializers.ModelSerializer):
    """List serializer for Additional RM Requests"""
    
    mo_id = serializers.CharField(source='mo.mo_id', read_only=True)
    mo_product = serializers.CharField(source='mo.product_code.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    rejected_by_name = serializers.SerializerMethodField()
    excess_batch_id = serializers.CharField(source='excess_batch.batch_id', read_only=True, allow_null=True)
    
    # Calculated fields
    total_new_limit_kg = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    can_mark_complete = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AdditionalRMRequest
        fields = [
            'id', 'request_id', 'mo', 'mo_id', 'mo_product',
            'original_allocated_rm_kg', 'rm_released_so_far_kg',
            'additional_rm_requested_kg', 'approved_quantity_kg',
            'reason', 'excess_batch', 'excess_batch_id',
            'status', 'status_display',
            'requested_by', 'requested_by_name', 'requested_at',
            'approved_by', 'approved_by_name', 'approved_at', 'approval_notes',
            'rejected_by', 'rejected_by_name', 'rejected_at', 'rejection_reason',
            'marked_complete_by', 'marked_complete_at', 'completion_notes',
            'total_new_limit_kg', 'can_mark_complete',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['request_id', 'created_at', 'updated_at']
    
    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.username
        return None
    
    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None
    
    def get_rejected_by_name(self, obj):
        if obj.rejected_by:
            return obj.rejected_by.get_full_name() or obj.rejected_by.username
        return None


class AdditionalRMRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Additional RM Requests"""
    
    # Related objects
    requested_by = UserBasicSerializer(read_only=True)
    approved_by = UserBasicSerializer(read_only=True)
    rejected_by = UserBasicSerializer(read_only=True)
    marked_complete_by = UserBasicSerializer(read_only=True)
    
    # MO details
    mo_details = serializers.SerializerMethodField()
    
    # Batch details
    excess_batch_details = serializers.SerializerMethodField()
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Calculated fields
    total_new_limit_kg = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    can_mark_complete = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AdditionalRMRequest
        fields = '__all__'
        read_only_fields = [
            'request_id', 'requested_by', 'requested_at',
            'approved_by', 'approved_at', 'rejected_by', 'rejected_at',
            'marked_complete_by', 'marked_complete_at',
            'created_at', 'updated_at'
        ]
    
    def get_mo_details(self, obj):
        from .serializers import ManufacturingOrderListSerializer
        return ManufacturingOrderListSerializer(obj.mo).data
    
    def get_excess_batch_details(self, obj):
        if obj.excess_batch:
            return {
                'id': obj.excess_batch.id,
                'batch_id': obj.excess_batch.batch_id,
                'planned_quantity_grams': obj.excess_batch.planned_quantity,
                'planned_quantity_kg': float(obj.excess_batch.planned_quantity / 1000),
                'status': obj.excess_batch.status,
                'notes': obj.excess_batch.notes,
            }
        return None


class CreateAdditionalRMRequestSerializer(serializers.Serializer):
    """Serializer for creating an additional RM request"""
    
    mo_id = serializers.IntegerField(required=True)
    additional_rm_requested_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        required=True,
        min_value=Decimal('0.001')
    )
    reason = serializers.CharField(required=True, min_length=10)
    excess_batch_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_mo_id(self, value):
        """Validate MO exists and is in proper status"""
        try:
            mo = ManufacturingOrder.objects.get(id=value)
        except ManufacturingOrder.DoesNotExist:
            raise serializers.ValidationError("Manufacturing Order not found")
        
        if mo.status not in ['on_hold', 'in_progress']:
            raise serializers.ValidationError(
                f"Cannot request additional RM for MO in {mo.status} status"
            )
        
        return value
    
    def validate_excess_batch_id(self, value):
        """Validate batch exists if provided"""
        if value:
            try:
                Batch.objects.get(id=value)
            except Batch.DoesNotExist:
                raise serializers.ValidationError("Batch not found")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        mo_id = attrs['mo_id']
        mo = ManufacturingOrder.objects.get(id=mo_id)
        
        # Check if there's already a pending request
        pending_exists = AdditionalRMRequest.objects.filter(
            mo=mo,
            status='pending'
        ).exists()
        
        if pending_exists:
            raise serializers.ValidationError(
                "There is already a pending additional RM request for this MO"
            )
        
        # Verify that RM limit is actually exceeded
        if not mo.is_rm_limit_exceeded:
            raise serializers.ValidationError(
                "Cannot request additional RM - current limit not exceeded"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create the additional RM request"""
        mo = ManufacturingOrder.objects.get(id=validated_data['mo_id'])
        excess_batch = None
        
        if validated_data.get('excess_batch_id'):
            excess_batch = Batch.objects.get(id=validated_data['excess_batch_id'])
        
        request = AdditionalRMRequest.objects.create(
            mo=mo,
            original_allocated_rm_kg=mo.rm_required_kg or Decimal('0'),
            rm_released_so_far_kg=mo.total_rm_released_kg,
            additional_rm_requested_kg=validated_data['additional_rm_requested_kg'],
            reason=validated_data['reason'],
            excess_batch=excess_batch,
            requested_by=self.context['request'].user
        )
        
        return request


class ApproveAdditionalRMRequestSerializer(serializers.Serializer):
    """Serializer for approving an additional RM request"""
    
    approved_quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        required=True,
        min_value=Decimal('0.001')
    )
    approval_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_approved_quantity_kg(self, value):
        """Validate approved quantity is reasonable"""
        # Get the request from context
        request_obj = self.context.get('request_obj')
        if request_obj:
            # Approved quantity should not exceed 2x requested (as a safety check)
            max_allowed = request_obj.additional_rm_requested_kg * Decimal('2')
            if value > max_allowed:
                raise serializers.ValidationError(
                    f"Approved quantity cannot exceed 2x requested quantity ({max_allowed} kg)"
                )
        
        return value


class RejectAdditionalRMRequestSerializer(serializers.Serializer):
    """Serializer for rejecting an additional RM request"""
    
    rejection_reason = serializers.CharField(required=True, min_length=10)


class MarkCompleteAdditionalRMRequestSerializer(serializers.Serializer):
    """Serializer for marking additional RM request as complete"""
    
    completion_notes = serializers.CharField(required=False, allow_blank=True)

