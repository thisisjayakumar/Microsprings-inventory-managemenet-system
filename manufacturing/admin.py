from django.contrib import admin
from .models import ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory, Batch


# Inline for displaying batches within Manufacturing Order admin
class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    readonly_fields = ('batch_id', 'completion_percentage_display', 'remaining_quantity_display')
    fields = ('batch_id', 'product_code', 'planned_quantity', 'actual_quantity_completed', 
             'status', 'assigned_operator', 'completion_percentage_display')
    
    def completion_percentage_display(self, obj):
        """Safe display of completion percentage"""
        if obj.pk:  # Only for existing objects
            return f"{obj.completion_percentage:.1f}%"
        return "-"
    completion_percentage_display.short_description = 'Completion %'
    
    def remaining_quantity_display(self, obj):
        """Safe display of remaining quantity"""
        if obj.pk:  # Only for existing objects
            return obj.remaining_quantity
        return "-"
    remaining_quantity_display.short_description = 'Remaining Qty'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product_code', 'assigned_operator')


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = ('mo_id', 'product_code', 'customer_display', 'quantity', 'status', 'priority', 'assigned_supervisor', 'created_at')
    list_filter = ('status', 'priority', 'shift', 'material_type', 'product_code__customer_c_id__industry_type', 'created_at')
    search_fields = ('mo_id', 'product_code__product_code', 'product_code__customer_c_id__name', 'product_code__customer_c_id__c_id', 'customer_name')
    readonly_fields = ('mo_id', 'date_time', 'product_type', 'material_name', 'material_type', 'grade', 
                      'wire_diameter_mm', 'thickness_mm', 'finishing', 'manufacturer_brand', 'weight_kg', 
                      'customer_name', 'strips_required', 'total_pieces_from_strips', 'excess_pieces')
    ordering = ('-created_at',)
    inlines = [BatchInline]
    
    def customer_display(self, obj):
        """Display customer information in list view"""
        # Check product's customer first, then MO's direct customer
        if obj.product_code and obj.product_code.customer_c_id:
            return f"{obj.product_code.customer_c_id.c_id} - {obj.product_code.customer_c_id.name}"
        elif obj.customer_c_id:
            return f"{obj.customer_c_id.c_id} - {obj.customer_c_id.name}"
        return obj.customer_name or "No customer"
    customer_display.short_description = 'Customer'
    customer_display.admin_order_field = 'product_code__customer_c_id__name'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance"""
        return super().get_queryset(request).select_related(
            'product_code', 'assigned_supervisor', 'product_code__customer_c_id', 'customer_c_id', 'created_by'
        )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('mo_id', 'date_time', 'product_code', 'quantity')
        }),
        ('Auto-Populated Product Details', {
            'fields': ('product_type', 'material_name', 'material_type', 'grade', 
                      'wire_diameter_mm', 'thickness_mm', 'finishing', 'manufacturer_brand', 'weight_kg'),
            'classes': ('collapse',)
        }),
        ('Raw Material Requirements', {
            'fields': ('loose_fg_stock', 'rm_required_kg', 'tolerance_percentage', 'scrap_percentage')
        }),
        ('Sheet-based Requirements (Press Components)', {
            'fields': ('strips_required', 'total_pieces_from_strips', 'excess_pieces'),
            'classes': ('collapse',),
            'description': 'Strips required for this MO. Auto-calculated based on pcs_per_strip.'
        }),
        ('Assignment & Planning', {
            'fields': ('assigned_supervisor', 'shift', 'planned_start_date', 'planned_end_date', 
                      'actual_start_date', 'actual_end_date')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Customer & Business Details', {
            'fields': ('customer_c_id', 'customer_name', 'delivery_date', 'special_instructions')
        }),
        ('Workflow Tracking', {
            'fields': ('submitted_at', 'gm_approved_at', 'gm_approved_by', 'rm_allocated_at', 'rm_allocated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_id', 'vendor_name', 'rm_code', 'quantity_ordered', 'status', 'expected_date', 'created_at')
    list_filter = ('status', 'material_type', 'expected_date', 'created_at')
    search_fields = ('po_id', 'vendor_name__name', 'rm_code__product_code')
    readonly_fields = ('po_id', 'date_time', 'material_type', 'material_auto', 'grade_auto', 
                      'wire_diameter_mm_auto', 'thickness_mm_auto', 'finishing_auto', 
                      'manufacturer_brand_auto', 'kg_auto', 'sheet_roll_auto', 'qty_sheets_auto',
                      'vendor_address_auto', 'gst_no_auto', 'mob_no_auto', 'total_amount')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('po_id', 'date_time', 'rm_code', 'quantity_ordered')
        }),
        ('Auto-Populated Material Details', {
            'fields': ('material_type', 'material_auto', 'grade_auto', 'wire_diameter_mm_auto', 
                      'thickness_mm_auto', 'finishing_auto', 'manufacturer_brand_auto', 'kg_auto',
                      'sheet_roll_auto', 'qty_sheets_auto'),
            'classes': ('collapse',)
        }),
        ('Vendor Information', {
            'fields': ('vendor_name', 'vendor_address_auto', 'gst_no_auto', 'mob_no_auto')
        }),
        ('Order Details', {
            'fields': ('expected_date', 'unit_price', 'total_amount')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Workflow Tracking', {
            'fields': ('submitted_at', 'gm_approved_at', 'gm_approved_by', 'po_created_at', 'po_created_by',
                      'rejected_at', 'rejected_by', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('terms_conditions', 'notes'),
            'classes': ('collapse',)
        })
    )


@admin.register(MOStatusHistory)
class MOStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('mo', 'from_status', 'to_status', 'changed_by', 'changed_at')
    list_filter = ('to_status', 'changed_at')
    search_fields = ('mo__mo_id', 'changed_by__email')
    ordering = ('-changed_at',)


@admin.register(POStatusHistory)
class POStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('po', 'from_status', 'to_status', 'changed_by', 'changed_at')
    list_filter = ('to_status', 'changed_at')
    search_fields = ('po__po_id', 'changed_by__email')
    ordering = ('-changed_at',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_id', 'mo', 'product_code', 'planned_quantity', 'actual_quantity_completed', 
                   'status', 'progress_percentage', 'assigned_operator', 'created_at')
    list_filter = ('status', 'mo__status', 'product_code__product_type', 'created_at')
    search_fields = ('batch_id', 'mo__mo_id', 'product_code__product_code', 'product_code__part_name')
    readonly_fields = ('batch_id', 'completion_percentage', 'is_overdue', 'remaining_quantity', 
                      'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('batch_id', 'mo', 'product_code')
        }),
        ('Quantities', {
            'fields': ('planned_quantity', 'actual_quantity_started', 'actual_quantity_completed', 
                      'scrap_quantity', 'completion_percentage', 'remaining_quantity')
        }),
        ('Planning & Timing', {
            'fields': ('planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('Status & Progress', {
            'fields': ('status', 'progress_percentage', 'current_process_step', 'is_overdue')
        }),
        ('Assignment', {
            'fields': ('assigned_operator', 'assigned_supervisor')
        }),
        ('Metrics & Notes', {
            'fields': ('total_processing_time_minutes', 'notes')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Inline display of batches in MO admin
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('mo', 'product_code', 'assigned_operator', 'assigned_supervisor')