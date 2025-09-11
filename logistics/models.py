from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PackagingType(models.Model):
    """
    Different packaging configurations
    """
    name = models.CharField(max_length=100)
    standard_quantity = models.PositiveIntegerField()
    applicable_products = models.ManyToManyField('products.Product', related_name='packaging_types')
    packaging_material_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Packaging Type'
        verbose_name_plural = 'Packaging Types'

    def __str__(self):
        return f"{self.name} ({self.standard_quantity} units)"


class PackedItem(models.Model):
    """
    Individual packed items with QR codes
    """
    STATUS_CHOICES = [
        ('packed', 'Packed'),
        ('in_fg_store', 'In FG Store'),
        ('dispatched', 'Dispatched')
    ]
    
    package_id = models.CharField(max_length=30, unique=True)  # For QR code
    batch = models.ForeignKey('manufacturing.Batch', on_delete=models.CASCADE, related_name='packed_items')
    packaging_type = models.ForeignKey(PackagingType, on_delete=models.PROTECT)
    
    quantity = models.PositiveIntegerField()
    pack_datetime = models.DateTimeField()
    packed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='packed_items')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='packed')
    
    # QR Code data
    qr_code_data = models.TextField()  # JSON string with all traceability info
    
    # Location tracking
    current_location = models.ForeignKey('inventory.Location', on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Packed Item'
        verbose_name_plural = 'Packed Items'

    def __str__(self):
        return f"{self.package_id} - {self.batch.batch_id}"


class DispatchOrder(models.Model):
    """
    Dispatch and shipping management
    """
    dispatch_id = models.CharField(max_length=20, unique=True)
    mo = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.PROTECT, related_name='dispatch_orders')
    
    # Customer details
    customer_name = models.CharField(max_length=200)
    delivery_address = models.TextField()
    
    # Dispatch details
    packed_items = models.ManyToManyField(PackedItem, related_name='dispatch_orders')
    dispatch_datetime = models.DateTimeField()
    dispatched_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='dispatched_orders')
    
    # Logistics
    vehicle_number = models.CharField(max_length=20, blank=True)
    driver_details = models.CharField(max_length=200, blank=True)
    
    # Documentation
    dispatch_note_generated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dispatch Order'
        verbose_name_plural = 'Dispatch Orders'

    def __str__(self):
        return f"{self.dispatch_id} - {self.customer_name}"