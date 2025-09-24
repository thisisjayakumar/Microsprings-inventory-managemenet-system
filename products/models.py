from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Product(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ('coil', 'Spring Coil'),
        ('sheet', 'Spring Sheet')
    ]
    
    PRODUCT_TYPE_CHOICES = [
        ('spring', 'Spring'),
        ('stamping_part', 'Stamping Part')
    ]
    
    product_code = models.CharField(max_length=100, unique=True)
    part_number = models.CharField(max_length=100, blank=True, help_text="Part number for identification")
    part_name = models.CharField(max_length=200, blank=True, help_text="Descriptive name of the part")
    
    # Product specifications
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='spring')
    material_type = models.CharField(max_length=10, choices=MATERIAL_TYPE_CHOICES)
    material_name = models.CharField(max_length=100, blank=True, help_text="Material name/type")
    grade = models.CharField(max_length=50, blank=True, help_text="Material grade")
    
    # Material specifications (conditional based on type)
    wire_diameter_mm = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Wire diameter for coil materials"
    )
    thickness_mm = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Thickness for sheet materials"
    )
    finishing = models.CharField(max_length=100, blank=True, help_text="Surface finishing")
    manufacturer_brand = models.CharField(max_length=100, blank=True, help_text="Manufacturer/Brand")
    
    # BOM and costing
    rm_consumption_per_unit = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        help_text="Raw material consumption per unit (kg)"
    )
    standard_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Standard cost per unit"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        if self.part_number and self.part_name:
            return f"{self.part_number} - {self.part_name}"
        return f"{self.product_code}"
