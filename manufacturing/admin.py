from django.contrib import admin
from .models import ManufacturingOrder, Batch, BatchProcessExecution


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = ('mo_id', 'product', 'quantity_ordered', 'status', 'priority', 'assigned_supervisor', 'created_at')
    list_filter = ('status', 'priority', 'shift', 'created_at')
    search_fields = ('mo_id', 'product__part_number', 'customer_order_reference')
    ordering = ('-created_at',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_id', 'mo', 'planned_quantity', 'actual_quantity_started', 'status', 'current_process_step')
    list_filter = ('status', 'created_at')
    search_fields = ('batch_id', 'mo__mo_id')
    ordering = ('-created_at',)


@admin.register(BatchProcessExecution)
class BatchProcessExecutionAdmin(admin.ModelAdmin):
    list_display = ('batch', 'process_step', 'assigned_operator', 'assigned_machine', 'status', 'start_datetime')
    list_filter = ('status', 'process_step', 'start_datetime')
    search_fields = ('batch__batch_id', 'process_step__step_name', 'assigned_operator__email')
    ordering = ('-start_datetime',)