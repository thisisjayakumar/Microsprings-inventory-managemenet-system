from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MaterialType(models.Model):
    """
    Types of materials (Coil, Sheet, etc.) with flexible properties schema
    """
    name = models.CharField(max_length=50, unique=True)  # 'Coil', 'Sheet', etc.
    properties_schema = models.JSONField(default=dict)  # Define what properties this material type needs
    
    class Meta:
        verbose_name = 'Material Type'
        verbose_name_plural = 'Material Types'

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    """
    Hierarchical product categories
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    """
    Main product model with flexible properties
    """
    UNIT_CHOICES = [
        ('Pcs', 'Pieces'),
        ('Kg', 'Kilograms'),
        ('Meters', 'Meters'),
        ('Liters', 'Liters'),
    ]
    
    part_number = models.CharField(max_length=100, unique=True)
    part_name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    material_type = models.ForeignKey(MaterialType, on_delete=models.PROTECT, related_name='products')
    grade = models.CharField(max_length=50)
    unit_of_measurement = models.CharField(max_length=10, choices=UNIT_CHOICES)
    
    # Dynamic properties based on material type
    properties = models.JSONField(default=dict)  # wire_diameter, thickness, etc.
    
    # Business logic
    is_active = models.BooleanField(default=True)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    standard_pack_size = models.IntegerField(default=1)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.part_number} - {self.part_name}"


class ProductSpecification(models.Model):
    """
    Version-controlled product specifications
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    version = models.CharField(max_length=20)
    specifications = models.JSONField()  # All technical specs
    is_current = models.BooleanField(default=True)
    effective_from = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['product', 'version']
        verbose_name = 'Product Specification'
        verbose_name_plural = 'Product Specifications'

    def __str__(self):
        return f"{self.product.part_number} - v{self.version}"