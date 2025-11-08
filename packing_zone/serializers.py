from rest_framework import serializers
from .models import (
    PackingBatch, PackingTransaction, LooseStock, MergedHeatNumber,
    MergeRequest, StockAdjustment, PackingLabel, FGStock
)
from authentication.models import CustomUser
from products.models import Product
from django.utils import timezone
from decimal import Decimal


class PackingUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for packing activities"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']


class PackingBatchListSerializer(serializers.ModelSerializer):
    """List serializer for packing batches"""
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    released_by_name = serializers.CharField(source='released_by.full_name', read_only=True)
    available_quantity_kg = serializers.DecimalField(
        max_digits=10, decimal_places=3, read_only=True
    )
    
    class Meta:
        model = PackingBatch
        fields = [
            'id', 'mo_id', 'product_code', 'ipc', 'heat_no', 'coil_no',
            'ok_quantity_kg', 'actual_received_kg', 'available_quantity_kg',
            'grams_per_product', 'packing_size', 'status', 'hold_reason',
            'hold_notes', 'verified_by', 'verified_by_name', 'verified_date',
            'released_by', 'released_by_name', 'released_date',
            'received_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'received_date']


class PackingBatchDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for packing batches"""
    verified_by_detail = PackingUserSerializer(source='verified_by', read_only=True)
    released_by_detail = PackingUserSerializer(source='released_by', read_only=True)
    available_quantity_kg = serializers.DecimalField(
        max_digits=10, decimal_places=3, read_only=True
    )
    
    class Meta:
        model = PackingBatch
        fields = [
            'id', 'mo_id', 'product_code', 'product', 'ipc', 'heat_no', 'coil_no',
            'ok_quantity_kg', 'actual_received_kg', 'available_quantity_kg',
            'grams_per_product', 'packing_size', 'status', 'hold_reason',
            'hold_notes', 'verified_by', 'verified_by_detail', 'verified_date',
            'released_by', 'released_by_detail', 'released_date',
            'received_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'received_date']


class PackingBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating packing batches (from Final Inspection)"""
    
    class Meta:
        model = PackingBatch
        fields = [
            'mo_id', 'product_code', 'product', 'ipc', 'heat_no', 'coil_no',
            'ok_quantity_kg', 'grams_per_product', 'packing_size'
        ]
    
    def validate(self, data):
        """Validate packing batch data"""
        if data.get('ok_quantity_kg') and data['ok_quantity_kg'] <= 0:
            raise serializers.ValidationError({
                'ok_quantity_kg': 'Quantity must be greater than 0'
            })
        
        if data.get('grams_per_product') and data['grams_per_product'] <= 0:
            raise serializers.ValidationError({
                'grams_per_product': 'Grams per product must be greater than 0'
            })
        
        if data.get('packing_size') and data['packing_size'] <= 0:
            raise serializers.ValidationError({
                'packing_size': 'Packing size must be greater than 0'
            })
        
        return data


class PackingBatchVerifySerializer(serializers.Serializer):
    """Serializer for verifying batches"""
    verified = serializers.BooleanField(default=True)


class PackingBatchReportSerializer(serializers.Serializer):
    """Serializer for reporting batch issues"""
    reason = serializers.ChoiceField(choices=PackingBatch.HOLD_REASON_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    actual_kg = serializers.DecimalField(
        max_digits=10, decimal_places=3, required=False, allow_null=True
    )
    
    def validate(self, data):
        """Validate report data"""
        reason = data.get('reason')
        if reason in ['low_qty', 'high_qty'] and not data.get('actual_kg'):
            raise serializers.ValidationError({
                'actual_kg': 'Actual kg is required for quantity discrepancies'
            })
        return data


class PackingTransactionListSerializer(serializers.ModelSerializer):
    """List serializer for packing transactions"""
    packed_by_name = serializers.CharField(source='packed_by.full_name', read_only=True)
    batch_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PackingTransaction
        fields = [
            'id', 'product_code', 'ipc', 'heat_no', 'total_weight_kg',
            'grams_per_product', 'packing_size', 'theoretical_packs',
            'actual_packs', 'loose_weight_kg', 'loose_pieces', 'variance_kg',
            'packed_by', 'packed_by_name', 'packed_date', 'batch_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_batch_count(self, obj):
        return obj.batches.count()


class PackingTransactionDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for packing transactions"""
    packed_by_detail = PackingUserSerializer(source='packed_by', read_only=True)
    batches_detail = PackingBatchListSerializer(source='batches', many=True, read_only=True)
    
    class Meta:
        model = PackingTransaction
        fields = [
            'id', 'batches', 'batches_detail', 'product_code', 'product', 'ipc',
            'heat_no', 'total_weight_kg', 'grams_per_product', 'packing_size',
            'theoretical_packs', 'actual_packs', 'loose_weight_kg',
            'loose_pieces', 'variance_kg', 'packed_by', 'packed_by_detail',
            'packed_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PackingTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating packing transactions"""
    batch_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    
    class Meta:
        model = PackingTransaction
        fields = [
            'batch_ids', 'product_code', 'product', 'ipc', 'heat_no',
            'total_weight_kg', 'grams_per_product', 'packing_size',
            'theoretical_packs', 'actual_packs', 'loose_weight_kg',
            'loose_pieces', 'variance_kg'
        ]
    
    def validate(self, data):
        """Validate packing transaction data"""
        # Validate batch IDs
        batch_ids = data.get('batch_ids', [])
        if not batch_ids:
            raise serializers.ValidationError({
                'batch_ids': 'At least one batch must be selected'
            })
        
        # Validate batches exist and are verified
        batches = PackingBatch.objects.filter(id__in=batch_ids, status='verified')
        if batches.count() != len(batch_ids):
            raise serializers.ValidationError({
                'batch_ids': 'All batches must be verified'
            })
        
        # Validate all batches have same product and heat number
        unique_products = batches.values_list('product_code', flat=True).distinct()
        unique_heat_nos = batches.values_list('heat_no', flat=True).distinct()
        
        if len(unique_products) > 1:
            raise serializers.ValidationError({
                'batch_ids': 'All batches must be for the same product'
            })
        
        if len(unique_heat_nos) > 1:
            raise serializers.ValidationError({
                'batch_ids': 'All batches must have the same heat number'
            })
        
        # Validate quantities
        if data.get('actual_packs') and data['actual_packs'] < 0:
            raise serializers.ValidationError({
                'actual_packs': 'Actual packs cannot be negative'
            })
        
        if data.get('loose_weight_kg') and data['loose_weight_kg'] < 0:
            raise serializers.ValidationError({
                'loose_weight_kg': 'Loose weight cannot be negative'
            })
        
        return data
    
    def create(self, validated_data):
        """Create packing transaction and update batches"""
        batch_ids = validated_data.pop('batch_ids')
        packed_by = self.context['request'].user
        
        # Create transaction
        transaction = PackingTransaction.objects.create(
            **validated_data,
            packed_by=packed_by
        )
        
        # Link batches
        batches = PackingBatch.objects.filter(id__in=batch_ids)
        transaction.batches.set(batches)
        
        # Update batch status
        batches.update(status='packed')
        
        # Update loose stock
        if validated_data['loose_weight_kg'] > 0:
            loose_stock, created = LooseStock.objects.get_or_create(
                product_code=validated_data['product_code'],
                ipc=validated_data['ipc'],
                heat_no=validated_data['heat_no'],
                defaults={
                    'product': validated_data.get('product'),
                    'grams_per_product': validated_data['grams_per_product'],
                    'loose_kg': Decimal('0.000'),
                    'loose_pieces': 0
                }
            )
            loose_stock.add_loose(
                validated_data['loose_weight_kg'],
                validated_data['loose_pieces']
            )
        
        # Update FG stock
        fg_stock, created = FGStock.objects.get_or_create(
            product_code=validated_data['product_code'],
            ipc=validated_data['ipc'],
            heat_no=validated_data['heat_no'],
            defaults={
                'product': validated_data.get('product'),
                'packing_size': validated_data['packing_size'],
                'grams_per_product': validated_data['grams_per_product'],
                'total_packs': 0
            }
        )
        fg_stock.add_packs(validated_data['actual_packs'])
        
        return transaction


class LooseStockSerializer(serializers.ModelSerializer):
    """Serializer for loose stock"""
    age_days = serializers.IntegerField(read_only=True)
    is_old = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LooseStock
        fields = [
            'id', 'product_code', 'product', 'ipc', 'heat_no',
            'loose_kg', 'loose_pieces', 'grams_per_product',
            'age_days', 'is_old', 'first_added_date', 'last_updated'
        ]
        read_only_fields = ['first_added_date', 'last_updated']


class MergedHeatNumberSerializer(serializers.ModelSerializer):
    """Serializer for merged heat numbers"""
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    original_heat_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MergedHeatNumber
        fields = [
            'id', 'merged_heat_no', 'original_heat_nos', 'original_heat_count',
            'product_code', 'product', 'ipc', 'heat_quantities',
            'total_merged_kg', 'total_merged_pieces', 'approved_by',
            'approved_by_name', 'approved_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'approved_date']
    
    def get_original_heat_count(self, obj):
        return len(obj.original_heat_nos) if obj.original_heat_nos else 0


class MergeRequestListSerializer(serializers.ModelSerializer):
    """List serializer for merge requests"""
    requested_by_name = serializers.CharField(source='requested_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    heat_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MergeRequest
        fields = [
            'id', 'product_code', 'ipc', 'heat_count', 'total_kg',
            'total_pieces', 'status', 'requested_by', 'requested_by_name',
            'requested_date', 'reviewed_by', 'reviewed_by_name', 'reviewed_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_heat_count(self, obj):
        return len(obj.heat_numbers_data) if obj.heat_numbers_data else 0


class MergeRequestDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for merge requests"""
    requested_by_detail = PackingUserSerializer(source='requested_by', read_only=True)
    reviewed_by_detail = PackingUserSerializer(source='reviewed_by', read_only=True)
    merged_heat_number_detail = MergedHeatNumberSerializer(
        source='merged_heat_number', read_only=True
    )
    
    class Meta:
        model = MergeRequest
        fields = [
            'id', 'product_code', 'product', 'ipc', 'heat_numbers_data',
            'total_kg', 'total_pieces', 'requested_by', 'requested_by_detail',
            'requested_date', 'reason', 'status', 'reviewed_by',
            'reviewed_by_detail', 'reviewed_date', 'review_notes',
            'merged_heat_number', 'merged_heat_number_detail',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class MergeRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating merge requests"""
    
    class Meta:
        model = MergeRequest
        fields = [
            'product_code', 'product', 'ipc', 'heat_numbers_data',
            'total_kg', 'total_pieces', 'reason'
        ]
    
    def validate(self, data):
        """Validate merge request data"""
        heat_data = data.get('heat_numbers_data', [])
        
        if len(heat_data) < 2:
            raise serializers.ValidationError({
                'heat_numbers_data': 'At least 2 heat numbers must be selected for merge'
            })
        
        # Validate all lots are old enough (>50 days)
        for item in heat_data:
            if item.get('age_days', 0) <= 50:
                raise serializers.ValidationError({
                    'heat_numbers_data': f'Heat number {item.get("heat_no")} is not old enough (must be >50 days)'
                })
        
        # Validate all have same product
        unique_products = set(item.get('product_code') for item in heat_data if item.get('product_code'))
        if len(unique_products) > 1:
            raise serializers.ValidationError({
                'heat_numbers_data': 'All heat numbers must be for the same product'
            })
        
        return data
    
    def create(self, validated_data):
        """Create merge request"""
        requested_by = self.context['request'].user
        return MergeRequest.objects.create(
            **validated_data,
            requested_by=requested_by
        )


class MergeRequestApproveSerializer(serializers.Serializer):
    """Serializer for approving merge requests"""
    merged_heat_no = serializers.CharField(
        max_length=50,
        help_text='New merged heat number (e.g., H2025A42M1)'
    )
    
    def validate_merged_heat_no(self, value):
        """Validate merged heat number is unique"""
        if MergedHeatNumber.objects.filter(merged_heat_no=value).exists():
            raise serializers.ValidationError(
                'This merged heat number already exists'
            )
        return value


class MergeRequestRejectSerializer(serializers.Serializer):
    """Serializer for rejecting merge requests"""
    notes = serializers.CharField(required=False, allow_blank=True)


class StockAdjustmentListSerializer(serializers.ModelSerializer):
    """List serializer for stock adjustments"""
    requested_by_name = serializers.CharField(source='requested_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    
    class Meta:
        model = StockAdjustment
        fields = [
            'id', 'product_code', 'ipc', 'heat_no', 'adjustment_kg',
            'adjustment_pieces', 'reason', 'status', 'requested_by',
            'requested_by_name', 'requested_date', 'reviewed_by',
            'reviewed_by_name', 'reviewed_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockAdjustmentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for stock adjustments"""
    requested_by_detail = PackingUserSerializer(source='requested_by', read_only=True)
    reviewed_by_detail = PackingUserSerializer(source='reviewed_by', read_only=True)
    
    class Meta:
        model = StockAdjustment
        fields = [
            'id', 'product_code', 'product', 'ipc', 'heat_no',
            'adjustment_kg', 'adjustment_pieces', 'reason', 'reason_details',
            'status', 'requested_by', 'requested_by_detail', 'requested_date',
            'reviewed_by', 'reviewed_by_detail', 'reviewed_date', 'review_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockAdjustmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stock adjustments"""
    
    class Meta:
        model = StockAdjustment
        fields = [
            'product_code', 'product', 'ipc', 'heat_no',
            'adjustment_kg', 'adjustment_pieces', 'reason', 'reason_details'
        ]
    
    def validate(self, data):
        """Validate stock adjustment data"""
        # Check if loose stock exists
        try:
            loose_stock = LooseStock.objects.get(
                product_code=data['product_code'],
                ipc=data['ipc'],
                heat_no=data['heat_no']
            )
            
            # Validate adjustment doesn't exceed available
            if data['adjustment_kg'] > loose_stock.loose_kg:
                raise serializers.ValidationError({
                    'adjustment_kg': f'Adjustment exceeds available loose stock ({loose_stock.loose_kg} kg)'
                })
            
            if data['adjustment_pieces'] > loose_stock.loose_pieces:
                raise serializers.ValidationError({
                    'adjustment_pieces': f'Adjustment exceeds available loose pieces ({loose_stock.loose_pieces} pcs)'
                })
        except LooseStock.DoesNotExist:
            raise serializers.ValidationError({
                'heat_no': 'No loose stock found for this product and heat number'
            })
        
        return data
    
    def create(self, validated_data):
        """Create stock adjustment"""
        requested_by = self.context['request'].user
        return StockAdjustment.objects.create(
            **validated_data,
            requested_by=requested_by
        )


class StockAdjustmentApproveSerializer(serializers.Serializer):
    """Serializer for approving stock adjustments"""
    pass


class StockAdjustmentRejectSerializer(serializers.Serializer):
    """Serializer for rejecting stock adjustments"""
    notes = serializers.CharField(required=False, allow_blank=True)


class PackingLabelSerializer(serializers.ModelSerializer):
    """Serializer for packing labels"""
    printed_by_name = serializers.CharField(source='printed_by.full_name', read_only=True)
    merged_heat_number_detail = MergedHeatNumberSerializer(
        source='merged_heat_number', read_only=True
    )
    
    class Meta:
        model = PackingLabel
        fields = [
            'id', 'label_id', 'product_code', 'product', 'ipc', 'product_name',
            'packing_size', 'quantity_pcs', 'quantity_kg', 'heat_no',
            'merged_heat_no', 'merged_heat_number_detail', 'date_of_manufacture',
            'date_packed', 'printed_by', 'printed_by_name', 'printed_date',
            'reprint_count', 'last_reprinted', 'packing_transaction',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'printed_date']


class PackingLabelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating packing labels"""
    pack_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text='List of FG stock IDs to generate labels for'
    )
    
    class Meta:
        model = PackingLabel
        fields = [
            'pack_ids', 'packing_transaction'
        ]
    
    def create(self, validated_data):
        """Create multiple labels for selected packs"""
        pack_ids = validated_data.pop('pack_ids')
        transaction = validated_data.get('packing_transaction')
        printed_by = self.context['request'].user
        
        labels = []
        for pack_id in pack_ids:
            # Get pack details from FG stock
            try:
                fg_stock = FGStock.objects.get(id=pack_id)
                
                # Generate unique label ID
                label_id = f"LBL{timezone.now().strftime('%Y%m%d%H%M%S')}{pack_id}"
                
                label = PackingLabel.objects.create(
                    label_id=label_id,
                    product_code=fg_stock.product_code,
                    product=fg_stock.product,
                    ipc=fg_stock.ipc,
                    product_name=fg_stock.product.product_name if fg_stock.product else '',
                    packing_size=fg_stock.packing_size,
                    quantity_pcs=fg_stock.packing_size,
                    quantity_kg=(fg_stock.packing_size * fg_stock.grams_per_product) / 1000,
                    heat_no=fg_stock.heat_no,
                    date_of_manufacture=transaction.packed_date.date() if transaction else timezone.now().date(),
                    date_packed=timezone.now().date(),
                    printed_by=printed_by,
                    packing_transaction=transaction
                )
                labels.append(label)
            except FGStock.DoesNotExist:
                continue
        
        return labels


class FGStockSerializer(serializers.ModelSerializer):
    """Serializer for FG stock"""
    
    class Meta:
        model = FGStock
        fields = [
            'id', 'product_code', 'product', 'ipc', 'heat_no',
            'total_packs', 'packing_size', 'grams_per_product', 'last_updated'
        ]
        read_only_fields = ['last_updated']


class PackingDashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    to_be_verified = serializers.IntegerField()
    verified = serializers.IntegerField()
    on_hold = serializers.IntegerField()
    packed_today = serializers.IntegerField()
    pending_merge_requests = serializers.IntegerField()
    pending_adjustments = serializers.IntegerField()
    total_loose_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    total_fg_packs = serializers.IntegerField()

