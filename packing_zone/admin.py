from django.contrib import admin
from .models import (
    PackingBatch, PackingTransaction, LooseStock, MergedHeatNumber,
    MergeRequest, StockAdjustment, PackingLabel, FGStock
)


@admin.register(PackingBatch)
class PackingBatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'mo_id', 'ipc', 'heat_no', 'ok_quantity_kg', 'status', 'received_date']
    list_filter = ['status', 'received_date']
    search_fields = ['mo_id', 'product_code', 'ipc', 'heat_no']
    readonly_fields = ['received_date', 'verified_date', 'released_date', 'created_at', 'updated_at']


@admin.register(PackingTransaction)
class PackingTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'ipc', 'heat_no', 'actual_packs', 'loose_weight_kg', 'packed_by', 'packed_date']
    list_filter = ['packed_date']
    search_fields = ['product_code', 'ipc', 'heat_no']
    readonly_fields = ['packed_date', 'created_at', 'updated_at']


@admin.register(LooseStock)
class LooseStockAdmin(admin.ModelAdmin):
    list_display = ['id', 'ipc', 'heat_no', 'loose_kg', 'loose_pieces', 'age_days']
    search_fields = ['product_code', 'ipc', 'heat_no']
    readonly_fields = ['first_added_date', 'last_updated']


@admin.register(MergedHeatNumber)
class MergedHeatNumberAdmin(admin.ModelAdmin):
    list_display = ['id', 'merged_heat_no', 'ipc', 'total_merged_kg', 'approved_by', 'approved_date']
    search_fields = ['merged_heat_no', 'product_code', 'ipc']
    readonly_fields = ['approved_date', 'created_at', 'updated_at']


@admin.register(MergeRequest)
class MergeRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'ipc', 'status', 'total_kg', 'requested_by', 'requested_date']
    list_filter = ['status', 'requested_date']
    search_fields = ['product_code', 'ipc']
    readonly_fields = ['requested_date', 'reviewed_date', 'created_at', 'updated_at']


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'ipc', 'heat_no', 'adjustment_kg', 'reason', 'status', 'requested_date']
    list_filter = ['status', 'reason', 'requested_date']
    search_fields = ['product_code', 'ipc', 'heat_no']
    readonly_fields = ['requested_date', 'reviewed_date', 'created_at', 'updated_at']


@admin.register(PackingLabel)
class PackingLabelAdmin(admin.ModelAdmin):
    list_display = ['id', 'label_id', 'ipc', 'heat_no', 'quantity_pcs', 'printed_by', 'printed_date', 'reprint_count']
    search_fields = ['label_id', 'product_code', 'ipc', 'heat_no']
    readonly_fields = ['printed_date', 'last_reprinted', 'created_at', 'updated_at']


@admin.register(FGStock)
class FGStockAdmin(admin.ModelAdmin):
    list_display = ['id', 'ipc', 'heat_no', 'total_packs', 'packing_size', 'last_updated']
    search_fields = ['product_code', 'ipc', 'heat_no']
    readonly_fields = ['last_updated']

