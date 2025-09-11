from django.contrib import admin
from .models import Location, InventoryTransaction, StockBalance


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'location_type', 'parent_location', 'is_active')
    list_filter = ('location_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'transaction_type', 'product', 'quantity', 'location_from', 'location_to', 'transaction_datetime')
    list_filter = ('transaction_type', 'transaction_datetime', 'reference_type')
    search_fields = ('transaction_id', 'product__part_number', 'reference_id')
    ordering = ('-transaction_datetime',)


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'location', 'batch', 'current_quantity', 'reserved_quantity', 'available_quantity', 'last_updated')
    list_filter = ('location', 'last_updated')
    search_fields = ('product__part_number', 'location__code')
    ordering = ('-last_updated',)