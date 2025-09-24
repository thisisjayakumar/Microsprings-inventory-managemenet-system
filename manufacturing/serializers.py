from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory
from products.models import Product
from inventory.models import RawMaterial
from third_party.models import Vendor

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class ProductBasicSerializer(serializers.ModelSerializer):
    """Basic product serializer for nested relationships"""
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'part_number', 'part_name', 'product_type', 
            'product_type_display', 'material_type', 'material_type_display',
            'material_name', 'grade', 'wire_diameter_mm', 'thickness_mm', 
            'finishing', 'manufacturer_brand', 'rm_consumption_per_unit'
        ]
        read_only_fields = fields


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.CharField(source='get_material_name_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'product_code', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'weight_kg', 'thickness_mm', 'quantity'
        ]
        read_only_fields = fields


class VendorBasicSerializer(serializers.ModelSerializer):
    """Basic vendor serializer for nested relationships"""
    vendor_type_display = serializers.CharField(source='get_vendor_type_display', read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'vendor_type', 'vendor_type_display', 'gst_no',
            'address', 'contact_no', 'email', 'contact_person', 'is_active'
        ]
        read_only_fields = fields


class MOStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for MO status history"""
    changed_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = MOStatusHistory
        fields = ['id', 'from_status', 'to_status', 'changed_by', 'changed_at', 'notes']
        read_only_fields = fields


class POStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for PO status history"""
    changed_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = POStatusHistory
        fields = ['id', 'from_status', 'to_status', 'changed_by', 'changed_at', 'notes']
        read_only_fields = fields


class ManufacturingOrderListSerializer(serializers.ModelSerializer):
    """Optimized serializer for MO list view"""
    product_code = ProductBasicSerializer(read_only=True)
    assigned_supervisor = UserBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    class Meta:
        model = ManufacturingOrder
        fields = [
            'id', 'mo_id', 'date_time', 'product_code', 'quantity', 'status', 
            'status_display', 'priority', 'priority_display', 'shift', 'shift_display',
            'assigned_supervisor', 'planned_start_date', 'planned_end_date',
            'delivery_date', 'created_by', 'created_at'
        ]
        read_only_fields = ['mo_id', 'date_time']


class ManufacturingOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for MO create/update/detail view"""
    product_code = ProductBasicSerializer(read_only=True)
    assigned_supervisor = UserBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    gm_approved_by = UserBasicSerializer(read_only=True)
    rm_allocated_by = UserBasicSerializer(read_only=True)
    status_history = MOStatusHistorySerializer(many=True, read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    # Write-only fields for creation
    product_code_id = serializers.IntegerField(write_only=True)
    assigned_supervisor_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ManufacturingOrder
        fields = [
            'id', 'mo_id', 'date_time', 'product_code', 'product_code_id', 'quantity',
            'product_type', 'material_name', 'material_type', 'grade', 'wire_diameter_mm',
            'thickness_mm', 'finishing', 'manufacturer_brand', 'weight_kg',
            'loose_fg_stock', 'rm_required_kg', 'assigned_supervisor', 'assigned_supervisor_id',
            'shift', 'shift_display', 'planned_start_date', 'planned_end_date',
            'actual_start_date', 'actual_end_date', 'status', 'status_display',
            'priority', 'priority_display', 'customer_order_reference', 'delivery_date',
            'special_instructions', 'submitted_at', 'gm_approved_at', 'gm_approved_by',
            'rm_allocated_at', 'rm_allocated_by', 'created_at', 'created_by',
            'updated_at', 'status_history'
        ]
        read_only_fields = [
            'mo_id', 'date_time', 'product_type', 'material_name', 'material_type',
            'grade', 'wire_diameter_mm', 'thickness_mm', 'finishing', 'manufacturer_brand',
            'weight_kg', 'submitted_at', 'gm_approved_at', 'gm_approved_by',
            'rm_allocated_at', 'rm_allocated_by', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Create MO with auto-population of product details"""
        product_code_id = validated_data.pop('product_code_id')
        assigned_supervisor_id = validated_data.pop('assigned_supervisor_id')
        
        try:
            product = Product.objects.get(id=product_code_id)
            supervisor = User.objects.get(id=assigned_supervisor_id)
        except (Product.DoesNotExist, User.DoesNotExist) as e:
            raise serializers.ValidationError(f"Invalid reference: {str(e)}")
        
        # Auto-populate product details
        validated_data.update({
            'product_code': product,
            'assigned_supervisor': supervisor,
            'product_type': product.get_product_type_display() if product.product_type else '',
            'material_name': product.material_name,
            'material_type': product.material_type,
            'grade': product.grade,
            'wire_diameter_mm': product.wire_diameter_mm,
            'thickness_mm': product.thickness_mm,
            'finishing': product.finishing,
            'manufacturer_brand': product.manufacturer_brand,
            'created_by': self.context['request'].user
        })
        
        # Calculate RM required (quantity * rm_consumption_per_unit)
        if product.rm_consumption_per_unit:
            validated_data['rm_required_kg'] = validated_data['quantity'] * product.rm_consumption_per_unit
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update MO with status change tracking"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Handle product change
        if 'product_code_id' in validated_data:
            product_code_id = validated_data.pop('product_code_id')
            try:
                product = Product.objects.get(id=product_code_id)
                validated_data['product_code'] = product
                # Re-populate product details if product changed
                validated_data.update({
                    'product_type': product.get_product_type_display() if product.product_type else '',
                    'material_name': product.material_name,
                    'material_type': product.material_type,
                    'grade': product.grade,
                    'wire_diameter_mm': product.wire_diameter_mm,
                    'thickness_mm': product.thickness_mm,
                    'finishing': product.finishing,
                    'manufacturer_brand': product.manufacturer_brand,
                })
            except Product.DoesNotExist:
                raise serializers.ValidationError("Invalid product reference")
        
        # Handle supervisor change
        if 'assigned_supervisor_id' in validated_data:
            supervisor_id = validated_data.pop('assigned_supervisor_id')
            try:
                supervisor = User.objects.get(id=supervisor_id)
                validated_data['assigned_supervisor'] = supervisor
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid supervisor reference")
        
        instance = super().update(instance, validated_data)
        
        # Create status history if status changed
        if old_status != new_status:
            MOStatusHistory.objects.create(
                mo=instance,
                from_status=old_status,
                to_status=new_status,
                changed_by=self.context['request'].user,
                notes=f"Status changed via API"
            )
        
        return instance


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Optimized serializer for PO list view"""
    rm_code = RawMaterialBasicSerializer(read_only=True)
    vendor_name = VendorBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_id', 'date_time', 'rm_code', 'vendor_name', 'quantity_ordered',
            'unit_price', 'total_amount', 'status', 'status_display', 'material_type',
            'material_type_display', 'expected_date', 'created_by', 'created_at'
        ]
        read_only_fields = ['po_id', 'date_time', 'total_amount']


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for PO create/update/detail view"""
    rm_code = RawMaterialBasicSerializer(read_only=True)
    vendor_name = VendorBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    gm_approved_by = UserBasicSerializer(read_only=True)
    po_created_by = UserBasicSerializer(read_only=True)
    rejected_by = UserBasicSerializer(read_only=True)
    status_history = POStatusHistorySerializer(many=True, read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    # Write-only fields for creation
    rm_code_id = serializers.IntegerField(write_only=True)
    vendor_name_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_id', 'date_time', 'rm_code', 'rm_code_id', 'material_type',
            'material_type_display', 'material_auto', 'grade_auto', 'wire_diameter_mm_auto',
            'thickness_mm_auto', 'finishing_auto', 'manufacturer_brand_auto', 'kg_auto',
            'sheet_roll_auto', 'qty_sheets_auto', 'vendor_name', 'vendor_name_id',
            'vendor_address_auto', 'gst_no_auto', 'mob_no_auto', 'expected_date',
            'quantity_ordered', 'unit_price', 'total_amount', 'status', 'status_display',
            'submitted_at', 'gm_approved_at', 'gm_approved_by', 'po_created_at',
            'po_created_by', 'rejected_at', 'rejected_by', 'rejection_reason',
            'terms_conditions', 'notes', 'created_at', 'created_by', 'updated_at',
            'status_history'
        ]
        read_only_fields = [
            'po_id', 'date_time', 'material_type', 'material_auto', 'grade_auto',
            'wire_diameter_mm_auto', 'thickness_mm_auto', 'finishing_auto',
            'manufacturer_brand_auto', 'kg_auto', 'sheet_roll_auto', 'qty_sheets_auto',
            'vendor_address_auto', 'gst_no_auto', 'mob_no_auto', 'total_amount',
            'submitted_at', 'gm_approved_at', 'gm_approved_by', 'po_created_at',
            'po_created_by', 'rejected_at', 'rejected_by', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Create PO with auto-population of material and vendor details"""
        rm_code_id = validated_data.pop('rm_code_id')
        vendor_name_id = validated_data.pop('vendor_name_id')
        
        try:
            rm_code = RawMaterial.objects.get(id=rm_code_id)
            vendor = Vendor.objects.get(id=vendor_name_id)
        except (RawMaterial.DoesNotExist, Vendor.DoesNotExist) as e:
            raise serializers.ValidationError(f"Invalid reference: {str(e)}")
        
        validated_data.update({
            'rm_code': rm_code,
            'vendor_name': vendor,
            'created_by': self.context['request'].user
        })
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update PO with status change tracking"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Handle rm_code change
        if 'rm_code_id' in validated_data:
            rm_code_id = validated_data.pop('rm_code_id')
            try:
                rm_code = RawMaterial.objects.get(id=rm_code_id)
                validated_data['rm_code'] = rm_code
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError("Invalid raw material reference")
        
        # Handle vendor change
        if 'vendor_name_id' in validated_data:
            vendor_id = validated_data.pop('vendor_name_id')
            try:
                vendor = Vendor.objects.get(id=vendor_id)
                validated_data['vendor_name'] = vendor
            except Vendor.DoesNotExist:
                raise serializers.ValidationError("Invalid vendor reference")
        
        instance = super().update(instance, validated_data)
        
        # Create status history if status changed
        if old_status != new_status:
            POStatusHistory.objects.create(
                po=instance,
                from_status=old_status,
                to_status=new_status,
                changed_by=self.context['request'].user,
                notes=f"Status changed via API"
            )
        
        return instance


# Utility serializers for dropdown/select options
class ProductDropdownSerializer(serializers.ModelSerializer):
    """Serializer for product dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'product_code', 'part_number', 'part_name', 'display_name', 'is_active']
    
    def get_display_name(self, obj):
        if obj.part_number and obj.part_name:
            return f"{obj.part_number} - {obj.part_name}"
        return obj.product_code


class RawMaterialDropdownSerializer(serializers.ModelSerializer):
    """Serializer for raw material dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = ['id', 'product_code', 'material_name', 'material_type', 'grade', 'display_name']
    
    def get_display_name(self, obj):
        return str(obj)  # Uses the __str__ method from the model


class VendorDropdownSerializer(serializers.ModelSerializer):
    """Serializer for vendor dropdown options"""
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'vendor_type', 'is_active']


class UserDropdownSerializer(serializers.ModelSerializer):
    """Serializer for user dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'display_name']
    
    def get_display_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.email
