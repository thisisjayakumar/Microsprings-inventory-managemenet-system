from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class Brand(models.Model):
    """
    Brand model to store brand information separately
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Brand name"
    )
    description = models.TextField(
        blank=True,
        help_text="Brand description or notes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this brand currently active?"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        # Convert brand name to title case for consistency
        if self.name:
            self.name = self.name.strip().title()


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
    
    # Products/Services offered by vendor
    products_process = models.TextField(
        blank=True, 
        help_text="Products or processes offered by vendor"
    )
    
    # Type/Category of products/services
    service_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type/category of service (e.g., COATING, PLATING, SHEET)"
    )
    
    # Many-to-Many relationship with brands
    brands = models.ManyToManyField(
        Brand,
        blank=True,
        related_name='vendors',
        help_text="Brands that this vendor works with or supplies"
    )
    
    # GST number validation - Indian GST format: 15 characters - NOW OPTIONAL
    gst_validator = RegexValidator(
        regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
        message='Enter a valid GST number (15 characters in format: 22AAAAA0000A1Z5)'
    )
    gst_no = models.CharField(
        max_length=15,
        validators=[gst_validator],
        unique=True,
        blank=True,
        null=True,
        help_text="15-digit GST number"
    )
    
    address = models.TextField(
        blank=True,
        help_text="Complete vendor address"
    )
    
    # Contact number validation - Indian phone number format - NOW OPTIONAL
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Enter a valid contact number (9-15 digits)'
    )
    contact_no = models.CharField(
        max_length=17,  # +91 followed by 10 digits
        validators=[phone_validator],
        blank=True,
        help_text="Contact phone number"
    )
    
    # Additional useful fields
    email = models.EmailField(blank=True, null=True, help_text="Vendor email address")
    contact_person = models.CharField(max_length=100, blank=True, help_text="Primary contact person name")
    is_active = models.BooleanField(default=True, help_text="Is this vendor currently active?")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_vendors')

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_vendor_type_display()})"
    
    @property
    def brands_list(self):
        """Return a comma-separated list of brand names"""
        return ", ".join([brand.name for brand in self.brands.all()])
    
    def get_brands_display(self):
        """Get brands display for admin or templates"""
        brands = self.brands.all()
        if brands:
            return ", ".join([brand.name for brand in brands])
        return "No brands"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Convert GST number to uppercase
        if self.gst_no:
            self.gst_no = self.gst_no.upper()