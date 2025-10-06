from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'product_type', 'spring_type','internal_product_code', 'get_customer_info', 'get_material_info', 'get_material_type', 'created_at', 'created_by')
    list_filter = ('product_type', 'spring_type', 'customer_c_id__name', 'customer_c_id__industry_type', 'material__material_type', 'material__material_name', 'created_at')
    search_fields = ('product_code', 'internal_product_code', 'customer_c_id__name', 'customer_c_id__c_id', 'material__material_code', 'material__grade')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'get_material_details')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_code', 'internal_product_code', 'product_type', 'spring_type', 'customer_c_id', 'material')
        }),
        ('Product Specifications', {
            'fields': ('grams_per_product', 'length_mm', 'breadth_mm'),
            'classes': ('collapse',),
            'description': 'Product-specific measurements and specifications.'
        }),
        ('Sheet Calculation (Press Components)', {
            'fields': (
                ('whole_sheet_length_mm', 'whole_sheet_breadth_mm'),
                ('strip_length_mm', 'strip_breadth_mm'),
                ('strips_per_sheet', 'pcs_per_strip')
            ),
            'classes': ('collapse',),
            'description': 'Sheet calculation data for RM ordering. strips_per_sheet = how many strips from one sheet.'
        }),
        ('Material Details (Read-only)', {
            'fields': ('get_material_details',),
            'classes': ('collapse',),
            'description': 'Material details are automatically populated from the selected raw material.'
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_info(self, obj):
        if obj.customer_c_id:
            return f"{obj.customer_c_id.c_id} - {obj.customer_c_id.name}"
        return "No customer assigned"
    get_customer_info.short_description = 'Customer'
    
    def get_material_info(self, obj):
        if obj.material:
            return f"{obj.material.material_code} - {obj.material.grade}"
        return "No material assigned"
    get_material_info.short_description = 'Material'
    
    def get_material_type(self, obj):
        return obj.material_type_display or "N/A"
    get_material_type.short_description = 'Material Type'
    
    def get_material_details(self, obj):
        if not obj.material:
            return "No material assigned"
        
        details = []
        details.append(f"Material Code: {obj.material.material_code}")
        details.append(f"Material Name: {obj.material_name}")
        details.append(f"Material Type: {obj.material_type_display}")
        details.append(f"Grade: {obj.grade}")
        
        if obj.wire_diameter_mm:
            details.append(f"Wire Diameter: {obj.wire_diameter_mm} mm")
        if obj.thickness_mm:
            details.append(f"Thickness: {obj.thickness_mm} mm")
        if obj.finishing:
            details.append(f"Finishing: {obj.finishing}")
        if obj.weight_kg:
            details.append(f"Weight: {obj.weight_kg} kg")
            
        return "\n".join(details)
    get_material_details.short_description = 'Material Details'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "material":
            # Order materials by material name and grade for easier selection
            kwargs["queryset"] = db_field.related_model.objects.order_by('material_name', 'grade', 'material_code')
        elif db_field.name == "customer_c_id":
            # Order customers by customer ID for easier selection
            kwargs["queryset"] = db_field.related_model.objects.order_by('c_id', 'name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)