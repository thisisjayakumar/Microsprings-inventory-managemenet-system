from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Location(models.Model):
    """
    Physical locations within the facility
    """
    LOCATION_TYPE_CHOICES = [
        ('rm_store', 'Raw Material Store'),
        ('wip', 'Work In Progress'),
        ('fg_store', 'Finished Goods Store'),
        ('quality', 'Quality Control'),
        ('dispatch', 'Dispatch Area')
    ]
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES)
    parent_location = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_locations')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f"{self.code} - {self.name}"


class InventoryTransaction(models.Model):
    """
    Universal inventory tracking
    """
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
    batch = models.ForeignKey('manufacturing.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions')
    
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


class StockBalance(models.Model):
    """
    Current stock levels - calculated/cached view
    """
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_balances')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='stock_balances')
    batch = models.ForeignKey('manufacturing.Batch', on_delete=models.CASCADE, null=True, blank=True, related_name='stock_balances')
    
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Allocated but not consumed
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # current - reserved
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'location', 'batch']
        verbose_name = 'Stock Balance'
        verbose_name_plural = 'Stock Balances'

    def __str__(self):
        return f"{self.product.part_number} @ {self.location.code}: {self.current_quantity}"