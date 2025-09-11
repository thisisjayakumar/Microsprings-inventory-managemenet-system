from django.contrib import admin
from .models import ReportTemplate, ScheduledReport


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'is_active', 'created_by')
    list_filter = ('report_type', 'is_active')
    search_fields = ('name', 'description')
    filter_horizontal = ('accessible_roles',)


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'schedule_type', 'is_active', 'last_run', 'next_run')
    list_filter = ('schedule_type', 'is_active', 'last_run')
    search_fields = ('name', 'template__name')
    filter_horizontal = ('recipients',)