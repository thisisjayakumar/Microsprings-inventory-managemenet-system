from django.contrib import admin
from django.utils.html import format_html
from .models import Process, SubProcess, ProcessStep, BOM


class SubProcessInline(admin.TabularInline):
    model = SubProcess
    extra = 0
    fields = ('name', 'description')
    show_change_link = True


class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 0
    fields = ('step_name', 'step_code', 'subprocess', 'sequence_order', 'description')
    ordering = ('sequence_order',)
    show_change_link = True


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'subprocess_count', 'step_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SubProcessInline, ProcessStepInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subprocess_count(self, obj):
        count = obj.subprocesses.count()
        if count > 0:
            return format_html('<span style="color: green;">{}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    subprocess_count.short_description = 'Subprocesses'
    
    def step_count(self, obj):
        count = obj.process_steps.count()
        if count > 0:
            return format_html('<span style="color: blue;">{}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    step_count.short_description = 'Steps'


class ProcessStepInlineForSubProcess(admin.TabularInline):
    model = ProcessStep
    extra = 0
    fields = ('step_name', 'step_code', 'sequence_order', 'description')
    ordering = ('sequence_order',)


@admin.register(SubProcess)
class SubProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'process', 'step_count', 'created_at')
    list_filter = ('process', 'created_at')
    search_fields = ('name', 'process__name', 'description')
    readonly_fields = ('created_at',)
    inlines = [ProcessStepInlineForSubProcess]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('process', 'name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def step_count(self, obj):
        count = obj.process_steps.count()
        if count > 0:
            return format_html('<span style="color: blue;">{}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    step_count.short_description = 'Steps'


class BOMInline(admin.TabularInline):
    model = BOM
    extra = 0
    fields = ('product_code', 'type', 'material', 'is_active')
    show_change_link = True


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ('step_name', 'step_code', 'process', 'subprocess', 'sequence_order', 'bom_count', 'created_at')
    list_filter = ('process', 'subprocess', 'created_at')
    search_fields = ('step_name', 'step_code', 'process__name', 'subprocess__name')
    readonly_fields = ('created_at', 'full_path_display')
    inlines = [BOMInline]
    ordering = ('process', 'sequence_order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('step_name', 'step_code', 'sequence_order')
        }),
        ('Process Hierarchy', {
            'fields': ('process', 'subprocess', 'full_path_display')
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def full_path_display(self, obj):
        if obj.pk:
            return format_html('<strong>{}</strong>', obj.full_path)
        return '-'
    full_path_display.short_description = 'Full Path'
    
    def bom_count(self, obj):
        count = obj.bom_set.count()
        if count > 0:
            return format_html('<span style="color: green;">{}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    bom_count.short_description = 'BOMs'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subprocess":
            # Filter subprocesses based on selected process
            if request.resolver_match.kwargs.get('object_id'):
                try:
                    process_step = ProcessStep.objects.get(pk=request.resolver_match.kwargs['object_id'])
                    kwargs["queryset"] = SubProcess.objects.filter(process=process_step.process)
                except ProcessStep.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'type', 'process_display', 'subprocess_display', 'step_display', 'material', 'is_active', 'created_at')
    list_filter = ('type', 'is_active', 'process_step__process', 'created_at')
    search_fields = ('product_code', 'process_step__step_name', 'process_step__process__name', 'material__material_code', 'material__grade')
    readonly_fields = ('created_at', 'updated_at', 'main_process', 'subprocess')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_code', 'type')
        }),
        ('Process & Materials', {
            'fields': ('process_step', 'material')
        }),
        ('Process Hierarchy (Read-only)', {
            'fields': ('main_process', 'subprocess'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def process_display(self, obj):
        return obj.main_process.name if obj.main_process else '-'
    process_display.short_description = 'Process'
    
    def subprocess_display(self, obj):
        return obj.subprocess.name if obj.subprocess else '-'
    subprocess_display.short_description = 'Subprocess'
    
    def step_display(self, obj):
        return f"{obj.process_step.step_name} (#{obj.process_step.sequence_order})"
    step_display.short_description = 'Step'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "process_step":
            # Order process steps by process and sequence
            kwargs["queryset"] = ProcessStep.objects.select_related('process', 'subprocess').order_by('process__name', 'sequence_order')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)