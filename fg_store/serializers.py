from rest_framework import serializers
from django.db.models import Sum, Q
from .models import DispatchBatch, DispatchTransaction, FGStockAlert, DispatchOrder
from manufacturing.models import ManufacturingOrder, Batch
from products.models import Product
from third_party.models import Customer


class DispatchBatchSerializer(serializers.ModelSerializer):
    """Serializer for Dispatch Batch model"""
    quantity_available = serializers.ReadOnlyField()
    dispatch_percentage = serializers.ReadOnlyField()
    mo_id = serializers.CharField(source='mo.mo_id', read_only=True)
    product_name = serializers.CharField(source='product_code.product_code', read_only=True)
    customer_name = serializers.CharField(source='mo.customer_c_id.name', read_only=True)
    customer_c_id = serializers.CharField(source='mo.customer_c_id.c_id', read_only=True)
    delivery_date = serializers.DateField(source='mo.delivery_date', read_only=True)
    packing_supervisor_name = serializers.CharField(source='packing_supervisor.full_name', read_only=True)
    
    class Meta:
        model = DispatchBatch
        fields = [
            'id', 'batch_id', 'mo', 'mo_id', 'production_batch', 'product_code',
            'product_name', 'customer_name', 'customer_c_id', 'delivery_date',
            'quantity_produced', 'quantity_packed', 'quantity_dispatched',
            'loose_stock', 'quantity_available', 'dispatch_percentage',
            'status', 'location_in_store', 'packing_date', 'packing_supervisor',
            'packing_supervisor_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['batch_id', 'created_at', 'updated_at']


class DispatchBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Dispatch Batch"""
    
    class Meta:
        model = DispatchBatch
        fields = [
            'mo', 'production_batch', 'product_code', 'quantity_produced',
            'quantity_packed', 'loose_stock', 'location_in_store',
            'packing_date', 'packing_supervisor'
        ]
    
    def validate(self, data):
        """Validate dispatch batch data"""
        mo = data.get('mo')
        production_batch = data.get('production_batch')
        product_code = data.get('product_code')
        
        # Validate MO exists and is completed
        if mo and mo.status != 'completed':
            raise serializers.ValidationError(
                f"Manufacturing Order {mo.mo_id} must be completed before creating dispatch batch"
            )
        
        # Validate production batch belongs to MO
        if production_batch and production_batch.mo != mo:
            raise serializers.ValidationError(
                "Production batch must belong to the specified MO"
            )
        
        # Validate product matches MO product
        if product_code and mo and mo.product_code != product_code:
            raise serializers.ValidationError(
                "Product code must match the MO's product code"
            )
        
        return data


class DispatchTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Dispatch Transaction model"""
    transaction_id = serializers.ReadOnlyField()
    dispatch_date = serializers.ReadOnlyField()
    mo_id = serializers.CharField(source='mo.mo_id', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_c_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    product_name = serializers.CharField(source='mo.product_code.product_code', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor_id.full_name', read_only=True)
    batch_id = serializers.CharField(source='dispatch_batch.batch_id', read_only=True)
    
    class Meta:
        model = DispatchTransaction
        fields = [
            'id', 'transaction_id', 'mo', 'mo_id', 'dispatch_batch', 'batch_id',
            'customer_c_id', 'customer_name', 'product_name', 'quantity_dispatched',
            'dispatch_date', 'supervisor_id', 'supervisor_name', 'status',
            'notes', 'delivery_reference', 'confirmed_at', 'received_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['transaction_id', 'dispatch_date', 'created_at', 'updated_at']


class DispatchTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Dispatch Transaction"""
    
    class Meta:
        model = DispatchTransaction
        fields = [
            'mo', 'dispatch_batch', 'customer_c_id', 'quantity_dispatched',
            'supervisor_id', 'notes', 'delivery_reference'
        ]
    
    def validate(self, data):
        """Validate dispatch transaction data"""
        dispatch_batch = data.get('dispatch_batch')
        quantity_dispatched = data.get('quantity_dispatched')
        
        # Validate quantity can be dispatched
        if dispatch_batch and not dispatch_batch.can_dispatch(quantity_dispatched):
            raise serializers.ValidationError(
                f"Cannot dispatch {quantity_dispatched} units. "
                f"Available quantity: {dispatch_batch.quantity_available}"
            )
        
        return data


class DispatchTransactionConfirmSerializer(serializers.Serializer):
    """Serializer for confirming dispatch transaction"""
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate confirmation data"""
        transaction = self.context.get('transaction')
        if not transaction:
            raise serializers.ValidationError("Transaction not found")
        
        if transaction.status != 'pending_confirmation':
            raise serializers.ValidationError(
                f"Transaction {transaction.transaction_id} is not pending confirmation"
            )
        
        return data


class FGStockAlertSerializer(serializers.ModelSerializer):
    """Serializer for FG Stock Alert model"""
    product_name = serializers.CharField(source='product_code.product_code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = FGStockAlert
        fields = [
            'id', 'product_code', 'product_name', 'alert_type', 'severity',
            'min_stock_level', 'max_stock_level', 'expiry_days_threshold',
            'is_active', 'last_triggered', 'last_alerted', 'description',
            'created_at', 'created_by', 'created_by_name', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DispatchOrderSerializer(serializers.ModelSerializer):
    """Serializer for Dispatch Order model"""
    order_id = serializers.ReadOnlyField()
    mo_id = serializers.CharField(source='mo.mo_id', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_c_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    product_name = serializers.CharField(source='mo.product_code.product_code', read_only=True)
    remaining_quantity = serializers.ReadOnlyField()
    dispatch_percentage = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = DispatchOrder
        fields = [
            'id', 'order_id', 'mo', 'mo_id', 'customer_c_id', 'customer_name',
            'product_name', 'total_quantity_ordered', 'total_quantity_dispatched',
            'remaining_quantity', 'dispatch_percentage', 'dispatch_date',
            'status', 'special_instructions', 'delivery_address',
            'created_at', 'created_by', 'created_by_name', 'updated_at'
        ]
        read_only_fields = ['order_id', 'created_at', 'updated_at']


class FGStockLevelSerializer(serializers.Serializer):
    """Serializer for FG Stock Level dashboard data"""
    batch_id = serializers.CharField()
    mo_id = serializers.CharField()
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    quantity_in_stock = serializers.IntegerField()
    loose_stock = serializers.IntegerField()
    unit = serializers.CharField()
    location = serializers.CharField()
    customer_name = serializers.CharField()
    delivery_date = serializers.DateField()
    status = serializers.CharField()
    packing_date = serializers.DateTimeField()


class MOPendingDispatchSerializer(serializers.Serializer):
    """Serializer for MO List (Pending Dispatch) data"""
    mo_id = serializers.CharField()
    customer_name = serializers.CharField()
    customer_c_id = serializers.CharField()
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    quantity_ordered = serializers.IntegerField()
    quantity_packed = serializers.IntegerField()
    quantity_dispatched = serializers.IntegerField()
    quantity_pending = serializers.IntegerField()
    delivery_date = serializers.DateField()
    priority = serializers.CharField()
    status = serializers.CharField()
    dispatch_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class DispatchTransactionLogSerializer(serializers.Serializer):
    """Serializer for Transactions Log data"""
    transaction_id = serializers.CharField()
    mo_id = serializers.CharField()
    batch_id = serializers.CharField()
    transaction_type = serializers.CharField()
    quantity = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    supervisor_id = serializers.IntegerField()
    supervisor_name = serializers.CharField()
    customer_name = serializers.CharField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    notes = serializers.CharField()


class DispatchValidationSerializer(serializers.Serializer):
    """Serializer for dispatch validation response"""
    is_valid = serializers.BooleanField()
    available_qty = serializers.IntegerField()
    warnings = serializers.ListField(child=serializers.CharField())
    errors = serializers.ListField(child=serializers.CharField())
