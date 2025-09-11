from django.contrib import admin
from .models import ProcessTemplate, ProcessStep, ProcessStepDependency, ProductProcessMapping


@admin.register(ProcessTemplate)
class ProcessTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    filter_horizontal = ('material_types',)


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ('template', 'sequence_order', 'step_name', 'is_mandatory', 'machine_required')
    list_filter = ('template', 'is_mandatory', 'machine_required', 'operator_required')
    search_fields = ('step_name', 'template__name')
    ordering = ('template', 'sequence_order')


@admin.register(ProcessStepDependency)
class ProcessStepDependencyAdmin(admin.ModelAdmin):
    list_display = ('step', 'depends_on', 'dependency_type')
    list_filter = ('dependency_type',)
    search_fields = ('step__step_name', 'depends_on__step_name')


@admin.register(ProductProcessMapping)
class ProductProcessMappingAdmin(admin.ModelAdmin):
    list_display = ('product', 'process_template', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__part_number', 'process_template__name')