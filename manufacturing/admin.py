from django.contrib import admin
from .models import ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = ('mo_id', 'product_code', 'quantity', 'status', 'priority', 'assigned_supervisor', 'created_at')
    list_filter = ('status', 'priority', 'shift', 'material_type', 'created_at')
    search_fields = ('mo_id', 'product_code__product_code', 'customer_order_reference')
    readonly_fields = ('mo_id', 'date_time', 'product_type', 'material_name', 'material_type', 'grade', 
                      'wire_diameter_mm', 'thickness_mm', 'finishing', 'manufacturer_brand', 'weight_kg')
    ordering = ('-created_at',)
    
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
            'fields': ('loose_fg_stock', 'rm_required_kg')
        }),
        ('Assignment & Planning', {
            'fields': ('assigned_supervisor', 'shift', 'planned_start_date', 'planned_end_date', 
                      'actual_start_date', 'actual_end_date')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Business Details', {
            'fields': ('customer_order_reference', 'delivery_date', 'special_instructions')
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