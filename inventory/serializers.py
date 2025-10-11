from rest_framework import serializers
from django.db import transaction
from products.models import Product
from .models import (
    RMStockBalance, RawMaterial, InventoryTransaction, Location,
    GRMReceipt, HeatNumber, RMStockBalanceHeat, InventoryTransactionHeat
)


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.CharField(source='material_name', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    finishing_display = serializers.CharField(source='get_finishing_display', read_only=True)
    available_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'material_code', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'thickness_mm', 'finishing', 'finishing_display', 'weight_kg', 'available_quantity',
            'length_mm', 'breadth_mm', 'quantity'
        ]
        read_only_fields = fields
    
    def get_available_quantity(self, obj):
        """Get available quantity from RMStockBalance"""
        stock_balance = RMStockBalance.objects.filter(raw_material=obj).first()
        if stock_balance:
            return float(stock_balance.available_quantity)
        return 0.0


class ProductListSerializer(serializers.ModelSerializer):
    """Product serializer for list view with stock balance"""
    material_details = RawMaterialBasicSerializer(source='material', read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    spring_type_display = serializers.CharField(source='get_spring_type_display', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    stock_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type', 
            'product_type_display', 'spring_type', 'spring_type_display',
            'material_details', 'customer_name', 'customer_id', 'stock_balance', 
            'grams_per_product', 'length_mm', 'breadth_mm',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_stock_balance(self, obj):
        """Get stock balance for the product"""
        try:
            stock_balance = obj.stock_balances.first()
            if stock_balance:
                return {
                    'available_quantity': stock_balance.available_quantity,
                    'last_updated': stock_balance.last_updated
                }
            return {
                'available_quantity': 0,
                'last_updated': None
            }
        except:
            return {
                'available_quantity': 0,
                'last_updated': None
            }


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product serializer for create/update operations"""
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type', 
            'spring_type', 'material', 'customer_c_id', 'grams_per_product',
            'length_mm', 'breadth_mm'
        ]
        read_only_fields = ['id']
    
    def validate_internal_product_code(self, value):
        """Validate internal product code uniqueness"""
        if value:
            instance = getattr(self, 'instance', None)
            if instance:
                # Update case - exclude current instance
                if Product.objects.filter(internal_product_code=value).exclude(id=instance.id).exists():
                    raise serializers.ValidationError("Internal product code already exists.")
            else:
                # Create case
                if Product.objects.filter(internal_product_code=value).exists():
                    raise serializers.ValidationError("Internal product code already exists.")
        return value
    
    def validate_product_code(self, value):
        """Validate product code uniqueness"""
        instance = getattr(self, 'instance', None)
        if instance:
            # Update case - exclude current instance
            if Product.objects.filter(product_code=value).exclude(id=instance.id).exists():
                raise serializers.ValidationError("Product code already exists.")
        else:
            # Create case
            if Product.objects.filter(product_code=value).exists():
                raise serializers.ValidationError("Product code already exists.")
        return value
    
    def create(self, validated_data):
        """Create product with audit trail"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class RMStockBalanceSerializer(serializers.ModelSerializer):
    """RMStockBalance serializer for CRUD operations"""
    raw_material_details = RawMaterialBasicSerializer(source='raw_material', read_only=True)
    material_code = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = RMStockBalance
        fields = [
            'id', 'raw_material', 'raw_material_details', 'material_code',
            'available_quantity', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def validate_available_quantity(self, value):
        """Validate available quantity is not negative"""
        if value < 0:
            raise serializers.ValidationError("Available quantity cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create or update stock balance using update_or_create"""
        material_code = validated_data.pop('material_code', None)
        
        if material_code:
            try:
                raw_material = RawMaterial.objects.only("id").get(material_code=material_code)
                validated_data['raw_material'] = raw_material
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError({"material_code": "Raw material with this code does not exist."})
        
        raw_material = validated_data['raw_material']
        available_quantity = validated_data['available_quantity']
        
        # Use update_or_create for upsert behavior
        stock_balance, created = RMStockBalance.objects.update_or_create(
            raw_material=raw_material,
            defaults={'available_quantity': available_quantity}
        )
        
        return stock_balance
    
    def update(self, instance, validated_data):
        """Update stock balance"""
        material_code = validated_data.pop('material_code', None)
        
        if material_code:
            try:
                raw_material = RawMaterial.objects.only("id").get(material_code=material_code)
                validated_data['raw_material'] = raw_material
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError({"material_code": "Raw material with this code does not exist."})
        
        return super().update(instance, validated_data)


class RMStockBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for bulk stock balance updates using material_code"""
    material_code = serializers.CharField(max_length=120)
    available_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0)
    
    def validate_material_code(self, value):
        """Validate that raw material exists"""
        try:
            RawMaterial.objects.only("id").get(material_code=value)
        except RawMaterial.DoesNotExist:
            raise serializers.ValidationError("Raw material with this code does not exist.")
        return value


class ProductStockDashboardSerializer(serializers.ModelSerializer):
    """Combined serializer for RM Store dashboard showing products with stock"""
    material = RawMaterialBasicSerializer(read_only=True)
    material_name = serializers.CharField(read_only=True)
    material_type_display = serializers.CharField(read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    spring_type_display = serializers.CharField(source='get_spring_type_display', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    stock_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type',
            'product_type_display', 'spring_type', 'spring_type_display',
            'material', 'material_name', 'material_type_display', 'customer_name', 
            'customer_id', 'stock_info'
        ]
    
    def get_stock_info(self, obj):
        """Get comprehensive stock information from material's stock balance"""
        try:
            # Access stock balance through the material relationship
            if obj.material and hasattr(obj.material, 'stock_balances'):
                stock_balance = obj.material.stock_balances.first()
                if stock_balance:
                    return {
                        'available_quantity': stock_balance.available_quantity,
                        'last_updated': stock_balance.last_updated,
                        'stock_status': 'in_stock' if stock_balance.available_quantity > 0 else 'out_of_stock'
                    }
            return {
                'available_quantity': 0,
                'last_updated': None,
                'stock_status': 'no_stock_record'
            }
        except Exception as e:
            return {
                'available_quantity': 0,
                'last_updated': None,
                'stock_status': 'error'
            }


class LocationBasicSerializer(serializers.ModelSerializer):
    """Minimal serializer for inventory locations"""

    class Meta:
        model = Location
        fields = ['id', 'location_name', 'location_type', 'parent_location']


class InventoryTransactionSerializer(serializers.ModelSerializer):
    """Serializer for inventory transactions"""
    product_display = serializers.SerializerMethodField()
    location_from_details = LocationBasicSerializer(source='location_from', read_only=True)
    location_to_details = LocationBasicSerializer(source='location_to', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'transaction_id', 'transaction_type', 'product', 'product_display',
            'manufacturing_order', 'location_from', 'location_from_details',
            'location_to', 'location_to_details', 'quantity', 'unit_cost',
            'total_value', 'transaction_datetime', 'created_at', 'created_by', 'created_by_name',
            'reference_type', 'reference_id',
        ]
        read_only_fields = fields

    def get_product_display(self, obj):
        if obj.product:
            if hasattr(obj.product, 'internal_product_code') and obj.product.internal_product_code:
                return f"{obj.product.internal_product_code} - {obj.product.product_code}"
            return getattr(obj.product, 'product_code', None)
        return None


# GRM and Heat Number Serializers

class HeatNumberSerializer(serializers.ModelSerializer):
    """Serializer for Heat Number model"""
    raw_material_details = RawMaterialBasicSerializer(source='raw_material', read_only=True)
    available_quantity_kg = serializers.SerializerMethodField()
    available_coils = serializers.SerializerMethodField()
    grm_number = serializers.CharField(source='grm_receipt.grm_number', read_only=True)
    
    class Meta:
        model = HeatNumber
        fields = [
            'id', 'heat_number', 'grm_receipt', 'raw_material', 'raw_material_details',
            'coils_received', 'total_weight_kg', 'sheets_received', 'test_certificate_date',
            'items', 'is_available', 'consumed_quantity_kg', 'available_quantity_kg', 'available_coils',
            'grm_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'grm_receipt', 'is_available', 'consumed_quantity_kg', 'created_at', 'updated_at', 'available_quantity_kg', 'available_coils']
    
    def get_available_quantity_kg(self, obj):
        """Get remaining available quantity in KG"""
        return float(obj.get_available_quantity_kg())
    
    def get_available_coils(self, obj):
        """Get remaining available coils"""
        return obj.get_available_coils()
    
    def validate(self, data):
        """Validate heat number data"""
        raw_material = data.get('raw_material')
        coils_received = data.get('coils_received', 0)
        sheets_received = data.get('sheets_received', 0)
        total_weight_kg = data.get('total_weight_kg')
        
        # Validate total weight
        if total_weight_kg is None or total_weight_kg <= 0:
            raise serializers.ValidationError({
                'total_weight_kg': 'Total weight must be greater than 0'
            })
        
        # Check if raw material is provided and validate quantities based on material type
        if raw_material:
            if raw_material.material_type == 'coil':
                if coils_received <= 0:
                    raise serializers.ValidationError({
                        'coils_received': 'Number of coils must be specified for coil materials'
                    })
                if sheets_received > 0:
                    raise serializers.ValidationError({
                        'sheets_received': 'Sheets should not be specified for coil materials'
                    })
            elif raw_material.material_type == 'sheet':
                if sheets_received <= 0:
                    raise serializers.ValidationError({
                        'sheets_received': 'Number of sheets must be specified for sheet materials'
                    })
                if coils_received > 0:
                    raise serializers.ValidationError({
                        'coils_received': 'Coils should not be specified for sheet materials'
                    })
        
        return data


class GRMReceiptSerializer(serializers.ModelSerializer):
    """Serializer for GRM Receipt model"""
    purchase_order_details = serializers.SerializerMethodField()
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)
    quality_check_by_name = serializers.CharField(source='quality_check_by.get_full_name', read_only=True)
    heat_numbers = HeatNumberSerializer(many=True, read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = GRMReceipt
        fields = [
            'id', 'grm_number', 'purchase_order', 'purchase_order_details',
            'truck_number', 'driver_name', 'receipt_date',
            'received_by', 'received_by_name', 'status', 'total_items_received',
            'total_items_expected', 'quality_check_passed',
            'quality_check_by', 'quality_check_by_name', 'quality_check_date',
            'heat_numbers', 'completion_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'grm_number', 'created_at', 'updated_at', 'completion_percentage']
    
    def get_purchase_order_details(self, obj):
        """Get purchase order details"""
        if obj.purchase_order:
            return {
                'po_id': obj.purchase_order.po_id,
                'vendor_name': obj.purchase_order.vendor_name.name if obj.purchase_order.vendor_name else None,
                'expected_date': obj.purchase_order.expected_date,
                'quantity_ordered': obj.purchase_order.quantity_ordered,
                'total_amount': obj.purchase_order.total_amount
            }
        return None
    
    def get_completion_percentage(self, obj):
        """Calculate completion percentage"""
        if obj.total_items_expected == 0:
            return 0
        return (obj.total_items_received / obj.total_items_expected) * 100


class GRMReceiptCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating GRM Receipt"""
    heat_numbers_data = HeatNumberSerializer(many=True, write_only=True)
    
    class Meta:
        model = GRMReceipt
        fields = [
            'purchase_order', 'truck_number', 'driver_name', 'heat_numbers_data'
        ]
    
    def validate(self, data):
        """Validate GRM receipt data"""
        purchase_order = data.get('purchase_order')
        heat_numbers_data = data.get('heat_numbers_data', [])
        
        # Check if GRM already exists for this PO
        if purchase_order and GRMReceipt.objects.filter(purchase_order=purchase_order).exists():
            raise serializers.ValidationError({
                'purchase_order': 'GRM receipt already exists for this Purchase Order'
            })
        
        # Validate heat numbers data
        if not heat_numbers_data:
            raise serializers.ValidationError({
                'heat_numbers_data': 'At least one heat number is required'
            })
        
        # Calculate total weight from heat numbers
        total_weight = 0
        for heat_data in heat_numbers_data:
            weight = heat_data.get('total_weight_kg', 0)
            if weight:
                total_weight += float(weight)
        
        # Set the calculated quantity_received
        data['quantity_received'] = total_weight
        
        return data
    
    def create(self, validated_data):
        """Create GRM receipt with heat numbers"""
        heat_numbers_data = validated_data.pop('heat_numbers_data', [])
        quantity_received = validated_data.pop('quantity_received', None)
        
        # Set received_by from context
        validated_data['received_by'] = self.context['request'].user
        
        # Create GRM receipt
        grm_receipt = GRMReceipt.objects.create(**validated_data)
        
        # Update PO with received quantity
        if quantity_received and grm_receipt.purchase_order:
            grm_receipt.purchase_order.quantity_received = quantity_received
            grm_receipt.purchase_order.save()
        
        # Create heat numbers
        for i, heat_data in enumerate(heat_numbers_data):
            try:
                HeatNumber.objects.create(grm_receipt=grm_receipt, **heat_data)
            except Exception as e:
                raise e
        
        # Update completion status
        grm_receipt.total_items_received = len(heat_numbers_data)
        grm_receipt.total_items_expected = quantity_received or 0
        grm_receipt.save()
        
        return grm_receipt


class RMStockBalanceHeatSerializer(serializers.ModelSerializer):
    """Enhanced stock balance serializer with heat number tracking"""
    raw_material_details = RawMaterialBasicSerializer(source='raw_material', read_only=True)
    heat_numbers_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = RMStockBalanceHeat
        fields = [
            'id', 'raw_material', 'raw_material_details', 'total_available_quantity_kg',
            'total_coils_available', 'total_sheets_available', 'active_heat_numbers_count',
            'heat_numbers_summary', 'last_updated'
        ]
        read_only_fields = fields
    
    def get_heat_numbers_summary(self, obj):
        """Get summary of heat numbers for this raw material"""
        heat_numbers = HeatNumber.objects.filter(
            raw_material=obj.raw_material,
            is_available=True
        ).order_by('-created_at')[:5]  # Get latest 5 heat numbers
        
        return [
            {
                'heat_number': heat.heat_number,
                'grm_number': heat.grm_receipt.grm_number,
                'available_quantity_kg': float(heat.get_available_quantity_kg()),
                'coils_available': heat.get_available_coils(),
                'created_at': heat.created_at
            }
            for heat in heat_numbers
        ]


class InventoryTransactionHeatSerializer(serializers.ModelSerializer):
    """Serializer for heat-tracked inventory transactions"""
    heat_number_details = HeatNumberSerializer(source='heat_number', read_only=True)
    transaction_details = InventoryTransactionSerializer(source='inventory_transaction', read_only=True)
    
    class Meta:
        model = InventoryTransactionHeat
        fields = [
            'id', 'inventory_transaction', 'transaction_details', 'heat_number',
            'heat_number_details', 'quantity_kg', 'coils_count', 'sheets_count',
            'grm_number'
        ]
        read_only_fields = ['id']


class GRMReceiptListSerializer(serializers.ModelSerializer):
    """Simplified serializer for GRM receipt list view"""
    purchase_order_po_id = serializers.CharField(source='purchase_order.po_id', read_only=True)
    vendor_name = serializers.CharField(source='purchase_order.vendor_name.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)
    heat_numbers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GRMReceipt
        fields = [
            'id', 'grm_number', 'purchase_order_po_id', 'vendor_name',
            'truck_number', 'driver_name', 'status', 'total_items_received',
            'total_items_expected', 'received_by_name', 'receipt_date',
            'heat_numbers_count', 'quality_check_passed'
        ]
    
    def get_heat_numbers_count(self, obj):
        """Get count of heat numbers in this GRM"""
        return obj.heat_numbers.count()
