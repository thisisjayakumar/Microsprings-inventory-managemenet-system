from django.contrib import admin
from .models import Machine, MachineSchedule


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('machine_id', 'name', 'machine_type', 'status', 'location', 'is_active')
    list_filter = ('status', 'machine_type', 'is_active')
    search_fields = ('machine_id', 'name', 'location')
    filter_horizontal = ('supported_processes',)


@admin.register(MachineSchedule)
class MachineScheduleAdmin(admin.ModelAdmin):
    list_display = ('machine', 'batch_process', 'scheduled_start', 'scheduled_end', 'status')
    list_filter = ('status', 'scheduled_start')
    search_fields = ('machine__machine_id', 'batch_process__batch__batch_id')