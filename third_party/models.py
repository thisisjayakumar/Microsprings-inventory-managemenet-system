from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class Vendor(models.Model):
    VENDOR_TYPE_CHOICES = [
        ('rm_vendor', 'RM Vendor'),
        ('outsource_vendor', 'Outsource Vendor'),
    ]
    
    name = models.CharField(max_length=200, help_text="Vendor company name")
    vendor_type = models.CharField(
        max_length=20, 
        choices=VENDOR_TYPE_CHOICES,
        help_text="Type of vendor - Raw Material or Outsource"
    )
    
    # GST number validation - Indian GST format: 15 characters
    gst_validator = RegexValidator(
        regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
        message='Enter a valid GST number (15 characters in format: 22AAAAA0000A1Z5)'
    )
    gst_no = models.CharField(
        max_length=15,
        validators=[gst_validator],
        unique=True,
        help_text="15-digit GST number"
    )
    
    address = models.TextField(help_text="Complete vendor address")
    
    # Contact number validation - Indian phone number format
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Enter a valid contact number (9-15 digits)'
    )
    contact_no = models.CharField(
        max_length=17,  # +91 followed by 10 digits
        validators=[phone_validator],
        help_text="Contact phone number"
    )
    
    # Additional useful fields
    email = models.EmailField(blank=True, null=True, help_text="Vendor email address")
    contact_person = models.CharField(max_length=100, blank=True, help_text="Primary contact person name")
    is_active = models.BooleanField(default=True, help_text="Is this vendor currently active?")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_vendors')

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_vendor_type_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Convert GST number to uppercase
        if self.gst_no:
            self.gst_no = self.gst_no.upper()
