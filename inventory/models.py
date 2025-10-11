from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class RawMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ('coil', 'Coil'),
        ('sheet', 'Sheet'),
    ]

    FINISHING_CHOICES = [
        ('soap_coated', 'Soap Coated'),
        ('bright','BRIGHT'),
    ]
    
    
    material_code = models.CharField(max_length=50, unique=True, help_text="Unique identifier for the raw material")
    material_name = models.CharField(max_length=100, help_text="Complete material name from CSV")
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES)
    grade = models.CharField(max_length=50)
    finishing = models.CharField(max_length=20, choices=FINISHING_CHOICES, null=True, blank=True)
    
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
    
    # Sheet dimensions (for sheet type only)
    length_mm = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Length in mm (for sheet type materials)"
    )
    breadth_mm = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Breadth in mm (for sheet type materials)"
    )
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of sheets (for sheet type materials)"
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
        
        spec_str = f" ({', '.join(specs)})" if specs else ""
        material_display = self.material_name if self.material_name else "Unknown Material"
        type_display = self.get_material_type_display() if self.material_type else "Unknown Type"
        grade_str = f" {self.grade}" if self.grade else ""
        
        return f"{self.material_code} - {material_display}{grade_str} - {type_display}{spec_str}"

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
            
            if self.weight_kg:
                errors['weight_kg'] = "Weight should not be set for Sheet type materials (use quantity instead)"
        
        # Validate positive values for numeric fields
        if self.wire_diameter_mm is not None and self.wire_diameter_mm <= 0:
            errors['wire_diameter_mm'] = "Wire diameter must be greater than 0"
            
        if self.weight_kg is not None and self.weight_kg <= 0:
            errors['weight_kg'] = "Weight must be greater than 0"
            
        if self.thickness_mm is not None and self.thickness_mm <= 0:
            errors['thickness_mm'] = "Thickness must be greater than 0"
            
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


class ProductLocation(models.Model):
    """
    Track current location of products, raw materials, and batches
    """
    # What item
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True, related_name='locations')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, null=True, blank=True, related_name='locations')
    batch = models.ForeignKey('manufacturing.Batch', on_delete=models.CASCADE, null=True, blank=True, related_name='locations')
    
    # Where
    current_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='current_items')
    
    # How much
    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Current quantity at this location")
    
    # Tracking
    last_moved_at = models.DateTimeField(auto_now=True)
    last_moved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Reference to the transaction that created this location record
    last_transaction = models.ForeignKey('InventoryTransaction', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # Ensure each item can only be in one location at a time
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(product__isnull=False, raw_material__isnull=True, batch__isnull=True) |
                    models.Q(product__isnull=True, raw_material__isnull=False, batch__isnull=True) |
                    models.Q(product__isnull=True, raw_material__isnull=True, batch__isnull=False)
                ),
                name='only_one_item_type'
            )
        ]
        indexes = [
            models.Index(fields=['current_location']),
            models.Index(fields=['last_moved_at']),
        ]
        verbose_name = 'Product Location'
        verbose_name_plural = 'Product Locations'

    def __str__(self):
        item_name = ""
        if self.product:
            item_name = f"Product: {self.product.product_code}"
        elif self.raw_material:
            item_name = f"RM: {self.raw_material.material_code}"
        elif self.batch:
            item_name = f"Batch: {self.batch.batch_id}"
        
        return f"{item_name} @ {self.current_location.location_name} ({self.quantity})"

    def get_item_identifier(self):
        """Get a string identifier for the item"""
        if self.product:
            return f"product_{self.product.id}"
        elif self.raw_material:
            return f"raw_material_{self.raw_material.id}"
        elif self.batch:
            return f"batch_{self.batch.id}"
        return "unknown"


class RMStockBalance(models.Model):
    """
    Current stock levels for raw materials
    """
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='stock_balances', null=True, blank=True)
    available_quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Available quantity in KG or pieces")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['raw_material']
        verbose_name = 'RM Stock Balance'
        verbose_name_plural = 'RM Stock Balances'

    def __str__(self):
        return f"{self.raw_material.material_code} - {self.available_quantity}"


class GRMReceipt(models.Model):
    """
    Goods Receipt Material (GRM) - Represents a truck delivery/consignment
    Each GRM can contain multiple raw materials with different heat numbers
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Receipt'),
        ('partial', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    
    # Auto-generated GRM number
    grm_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Related Purchase Order
    purchase_order = models.ForeignKey(
        'manufacturing.PurchaseOrder', 
        on_delete=models.PROTECT, 
        related_name='grm_receipts',
        help_text="Purchase Order this GRM is for"
    )
    
    # Delivery Information
    truck_number = models.CharField(max_length=20, blank=True, help_text="Truck/Van number")
    driver_name = models.CharField(max_length=100, blank=True)
    
    # Receipt Details
    receipt_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='grm_receipts')
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_items_received = models.PositiveIntegerField(default=0)
    total_items_expected = models.PositiveIntegerField(default=0)
    
    # Additional Information
    quality_check_passed = models.BooleanField(default=False)
    quality_check_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quality_checked_grms'
    )
    quality_check_date = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-receipt_date']
        verbose_name = 'GRM Receipt'
        verbose_name_plural = 'GRM Receipts'
        indexes = [
            models.Index(fields=['grm_number']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"GRM-{self.grm_number} - {self.purchase_order.po_id}"
    
    def save(self, *args, **kwargs):
        if not self.grm_number:
            # Generate GRM number: GRM-YYYYMMDD-XXXX
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_grm = GRMReceipt.objects.filter(
                grm_number__startswith=f'GRM-{date_str}'
            ).order_by('-grm_number').first()
            
            if last_grm:
                last_num = int(last_grm.grm_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.grm_number = f'GRM-{date_str}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    def calculate_completion_status(self):
        """Calculate completion status based on received items"""
        if self.total_items_expected == 0:
            return 'pending'
        
        if self.total_items_received == 0:
            return 'pending'
        elif self.total_items_received < self.total_items_expected:
            return 'partial'
        else:
            return 'completed'


class HeatNumber(models.Model):
    """
    Heat Number - Represents a specific batch/lot of raw material within a GRM
    Each heat number contains specific quantities and specifications
    """
    # Heat number identifier
    heat_number = models.CharField(max_length=50, help_text="Heat number from supplier")
    
    # Related GRM and Raw Material
    grm_receipt = models.ForeignKey(
        GRMReceipt, 
        on_delete=models.CASCADE, 
        related_name='heat_numbers'
    )
    raw_material = models.ForeignKey(
        RawMaterial, 
        on_delete=models.PROTECT, 
        related_name='heat_numbers'
    )
    
    # Quantities
    coils_received = models.PositiveIntegerField(
        default=0, 
        help_text="Number of coils received for this heat number"
    )
    total_weight_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Total weight in KG for this heat number"
    )
    
    # For sheet materials
    sheets_received = models.PositiveIntegerField(
        default=0, 
        help_text="Number of sheets received (for sheet materials)"
    )
    
    # Quality Information
    test_certificate_date = models.DateField(null=True, blank=True)
    
    # Individual items (coils/sheets) details
    items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of individual coil/sheet items with number and weight"
    )
    
    # Status
    is_available = models.BooleanField(default=True, help_text="Is this heat number still available for use")
    consumed_quantity_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=0,
        help_text="Quantity consumed from this heat number"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['heat_number', 'grm_receipt', 'raw_material']
        ordering = ['-created_at']
        verbose_name = 'Heat Number'
        verbose_name_plural = 'Heat Numbers'
        indexes = [
            models.Index(fields=['heat_number']),
            models.Index(fields=['grm_receipt', 'raw_material']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"{self.heat_number} - {self.raw_material.material_code} ({self.total_weight_kg}kg)"
    
    def get_available_quantity_kg(self):
        """Get remaining available quantity in KG"""
        return self.total_weight_kg - self.consumed_quantity_kg
    
    def get_available_coils(self):
        """Get remaining available coils"""
        consumed_coils = int((self.consumed_quantity_kg / self.total_weight_kg) * self.coils_received) if self.total_weight_kg > 0 else 0
        return max(0, self.coils_received - consumed_coils)
    
    def update_stock_balance(self):
        """Update the stock balance for this heat number's raw material"""
        try:
            stock_balance, created = RMStockBalanceHeat.objects.get_or_create(
                raw_material=self.raw_material,
                defaults={
                    'total_available_quantity_kg': 0,
                    'total_coils_available': 0,
                    'total_sheets_available': 0,
                    'active_heat_numbers_count': 0
                }
            )
            stock_balance.update_from_heat_numbers()
        except Exception as e:
            print(f"Error updating stock balance: {e}")
    
    def clean(self):
        """Validate heat number data"""
        print(f"DEBUG: HeatNumber model clean() called")
        print(f"DEBUG: raw_material: {self.raw_material}")
        print(f"DEBUG: coils_received: {self.coils_received}")
        print(f"DEBUG: sheets_received: {self.sheets_received}")
        print(f"DEBUG: total_weight_kg: {self.total_weight_kg}")
        
        # Skip validation if raw_material is not set (during creation)
        if not self.raw_material:
            print(f"DEBUG: raw_material not set, skipping validation")
            return
            
        errors = {}
        
        # Validate quantities based on material type
        if self.raw_material.material_type == 'coil':
            if self.coils_received == 0:
                errors['coils_received'] = "Number of coils must be specified for coil materials"
            if self.sheets_received > 0:
                errors['sheets_received'] = "Sheets should not be specified for coil materials"
        elif self.raw_material.material_type == 'sheet':
            if self.sheets_received == 0:
                errors['sheets_received'] = "Number of sheets must be specified for sheet materials"
            if self.coils_received > 0:
                errors['coils_received'] = "Coils should not be specified for sheet materials"
        
        # Validate weight
        if self.total_weight_kg and self.total_weight_kg <= 0:
            errors['total_weight_kg'] = "Total weight must be greater than 0"
        
        if errors:
            print(f"DEBUG: Model validation errors: {errors}")
            raise ValidationError(errors)
        
        print(f"DEBUG: Model validation passed")


class RMStockBalanceHeat(models.Model):
    """
    Enhanced stock balance tracking with Heat number traceability
    Replaces the simple RMStockBalance model
    """
    raw_material = models.ForeignKey(
        RawMaterial, 
        on_delete=models.CASCADE, 
        related_name='heat_stock_balances'
    )
    
    # Aggregate quantities across all heat numbers
    total_available_quantity_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=0,
        help_text="Total available quantity across all heat numbers"
    )
    total_coils_available = models.PositiveIntegerField(
        default=0,
        help_text="Total coils available across all heat numbers"
    )
    total_sheets_available = models.PositiveIntegerField(
        default=0,
        help_text="Total sheets available across all heat numbers"
    )
    
    # Heat number count
    active_heat_numbers_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of active heat numbers with available stock"
    )
    
    # Last updated
    last_updated = models.DateTimeField(auto_now=True)
    last_transaction = models.ForeignKey(
        InventoryTransaction, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        unique_together = ['raw_material']
        verbose_name = 'RM Stock Balance (Heat Tracked)'
        verbose_name_plural = 'RM Stock Balances (Heat Tracked)'
    
    def __str__(self):
        return f"{self.raw_material.material_code} - {self.total_available_quantity_kg}kg"
    
    def update_from_heat_numbers(self):
        """Update stock balance from all active heat numbers"""
        heat_numbers = HeatNumber.objects.filter(
            raw_material=self.raw_material,
            is_available=True
        )
        
        self.total_available_quantity_kg = sum(
            heat.get_available_quantity_kg() for heat in heat_numbers
        )
        self.total_coils_available = sum(
            heat.get_available_coils() for heat in heat_numbers
        )
        self.total_sheets_available = sum(
            heat.sheets_received for heat in heat_numbers if heat.raw_material.material_type == 'sheet'
        )
        self.active_heat_numbers_count = heat_numbers.count()
        
        self.save()


class InventoryTransactionHeat(models.Model):
    """
    Enhanced inventory transaction with Heat number tracking
    Links transactions to specific heat numbers for full traceability
    """
    # Link to existing transaction
    inventory_transaction = models.OneToOneField(
        InventoryTransaction,
        on_delete=models.CASCADE,
        related_name='heat_transaction'
    )
    
    # Heat number details
    heat_number = models.ForeignKey(
        HeatNumber,
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text="Specific heat number involved in this transaction"
    )
    
    # Transaction quantities
    quantity_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        help_text="Quantity in KG for this transaction"
    )
    coils_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of coils involved (for coil materials)"
    )
    sheets_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of sheets involved (for sheet materials)"
    )
    
    # Traceability
    grm_number = models.CharField(
        max_length=20,
        help_text="GRM number for traceability"
    )
    
    class Meta:
        verbose_name = 'Inventory Transaction Heat'
        verbose_name_plural = 'Inventory Transactions Heat'
        indexes = [
            models.Index(fields=['heat_number']),
            models.Index(fields=['grm_number']),
        ]
    
    def __str__(self):
        return f"{self.inventory_transaction.transaction_id} - {self.heat_number.heat_number}"