from django.contrib import admin
from .models import PackagingType, PackedItem, DispatchOrder


@admin.register(PackagingType)
class PackagingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'standard_quantity', 'packaging_material_cost')
    search_fields = ('name',)
    filter_horizontal = ('applicable_products',)


@admin.register(PackedItem)
class PackedItemAdmin(admin.ModelAdmin):
    list_display = ('package_id', 'manufacturing_order', 'packaging_type', 'quantity', 'status', 'pack_datetime')
    list_filter = ('status', 'pack_datetime', 'packaging_type')
    search_fields = ('package_id', 'manufacturing_order__mo_id')
    ordering = ('-pack_datetime',)


@admin.register(DispatchOrder)
class DispatchOrderAdmin(admin.ModelAdmin):
    list_display = ('dispatch_id', 'mo', 'customer_name', 'dispatch_datetime', 'dispatched_by')
    list_filter = ('dispatch_datetime',)
    search_fields = ('dispatch_id', 'customer_name', 'mo__mo_id')
    filter_horizontal = ('packed_items',)
    ordering = ('-dispatch_datetime',)