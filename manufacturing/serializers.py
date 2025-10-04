from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory,
    MOProcessExecution, MOProcessStepExecution, MOProcessAlert
)
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
    material_type_display = serializers.CharField(read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    material_name = serializers.CharField(read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    grade = serializers.CharField(read_only=True)
    wire_diameter_mm = serializers.DecimalField(max_digits=8, decimal_places=3, read_only=True)
    thickness_mm = serializers.DecimalField(max_digits=8, decimal_places=3, read_only=True)
    finishing = serializers.CharField(read_only=True)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    material_type = serializers.CharField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'product_type', 'product_type_display', 
            'material_type', 'material_type_display', 'material_name', 'grade', 
            'wire_diameter_mm', 'thickness_mm', 'finishing', 'weight_kg', 
            'customer_name', 'customer_id'
        ]
        read_only_fields = fields


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.CharField(source='get_material_name_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'weight_kg', 'thickness_mm', 'quantity', 'finishing'
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
    
    # Customer fields
    from third_party.serializers import CustomerListSerializer
    customer = CustomerListSerializer(read_only=True)
    
    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    # Write-only fields for creation
    product_code_id = serializers.IntegerField(write_only=True)
    assigned_supervisor_id = serializers.IntegerField(write_only=True, required=False)
    customer_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ManufacturingOrder
        fields = [
            'id', 'mo_id', 'date_time', 'product_code', 'product_code_id', 'quantity',
            'product_type', 'material_name', 'material_type', 'grade', 'wire_diameter_mm',
            'thickness_mm', 'finishing', 'manufacturer_brand', 'weight_kg',
            'loose_fg_stock', 'rm_required_kg', 'assigned_supervisor', 'assigned_supervisor_id',
            'shift', 'shift_display', 'planned_start_date', 'planned_end_date',
            'actual_start_date', 'actual_end_date', 'status', 'status_display',
            'priority', 'priority_display', 'customer', 'customer_id', 'customer_name', 
            'delivery_date', 'special_instructions', 'submitted_at', 'gm_approved_at', 
            'gm_approved_by', 'rm_allocated_at', 'rm_allocated_by', 'created_at', 
            'created_by', 'updated_at', 'status_history'
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
        assigned_supervisor_id = validated_data.pop('assigned_supervisor_id', None)
        customer_id = validated_data.pop('customer_id', None)
        
        try:
            # Try to get product by ID first (numeric)
            if str(product_code_id).isdigit():
                product = Product.objects.select_related('customer_c_id', 'material').get(id=product_code_id)
            else:
                # If ID is not numeric, treat it as product_code (string)
                product = Product.objects.select_related('customer_c_id', 'material').get(product_code=product_code_id)
        except Product.DoesNotExist:
            # If product doesn't exist, we need to create it or handle it differently
            from processes.models import BOM
            bom_item = BOM.objects.filter(product_code=product_code_id, is_active=True).first()
            if not bom_item:
                raise serializers.ValidationError("Invalid product reference - not found in Product table or BOM")
            
            # Create a new Product record from BOM data
            # First, try to get the material from BOM
            material = bom_item.material
            if not material:
                raise serializers.ValidationError("BOM item has no associated material")
            
            product = Product.objects.create(
                product_code=product_code_id,
                product_type='spring' if bom_item.type == 'spring' else 'stamping_part',
                material=material,
                created_by=self.context['request'].user
            )
        
        # Handle optional supervisor
        supervisor = None
        if assigned_supervisor_id:
            try:
                supervisor = User.objects.get(id=assigned_supervisor_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid supervisor reference")
        
        # Handle optional customer
        customer = None
        if customer_id:
            try:
                from third_party.models import Customer
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                raise serializers.ValidationError("Invalid customer reference")
        
        # Auto-populate product details
        validated_data.update({
            'product_code': product,
            'assigned_supervisor': supervisor,
            'customer': customer,
            'customer_name': customer.name if customer else validated_data.get('customer_name', ''),
            'product_type': product.get_product_type_display() if product.product_type else '',
            'material_name': product.material_name or '',
            'material_type': product.material_type or '',
            'grade': product.grade or '',
            'wire_diameter_mm': product.wire_diameter_mm,
            'thickness_mm': product.thickness_mm,
            'finishing': product.finishing or '',
            'manufacturer_brand': '',  # Not available in new structure
            'weight_kg': product.weight_kg,
            'created_by': self.context['request'].user
        })
        
        # Set default RM required (can be updated later)
        validated_data['rm_required_kg'] = validated_data['quantity'] * 0.001  # Default 1g per unit
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update MO with status change tracking"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Handle product change
        if 'product_code_id' in validated_data:
            product_code_id = validated_data.pop('product_code_id')
            try:
                product = Product.objects.select_related('customer_c_id', 'material').get(id=product_code_id)
                validated_data['product_code'] = product
                # Re-populate product details if product changed
                validated_data.update({
                    'product_type': product.get_product_type_display() if product.product_type else '',
                    'material_name': product.material_name or '',
                    'material_type': product.material_type or '',
                    'grade': product.grade or '',
                    'wire_diameter_mm': product.wire_diameter_mm,
                    'thickness_mm': product.thickness_mm,
                    'finishing': product.finishing or '',
                    'manufacturer_brand': '',  # Not available in new structure
                    'weight_kg': product.weight_kg,
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


# Process Execution Serializers
class MOProcessStepExecutionSerializer(serializers.ModelSerializer):
    """Serializer for process step execution tracking"""
    process_step_name = serializers.CharField(source='process_step.step_name', read_only=True)
    process_step_code = serializers.CharField(source='process_step.step_code', read_only=True)
    process_step_full_path = serializers.CharField(source='process_step.full_path', read_only=True)
    operator_name = serializers.CharField(source='operator.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quality_status_display = serializers.CharField(source='get_quality_status_display', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    efficiency_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = MOProcessStepExecution
        fields = [
            'id', 'process_step', 'process_step_name', 'process_step_code', 
            'process_step_full_path', 'status', 'status_display', 
            'quality_status', 'quality_status_display', 'actual_start_time', 
            'actual_end_time', 'quantity_processed', 'quantity_passed', 
            'quantity_failed', 'scrap_percentage', 'operator', 'operator_name',
            'operator_notes', 'quality_notes', 'duration_minutes', 
            'efficiency_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class MOProcessExecutionListSerializer(serializers.ModelSerializer):
    """Optimized serializer for process execution list view"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    process_code = serializers.IntegerField(source='process.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_operator_name = serializers.CharField(source='assigned_operator.get_full_name', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    step_count = serializers.SerializerMethodField()
    completed_steps = serializers.SerializerMethodField()
    
    class Meta:
        model = MOProcessExecution
        fields = [
            'id', 'process', 'process_name', 'process_code', 'status', 
            'status_display', 'sequence_order', 'planned_start_time', 
            'planned_end_time', 'actual_start_time', 'actual_end_time',
            'assigned_operator', 'assigned_operator_name', 'progress_percentage',
            'duration_minutes', 'is_overdue', 'step_count', 'completed_steps',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_step_count(self, obj):
        return obj.step_executions.count()
    
    def get_completed_steps(self, obj):
        return obj.step_executions.filter(status='completed').count()


class MOProcessExecutionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for process execution with step details"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    process_code = serializers.IntegerField(source='process.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_operator_name = serializers.CharField(source='assigned_operator.get_full_name', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    step_executions = MOProcessStepExecutionSerializer(many=True, read_only=True)
    alerts = serializers.SerializerMethodField()
    
    class Meta:
        model = MOProcessExecution
        fields = [
            'id', 'process', 'process_name', 'process_code', 'status', 
            'status_display', 'sequence_order', 'planned_start_time', 
            'planned_end_time', 'actual_start_time', 'actual_end_time',
            'assigned_operator', 'assigned_operator_name', 'progress_percentage',
            'notes', 'duration_minutes', 'is_overdue', 'step_executions',
            'alerts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_alerts(self, obj):
        from .serializers import MOProcessAlertSerializer
        return MOProcessAlertSerializer(
            obj.alerts.filter(is_resolved=False), many=True
        ).data


class MOProcessAlertSerializer(serializers.ModelSerializer):
    """Serializer for process alerts"""
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True)
    
    class Meta:
        model = MOProcessAlert
        fields = [
            'id', 'alert_type', 'alert_type_display', 'severity', 'severity_display',
            'title', 'description', 'is_resolved', 'resolved_at', 'resolved_by',
            'resolved_by_name', 'resolution_notes', 'created_at', 'created_by',
            'created_by_name'
        ]
        read_only_fields = ['created_at']


class ManufacturingOrderWithProcessesSerializer(serializers.ModelSerializer):
    """Enhanced MO serializer with process execution details"""
    product_code_display = serializers.CharField(source='product_code.display_name', read_only=True)
    product_code_value = serializers.CharField(source='product_code.product_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    assigned_supervisor_name = serializers.CharField(source='assigned_supervisor.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    process_executions = MOProcessExecutionListSerializer(many=True, read_only=True)
    overall_progress = serializers.SerializerMethodField()
    active_process = serializers.SerializerMethodField()
    
    class Meta:
        model = ManufacturingOrder
        fields = [
            'id', 'mo_id', 'date_time', 'product_code', 'product_code_display', 'product_code_value',
            'quantity', 'product_type', 'material_name', 'material_type', 'grade',
            'wire_diameter_mm', 'thickness_mm', 'finishing', 'manufacturer_brand',
            'weight_kg', 'loose_fg_stock', 'rm_required_kg', 'assigned_supervisor',
            'assigned_supervisor_name', 'shift', 'shift_display', 'planned_start_date',
            'planned_end_date', 'actual_start_date', 'actual_end_date', 'status',
            'status_display', 'priority', 'priority_display', 'customer_name',
            'delivery_date', 'special_instructions', 'created_at', 'created_by',
            'created_by_name', 'updated_at', 'process_executions', 'overall_progress',
            'active_process'
        ]
        read_only_fields = ['mo_id', 'date_time', 'created_at', 'updated_at']
    
    def get_overall_progress(self, obj):
        """Calculate overall progress across all processes"""
        executions = obj.process_executions.all()
        if not executions:
            return 0
        
        total_progress = sum(exec.progress_percentage for exec in executions)
        return round(total_progress / len(executions), 2)
    
    def get_active_process(self, obj):
        """Get currently active process"""
        active_exec = obj.process_executions.filter(status='in_progress').first()
        if active_exec:
            return {
                'id': active_exec.id,
                'process_name': active_exec.process.name,
                'progress_percentage': active_exec.progress_percentage,
                'assigned_operator': active_exec.assigned_operator.get_full_name() if active_exec.assigned_operator else None
            }
        return None


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
        fields = ['id', 'product_code', 'display_name']
    
    def get_display_name(self, obj):
        return obj.product_code


class RawMaterialDropdownSerializer(serializers.ModelSerializer):
    """Serializer for raw material dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = ['id', 'material_name', 'material_type', 'grade', 'display_name']
    
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
