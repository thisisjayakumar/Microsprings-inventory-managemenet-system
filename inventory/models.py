from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class RawMaterial(models.Model):
    MATERIAL_NAME_CHOICES = [
        ('spring', 'Spring Steel'),
        ('stain', 'Stainless Steel'),
        ('ms','Mild Steel'),
    ]
    
    MATERIAL_TYPE_CHOICES = [
        ('coil', 'Coil'),
        ('sheet', 'Sheet'),
    ]

    product_code = models.CharField(max_length=100, unique=True)
    material_name = models.CharField(max_length=20, choices=MATERIAL_NAME_CHOICES)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES)
    grade = models.CharField(max_length=50)
    
    # Conditional fields based on material type
    wire_diameter_mm = models.DecimalField(
        max_digits=8, 
        decimal_places=3, 
        null=True, 
        blank=True,
        help_text="Required if material type is Coil"
    )
    weight_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        null=True, 
        blank=True,
        help_text="Weight in KG for Coil type"
    )
    thickness_mm = models.DecimalField(
        max_digits=8, 
        decimal_places=3, 
        null=True, 
        blank=True,
        help_text="Required if material type is Sheet"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        null=True, 
        blank=True,
        help_text="Quantity for Sheet type kg"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['material_name', 'grade']

    def __str__(self):
        specs = []
        if self.material_type == 'coil':
            if self.wire_diameter_mm:
                specs.append(f"⌀{self.wire_diameter_mm}mm")
            if self.weight_kg:
                specs.append(f"{self.weight_kg}kg")
        elif self.material_type == 'sheet':
            if self.thickness_mm:
                specs.append(f"t{self.thickness_mm}mm")
            if self.quantity:
                specs.append(f"{self.quantity}kg")
        
        spec_str = f" ({', '.join(specs)})" if specs else ""
        material_display = self.get_material_name_display() if self.material_name else "Unknown Material"
        type_display = self.get_material_type_display() if self.material_type else "Unknown Type"
        grade_str = f" {self.grade}" if self.grade else ""
        
        return f"{self.product_code} - {material_display}{grade_str} - {type_display}{spec_str}"

    def clean(self):
        errors = {}

        if self.material_type == 'coil':
            if not self.wire_diameter_mm:
                errors['wire_diameter_mm'] = "Wire diameter is required for Coil type materials"
 
            if self.thickness_mm:
                errors['thickness_mm'] = "Thickness should not be set for Coil type materials"
                
        elif self.material_type == 'sheet':
            if not self.thickness_mm:
                errors['thickness_mm'] = "Thickness is required for Sheet type materials"

            if self.wire_diameter_mm:
                errors['wire_diameter_mm'] = "Wire diameter should not be set for Sheet type materials"
        
        # Validate positive values for numeric fields
        if self.wire_diameter_mm is not None and self.wire_diameter_mm <= 0:
            errors['wire_diameter_mm'] = "Wire diameter must be greater than 0"
            
        if self.weight_kg is not None and self.weight_kg <= 0:
            errors['weight_kg'] = "Weight must be greater than 0"
            
        if self.thickness_mm is not None and self.thickness_mm <= 0:
            errors['thickness_mm'] = "Thickness must be greater than 0"
            
        if self.quantity is not None and self.quantity <= 0:
            errors['quantity'] = "Quantity must be greater than 0"
        
        if errors:
            raise ValidationError(errors)


class Location(models.Model):
    LOCATION_TYPE_CHOICES = [
        ('rm_store', 'Raw Material Store'),
        ('coiling', 'Coiling'),
        ('forming', 'Forming'),
        ('tempering', 'Tempering'),
        ('coating', 'Coating'),
        ('blanking', 'Blanking'),
        ('piercing', 'Piercing'),
        ('deburring', 'Deburring'),
        ('ironing', 'Ironing'),
        ('champering', 'Champering'),
        ('bending', 'Bending'),
        ('plating', 'Plating'),
        ('blue_coating', 'Blue Coating'),
        ('bush_assembly', 'Bush Assembly'),
        ('riveting', 'Riveting'),
        ('remar', 'Remar'),
        ('brass_welding', 'Brass Welding'),
        ('grinding_buffing', 'Grinding & Buffing'),
        ('blacking', 'Blacking'),
        ('phosphating', 'Phosphating'),
        ('final_inspection', 'Final Inspection'),
        ('packing_zone', 'Packing Zone'),
        ('fg', 'FG Store'),
        ('dispatched', 'Dispatched')
    ]
    
    code = models.CharField(max_length=20, unique=True)
    location_name = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES, default='rm_store')
    parent_location = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_locations')

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f"{self.location_name}"


class InventoryTransaction(models.Model):

    TRANSACTION_TYPES = [
        ('inward', 'Inward Receipt'),
        ('outward', 'Outward Issue'),
        ('transfer', 'Location Transfer'),
        ('adjustment', 'Stock Adjustment'),
        ('consumption', 'Process Consumption'),
        ('production', 'Process Output'),
        ('scrap', 'Scrap Generation'),
        ('return', 'Return to Stock')
    ]
    
    REFERENCE_TYPES = [
        ('mo', 'Manufacturing Order'),
        ('po', 'Purchase Order'),
        ('process', 'Process Execution'),
        ('adjustment', 'Stock Adjustment')
    ]
    
    transaction_id = models.CharField(max_length=20, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # What
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='inventory_transactions')
    manufacturing_order = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions')
    
    # Where
    location_from = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name='outgoing_transactions')
    location_to = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name='incoming_transactions')
    
    # How Much
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    idempotency_key = models.CharField(
        max_length=64,
        unique=False,
        null=True,
        blank=True,
        help_text="Idempotency key for safe retries. Ensures no duplicate transaction on retries."
    )

    # When & Who
    transaction_datetime = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_transactions')
    
    # Reference
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES, null=True, blank=True)
    reference_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Additional Info
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['transaction_datetime']),
            models.Index(fields=['product', 'location_to']),
        ]
        verbose_name = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'

    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type}"


class RMStockBalance(models.Model):
    """
    Current stock levels - calculated/cached view
    """
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_balances')
    type = models.CharField(max_length=5, choices=[('coil', 'Coil'), ('sheet', 'Sheet')])
    current_quantity = models.IntegerField()
    reserved_quantity = models.IntegerField()  # Allocated but not consumed
    available_quantity = models.IntegerField()  # current - reserved
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'type', 'available_quantity']
        verbose_name = 'Inventory Stock Balance'
        verbose_name_plural = 'Inventory Stock Balances'

    def __str__(self):
        return f"{self.product.part_number} @ {self.type}: {self.current_quantity}"