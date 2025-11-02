"""
Outsourcing Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from utils.enums import OutsourcingStatusChoices

User = get_user_model()


class OutsourcingRequest(models.Model):
    """
    Outsourcing Request - Track items sent to external vendors for processing
    """
    # Auto-generated fields
    request_id = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Basic info
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_outsourcing_requests')
    vendor = models.ForeignKey('third_party.Vendor', on_delete=models.PROTECT, related_name='outsourcing_requests')
    
    # Dates
    date_sent = models.DateField(null=True, blank=True)
    expected_return_date = models.DateField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=OutsourcingStatusChoices.choices, default='draft')
    
    # Collection info
    collected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='collected_outsourcing_requests'
    )
    collection_date = models.DateField(null=True, blank=True)
    
    # Contact person at vendor
    vendor_contact_person = models.CharField(max_length=100, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Outsourcing Request'
        verbose_name_plural = 'Outsourcing Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['vendor']),
            models.Index(fields=['created_by']),
            models.Index(fields=['expected_return_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            now = timezone.now()
            date_str = now.strftime('%Y%m%d')
            
            existing_requests = OutsourcingRequest.objects.filter(
                request_id__startswith=f'OUT-{date_str}'
            ).count()
            sequence = existing_requests + 1
            self.request_id = f'OUT-{date_str}-{sequence:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.request_id} - {self.vendor.name} ({self.get_status_display()})"
    
    @property
    def is_overdue(self):
        """Check if the request is overdue"""
        if self.status in ['returned', 'closed']:
            return False
        return self.expected_return_date < timezone.now().date()
    
    @property
    def total_items(self):
        """Get total number of items in this request"""
        return self.items.count()
    
    @property
    def total_qty(self):
        """Get total quantity across all items"""
        return sum(item.qty or 0 for item in self.items.all())
    
    @property
    def total_kg(self):
        """Get total weight across all items"""
        return sum(item.kg or 0 for item in self.items.all())


class OutsourcedItem(models.Model):
    """
    Individual items within an outsourcing request
    """
    request = models.ForeignKey(OutsourcingRequest, on_delete=models.CASCADE, related_name='items')
    
    # Product info
    mo_number = models.CharField(max_length=20, help_text="Manufacturing Order number")
    product_code = models.CharField(max_length=120, help_text="Product code")
    
    # Quantities
    qty = models.PositiveIntegerField(null=True, blank=True, help_text="Quantity in pieces")
    kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Weight in kg")
    
    # Return tracking
    returned_qty = models.PositiveIntegerField(default=0, help_text="Returned quantity in pieces")
    returned_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Returned weight in kg")
    
    # Additional info
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Outsourced Item'
        verbose_name_plural = 'Outsourced Items'
        ordering = ['mo_number', 'product_code']
        indexes = [
            models.Index(fields=['request', 'mo_number']),
            models.Index(fields=['product_code']),
        ]
    
    def __str__(self):
        return f"{self.mo_number} - {self.product_code} (Qty: {self.qty}, Kg: {self.kg})"
    
    def clean(self):
        """Validate that at least qty or kg is provided"""
        if not self.qty and not self.kg:
            raise ValidationError("Either quantity or weight must be provided")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
