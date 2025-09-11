from django.contrib import admin
from .models import MaterialType, ProductCategory, Product, ProductSpecification


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('part_number', 'part_name', 'category', 'material_type', 'grade', 'is_active')
    list_filter = ('category', 'material_type', 'is_active', 'created_at')
    search_fields = ('part_number', 'part_name', 'grade')
    ordering = ('-created_at',)


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'version', 'is_current', 'effective_from')
    list_filter = ('is_current', 'effective_from')
    search_fields = ('product__part_number', 'version')