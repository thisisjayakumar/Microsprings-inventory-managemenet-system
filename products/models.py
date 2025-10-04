from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('spring', 'Spring'),
        ('press_component', 'PRESS COMPONENT')
    ]
    
    SPRING_TYPE_CHOICES = [
        ('tension', 'TENSION SPRING'),
        ('wire_form', 'WIRE FORM SPRING'),
        ('compression', 'COMPRESSION SPRING'),
        ('torsion', 'TORSION SPRING'),
        ('clip', 'CLIP'),
        ('rivet', 'RIVET'),
        ('helical', 'HELICAL SPRING'),
        ('length_pin', 'LENGTH PIN'),
        ('length_rod', 'LENGTH ROD'),
        ('double_torsion', 'DOUBLE TORSION SPRING'),
        ('cotter_pin', 'COTTER PIN'),
        ('conical', 'CONICAL SPRING'),
        ('ring', 'RING'),
        ('s-spring', 'S-SPRING'),
    ]

    product_code = models.CharField(max_length=120, unique=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='spring')
    spring_type = models.CharField(max_length=20, choices=SPRING_TYPE_CHOICES, default='tension')
    
    # Foreign key to RawMaterial for material details
    material = models.ForeignKey(
        'inventory.RawMaterial', 
        on_delete=models.PROTECT, 
        related_name='products',
        help_text="Raw material used for this product"
    )
    
    # Foreign key to Customer using c_id field for customer relationship
    customer_c_id = models.ForeignKey(
        'third_party.Customer',
        to_field='c_id',
        on_delete=models.PROTECT,
        related_name='products',
        help_text="Customer associated with this product (references c_id)",
        null=True,
        blank=True
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')
    updated_at = models.DateTimeField(auto_now=True)
    internal_product_code = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        customer_info = f" ({self.customer_c_id.c_id})" if self.customer_c_id else ""
        return f"{self.product_code}{customer_info}"
    
    # Properties to access material details
    @property
    def material_type(self):
        return self.material.material_type if self.material else None
    
    @property
    def material_name(self):
        return self.material.material_name if self.material else None
    
    @property
    def grade(self):
        return self.material.grade if self.material else None
    
    @property
    def wire_diameter_mm(self):
        return self.material.wire_diameter_mm if self.material else None
    
    @property
    def thickness_mm(self):
        return self.material.thickness_mm if self.material else None
    
    @property
    def finishing(self):
        return self.material.get_finishing_display() if self.material else None
    
    @property
    def weight_kg(self):
        return self.material.weight_kg if self.material else None
    
    @property
    def material_type_display(self):
        return self.material.get_material_type_display() if self.material else None
    
    # Properties to access customer details
    @property
    def customer_name(self):
        return self.customer_c_id.name if self.customer_c_id else None
    
    @property
    def customer_id(self):
        return self.customer_c_id.c_id if self.customer_c_id else None
    
    @property
    def customer_industry(self):
        return self.customer_c_id.get_industry_type_display() if self.customer_c_id else None
    
    def get_product_type_display(self):
        return dict(self.PRODUCT_TYPE_CHOICES).get(self.product_type, self.product_type)

