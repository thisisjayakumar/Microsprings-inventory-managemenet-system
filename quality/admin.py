from django.contrib import admin
from .models import QualityCheckTemplate, QualityCheck, TraceabilityRecord


@admin.register(QualityCheckTemplate)
class QualityCheckTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'process_step', 'is_mandatory')
    list_filter = ('is_mandatory', 'process_step')
    search_fields = ('name', 'process_step__step_name')


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ('batch_process', 'template', 'overall_result', 'inspector', 'check_datetime')
    list_filter = ('overall_result', 'check_datetime', 'template')
    search_fields = ('batch_process__batch__batch_id', 'template__name', 'inspector__email')
    ordering = ('-check_datetime',)


@admin.register(TraceabilityRecord)
class TraceabilityRecordAdmin(admin.ModelAdmin):
    list_display = ('batch', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('batch__batch_id',)
    ordering = ('-created_at',)