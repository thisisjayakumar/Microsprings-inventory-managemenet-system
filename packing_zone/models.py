from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from authentication.models import CustomUser
from products.models import Product
from datetime import timedelta
from decimal import Decimal


class PackingBatch(models.Model):
    """
    Incoming batch from Final Inspection to be packed
    """
    STATUS_CHOICES = [
        ('to_be_verified', 'To Be Verified'),
        ('verified', 'Verified'),
        ('on_hold', 'On Hold'),
        ('packed', 'Packed'),
        ('reported', 'Reported'),
    ]
    
    HOLD_REASON_CHOICES = [
        ('low_qty', 'Received Low Qty'),
        ('high_qty', 'Received High Qty'),
        ('product_mismatch', 'Different Product Received'),
        ('other', 'Others'),
    ]
    
    # Product and batch information
    mo_id = models.CharField(max_length=50, help_text='Manufacturing Order ID')
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='packing_batches',
        null=True
    )
    ipc = models.CharField(
        max_length=100,
        help_text='Internal Product Code'
    )
    heat_no = models.CharField(max_length=50, help_text='Heat Number')
    coil_no = models.CharField(max_length=50, blank=True, null=True)
    
    # Quantity and specifications
    ok_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='OK Quantity in kg from Final Inspection'
    )
    actual_received_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Actual quantity received if different'
    )
    grams_per_product = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Grams per product from BoM'
    )
    packing_size = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text='Number of pieces per pack'
    )
    
    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='to_be_verified'
    )
    hold_reason = models.CharField(
        max_length=20,
        choices=HOLD_REASON_CHOICES,
        blank=True,
        null=True
    )
    hold_notes = models.TextField(blank=True, null=True)
    
    # Tracking
    received_date = models.DateTimeField(auto_now_add=True)
    verified_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_batches'
    )
    released_date = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_batches',
        help_text='PH who released from hold'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Packing Batch'
        verbose_name_plural = 'Packing Batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'product_code']),
            models.Index(fields=['heat_no', 'ipc']),
            models.Index(fields=['mo_id']),
        ]
    
    def __str__(self):
        return f"{self.ipc} - {self.heat_no} ({self.ok_quantity_kg} kg)"
    
    @property
    def available_quantity_kg(self):
        """Get the available quantity for packing"""
        return self.actual_received_kg or self.ok_quantity_kg
    
    def verify(self, user):
        """Mark batch as verified"""
        self.status = 'verified'
        self.verified_by = user
        self.verified_date = timezone.now()
        self.save()
    
    def report_issue(self, reason, notes='', actual_kg=None):
        """Report an issue with the batch"""
        self.status = 'on_hold' if reason == 'product_mismatch' else 'reported'
        self.hold_reason = reason
        self.hold_notes = notes
        if actual_kg is not None:
            self.actual_received_kg = actual_kg
        self.save()
    
    def release_from_hold(self, user):
        """Release batch from hold (PH only)"""
        self.status = 'verified'
        self.released_by = user
        self.released_date = timezone.now()
        self.save()


class PackingTransaction(models.Model):
    """
    Record of packing activity
    """
    # Batches involved
    batches = models.ManyToManyField(
        PackingBatch,
        related_name='packing_transactions'
    )
    
    # Product information
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='packing_transactions',
        null=True
    )
    ipc = models.CharField(max_length=100)
    heat_no = models.CharField(
        max_length=50,
        help_text='Primary heat number or merged heat number'
    )
    
    # Packing details
    total_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Total weight used for packing'
    )
    grams_per_product = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    packing_size = models.IntegerField()
    
    # Packing results
    theoretical_packs = models.IntegerField(
        help_text='Calculated number of packs'
    )
    actual_packs = models.IntegerField(
        help_text='Actual packs created'
    )
    loose_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Remaining loose weight'
    )
    loose_pieces = models.IntegerField(
        help_text='Calculated loose pieces'
    )
    variance_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text='Theoretical vs Actual variance'
    )
    
    # Tracking
    packed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='packing_activities'
    )
    packed_date = models.DateTimeField(auto_now_add=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Packing Transaction'
        verbose_name_plural = 'Packing Transactions'
        ordering = ['-packed_date']
        indexes = [
            models.Index(fields=['product_code', 'heat_no']),
            models.Index(fields=['packed_date']),
            models.Index(fields=['packed_by']),
        ]
    
    def __str__(self):
        return f"{self.ipc} - {self.actual_packs} packs ({self.packed_date.date()})"


class LooseStock(models.Model):
    """
    Tracking loose pieces by product and heat number
    """
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='loose_stocks',
        null=True
    )
    ipc = models.CharField(max_length=100)
    heat_no = models.CharField(max_length=50)
    
    # Quantity
    loose_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000')
    )
    loose_pieces = models.IntegerField(default=0)
    grams_per_product = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    
    # Tracking
    first_added_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Loose Stock'
        verbose_name_plural = 'Loose Stocks'
        unique_together = ['product_code', 'ipc', 'heat_no']
        ordering = ['product_code', 'heat_no']
        indexes = [
            models.Index(fields=['product_code', 'heat_no']),
            models.Index(fields=['ipc']),
        ]
    
    def __str__(self):
        return f"{self.ipc} - {self.heat_no} ({self.loose_kg} kg, {self.loose_pieces} pcs)"
    
    @property
    def age_days(self):
        """Calculate age of loose stock in days"""
        return (timezone.now() - self.first_added_date).days
    
    @property
    def is_old(self):
        """Check if loose stock is older than 50 days"""
        return self.age_days > 50
    
    def add_loose(self, kg, pieces):
        """Add to loose stock"""
        self.loose_kg += Decimal(str(kg))
        self.loose_pieces += pieces
        self.save()
    
    def reduce_loose(self, kg, pieces):
        """Reduce from loose stock"""
        self.loose_kg -= Decimal(str(kg))
        self.loose_pieces -= pieces
        if self.loose_kg < 0:
            self.loose_kg = Decimal('0.000')
        if self.loose_pieces < 0:
            self.loose_pieces = 0
        self.save()


class MergedHeatNumber(models.Model):
    """
    Tracking merged heat numbers
    """
    merged_heat_no = models.CharField(
        max_length=50,
        unique=True,
        help_text='New merged heat number (e.g., H2025A42M1)'
    )
    original_heat_nos = models.JSONField(
        help_text='List of original heat numbers merged'
    )
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='merged_heat_numbers',
        null=True
    )
    ipc = models.CharField(max_length=100)
    
    # Quantities from each heat number
    heat_quantities = models.JSONField(
        help_text='Dict mapping heat_no to kg quantity',
        default=dict
    )
    total_merged_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    total_merged_pieces = models.IntegerField()
    
    # Approval tracking
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_merges'
    )
    approved_date = models.DateTimeField(auto_now_add=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Merged Heat Number'
        verbose_name_plural = 'Merged Heat Numbers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merged_heat_no']),
            models.Index(fields=['product_code']),
        ]
    
    def __str__(self):
        return f"{self.merged_heat_no} (from {len(self.original_heat_nos)} heat nos.)"


class MergeRequest(models.Model):
    """
    Request to merge different heat numbers (requires PH approval)
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='merge_requests',
        null=True
    )
    ipc = models.CharField(max_length=100)
    
    # Heat numbers and quantities to merge
    heat_numbers_data = models.JSONField(
        help_text='List of dicts with heat_no, kg, pieces, age_days'
    )
    total_kg = models.DecimalField(max_digits=10, decimal_places=3)
    total_pieces = models.IntegerField()
    
    # Request details
    requested_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='merge_requests_created'
    )
    requested_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(help_text='Reason for merge request')
    
    # Approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merge_requests_reviewed'
    )
    reviewed_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # Generated merged heat number
    merged_heat_number = models.ForeignKey(
        MergedHeatNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merge_request'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Merge Request'
        verbose_name_plural = 'Merge Requests'
        ordering = ['-requested_date']
        indexes = [
            models.Index(fields=['status', 'product_code']),
            models.Index(fields=['requested_by', 'requested_date']),
        ]
    
    def __str__(self):
        heat_count = len(self.heat_numbers_data) if self.heat_numbers_data else 0
        return f"Merge Request - {self.ipc} ({heat_count} heat nos.) - {self.status}"
    
    def approve(self, user, merged_heat_no):
        """Approve merge request and create merged heat number"""
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_date = timezone.now()
        self.save()
        
        # Create MergedHeatNumber record
        original_heat_nos = [item['heat_no'] for item in self.heat_numbers_data]
        heat_quantities = {
            item['heat_no']: item['kg'] 
            for item in self.heat_numbers_data
        }
        
        merged = MergedHeatNumber.objects.create(
            merged_heat_no=merged_heat_no,
            original_heat_nos=original_heat_nos,
            product_code=self.product_code,
            product=self.product,
            ipc=self.ipc,
            heat_quantities=heat_quantities,
            total_merged_kg=self.total_kg,
            total_merged_pieces=self.total_pieces,
            approved_by=user
        )
        
        self.merged_heat_number = merged
        self.save()
        
        return merged
    
    def reject(self, user, notes=''):
        """Reject merge request"""
        self.status = 'rejected'
        self.reviewed_by = user
        self.reviewed_date = timezone.now()
        self.review_notes = notes
        self.save()


class StockAdjustment(models.Model):
    """
    Adjustments for old/rusted loose stock (requires PH approval)
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    REASON_CHOICES = [
        ('rust', 'Rust'),
        ('old_stock', 'Old Stock'),
        ('other', 'Other'),
    ]
    
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_adjustments',
        null=True
    )
    ipc = models.CharField(max_length=100)
    heat_no = models.CharField(max_length=50)
    
    # Adjustment details
    adjustment_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    adjustment_pieces = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reason_details = models.TextField(help_text='Detailed reason for adjustment')
    
    # Request details
    requested_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='adjustment_requests_created'
    )
    requested_date = models.DateTimeField(auto_now_add=True)
    
    # Approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adjustment_requests_reviewed'
    )
    reviewed_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        ordering = ['-requested_date']
        indexes = [
            models.Index(fields=['status', 'product_code']),
            models.Index(fields=['heat_no']),
        ]
    
    def __str__(self):
        return f"Adjustment - {self.ipc} ({self.adjustment_kg} kg) - {self.status}"
    
    def approve(self, user):
        """Approve adjustment and update loose stock"""
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_date = timezone.now()
        self.save()
    
    def reject(self, user, notes=''):
        """Reject adjustment"""
        self.status = 'rejected'
        self.reviewed_by = user
        self.reviewed_date = timezone.now()
        self.review_notes = notes
        self.save()


class PackingLabel(models.Model):
    """
    Tracking printed labels for traceability
    """
    # Label information
    label_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique label identifier'
    )
    
    # Product information
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='packing_labels',
        null=True
    )
    ipc = models.CharField(max_length=100, help_text='Internal Product Code')
    product_name = models.CharField(max_length=200)
    
    # Packing details
    packing_size = models.IntegerField()
    quantity_pcs = models.IntegerField()
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Heat number (not printed on customer label)
    heat_no = models.CharField(
        max_length=50,
        help_text='Heat number (internal only)'
    )
    merged_heat_no = models.ForeignKey(
        MergedHeatNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='If from merged batch'
    )
    
    # Dates
    date_of_manufacture = models.DateField()
    date_packed = models.DateField()
    
    # Printing tracking
    printed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='printed_labels'
    )
    printed_date = models.DateTimeField(auto_now_add=True)
    reprint_count = models.IntegerField(default=0)
    last_reprinted = models.DateTimeField(null=True, blank=True)
    
    # Link to transaction
    packing_transaction = models.ForeignKey(
        PackingTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='labels'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Packing Label'
        verbose_name_plural = 'Packing Labels'
        ordering = ['-printed_date']
        indexes = [
            models.Index(fields=['label_id']),
            models.Index(fields=['ipc', 'heat_no']),
            models.Index(fields=['printed_date']),
        ]
    
    def __str__(self):
        return f"Label {self.label_id} - {self.ipc}"
    
    def reprint(self):
        """Track label reprint"""
        self.reprint_count += 1
        self.last_reprinted = timezone.now()
        self.save()


class FGStock(models.Model):
    """
    Finished Goods stock tracking by product and heat number
    """
    product_code = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='fg_stocks',
        null=True
    )
    ipc = models.CharField(max_length=100)
    heat_no = models.CharField(max_length=50)
    
    # Stock details
    total_packs = models.IntegerField(default=0)
    packing_size = models.IntegerField()
    grams_per_product = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'FG Stock'
        verbose_name_plural = 'FG Stocks'
        unique_together = ['product_code', 'ipc', 'heat_no']
        ordering = ['product_code', 'heat_no']
        indexes = [
            models.Index(fields=['product_code', 'heat_no']),
            models.Index(fields=['ipc']),
        ]
    
    def __str__(self):
        return f"{self.ipc} - {self.heat_no} ({self.total_packs} packs)"
    
    def add_packs(self, count):
        """Add packs to FG stock"""
        self.total_packs += count
        self.save()
    
    def reduce_packs(self, count):
        """Reduce packs from FG stock"""
        self.total_packs -= count
        if self.total_packs < 0:
            self.total_packs = 0
        self.save()

