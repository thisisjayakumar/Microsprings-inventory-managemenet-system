from django.contrib import admin
from .models import DispatchBatch, DispatchTransaction, FGStockAlert, DispatchOrder


@admin.register(DispatchBatch)
class DispatchBatchAdmin(admin.ModelAdmin):
    list_display = [
        'batch_id', 'mo', 'product_code', 'quantity_produced', 
        'quantity_packed', 'quantity_dispatched', 'quantity_available', 
        'status', 'packing_date', 'location_in_store'
    ]
    list_filter = [
        'status', 'product_code', 'mo__customer_c_id', 
        'packing_date', 'created_at'
    ]
    search_fields = [
        'batch_id', 'mo__mo_id', 'product_code__product_code',
        'location_in_store'
    ]
    readonly_fields = ['batch_id', 'quantity_available', 'dispatch_percentage']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('batch_id', 'mo', 'production_batch', 'product_code')
        }),
        ('Quantities', {
            'fields': ('quantity_produced', 'quantity_packed', 'quantity_dispatched', 
                     'loose_stock', 'quantity_available', 'dispatch_percentage')
        }),
        ('Status & Location', {
            'fields': ('status', 'location_in_store', 'packing_date', 'packing_supervisor')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(DispatchTransaction)
class DispatchTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'mo', 'customer_c_id', 'quantity_dispatched',
        'dispatch_date', 'supervisor_id', 'status', 'confirmed_at'
    ]
    list_filter = [
        'status', 'dispatch_date', 'supervisor_id', 
        'customer_c_id', 'mo__product_code'
    ]
    search_fields = [
        'transaction_id', 'mo__mo_id', 'customer_c_id__name',
        'delivery_reference', 'notes'
    ]
    readonly_fields = ['transaction_id', 'dispatch_date']
    ordering = ['-dispatch_date']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_id', 'mo', 'dispatch_batch', 'customer_c_id')
        }),
        ('Dispatch Information', {
            'fields': ('quantity_dispatched', 'dispatch_date', 'supervisor_id', 
                     'delivery_reference', 'notes')
        }),
        ('Status & Confirmation', {
            'fields': ('status', 'confirmed_at', 'received_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(FGStockAlert)
class FGStockAlertAdmin(admin.ModelAdmin):
    list_display = [
        'product_code', 'alert_type', 'severity', 'is_active',
        'min_stock_level', 'max_stock_level', 'last_triggered'
    ]
    list_filter = [
        'alert_type', 'severity', 'is_active', 'product_code'
    ]
    search_fields = [
        'product_code__product_code', 'description'
    ]
    ordering = ['product_code', 'alert_type']
    
    fieldsets = (
        ('Alert Configuration', {
            'fields': ('product_code', 'alert_type', 'severity', 'is_active')
        }),
        ('Thresholds', {
            'fields': ('min_stock_level', 'max_stock_level', 'expiry_days_threshold')
        }),
        ('Status & Tracking', {
            'fields': ('last_triggered', 'last_alerted', 'description')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(DispatchOrder)
class DispatchOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'mo', 'customer_c_id', 'total_quantity_ordered',
        'total_quantity_dispatched', 'remaining_quantity', 'dispatch_percentage',
        'status', 'dispatch_date'
    ]
    list_filter = [
        'status', 'dispatch_date', 'customer_c_id', 'mo__product_code'
    ]
    search_fields = [
        'order_id', 'mo__mo_id', 'customer_c_id__name',
        'special_instructions', 'delivery_address'
    ]
    readonly_fields = ['order_id', 'remaining_quantity', 'dispatch_percentage']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Details', {
            'fields': ('order_id', 'mo', 'customer_c_id')
        }),
        ('Quantities', {
            'fields': ('total_quantity_ordered', 'total_quantity_dispatched', 
                     'remaining_quantity', 'dispatch_percentage')
        }),
        ('Dispatch Information', {
            'fields': ('status', 'dispatch_date', 'special_instructions', 'delivery_address')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
