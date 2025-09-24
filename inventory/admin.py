from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import TextInput, Textarea
from .models import RawMaterial, Location, InventoryTransaction, RMStockBalance


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'material_name', 'material_type', 'grade', 'get_specifications', 'created_at')
    list_filter = ('material_name', 'material_type', 'created_at')
    search_fields = ('product_code', 'grade')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product_code', 'material_name', 'material_type', 'grade')
        }),
        ('Coil Specifications', {
            'fields': ('wire_diameter_mm', 'weight_kg'),
            'classes': ('collapse',),
            'description': 'Fill these fields only for Coil type materials'
        }),
        ('Sheet Specifications', {
            'fields': ('thickness_mm', 'quantity'),
            'classes': ('collapse',),
            'description': 'Fill these fields only for Sheet type materials'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
        models.DecimalField: {'widget': TextInput(attrs={'size': '15'})},
    }
    
    def get_specifications(self, obj):
        """Display material specifications in a readable format"""
        specs = []
        if obj.material_type == 'coil':
            if obj.wire_diameter_mm:
                specs.append(f"⌀{obj.wire_diameter_mm}mm")
            if obj.weight_kg:
                specs.append(f"{obj.weight_kg}kg")
        elif obj.material_type == 'sheet':
            if obj.thickness_mm:
                specs.append(f"t{obj.thickness_mm}mm")
            if obj.quantity:
                specs.append(f"{obj.quantity}kg")
        
        return ', '.join(specs) if specs else '-'
    
    get_specifications.short_description = 'Specifications'
    
    class Media:
        js = ('admin/js/collapse.js',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'location_name', 'parent_location', 'get_location_hierarchy')
    list_filter = ('location_name', 'parent_location')
    search_fields = ('code', 'location_name')
    ordering = ('location_name', 'code')
    
    fieldsets = (
        ('Location Details', {
            'fields': ('code', 'location_name', 'parent_location')
        }),
    )
    
    def get_location_hierarchy(self, obj):
        """Show the full location hierarchy"""
        hierarchy = []
        current = obj
        while current:
            hierarchy.insert(0, current.get_location_name_display())
            current = current.parent_location
        return ' → '.join(hierarchy)
    
    get_location_hierarchy.short_description = 'Full Hierarchy'


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'transaction_type', 'product', 'quantity', 
        'location_from', 'location_to', 'transaction_datetime', 'created_by'
    )
    list_filter = (
        'transaction_type', 'reference_type', 'transaction_datetime', 
        'location_from', 'location_to', 'created_by'
    )
    search_fields = ('transaction_id', 'product__product_code', 'reference_id', 'notes')
    ordering = ('-transaction_datetime',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'transaction_datetime'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_id', 'transaction_type', 'transaction_datetime')
        }),
        ('Product & Batch', {
            'fields': ('product', 'batch')
        }),
        ('Location Movement', {
            'fields': ('location_from', 'location_to'),
            'description': 'For transfers, specify both locations. For inward/outward, use appropriate location.'
        }),
        ('Quantity & Value', {
            'fields': ('quantity', 'unit_cost', 'total_value')
        }),
        ('Reference & Tracking', {
            'fields': ('reference_type', 'reference_id', 'idempotency_key'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 60})},
        models.CharField: {'widget': TextInput(attrs={'size': '30'})},
    }
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'batch', 'location_from', 'location_to', 'created_by'
        )


@admin.register(RMStockBalance)
class RMStockBalanceAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'type', 'current_quantity', 'reserved_quantity', 
        'available_quantity', 'get_stock_status', 'last_updated'
    )
    list_filter = ('type', 'last_updated')
    search_fields = ('product__product_code',)
    ordering = ('-last_updated',)
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'type')
        }),
        ('Stock Levels', {
            'fields': ('current_quantity', 'reserved_quantity', 'available_quantity')
        }),
        ('Tracking', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def get_stock_status(self, obj):
        """Visual indicator for stock status"""
        if obj.available_quantity <= 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.available_quantity < 10:  # Assuming low stock threshold
            color = 'orange'
            status = 'Low Stock'
        else:
            color = 'green'
            status = 'In Stock'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    
    get_stock_status.short_description = 'Stock Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


# Custom admin site configuration
admin.site.site_header = "Microsprings Inventory Management"
admin.site.site_title = "MSP Inventory Admin"
admin.site.index_title = "Inventory Management System"