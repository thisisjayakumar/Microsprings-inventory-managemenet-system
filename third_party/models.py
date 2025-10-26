from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from utils.enums import VendorTypeChoices, IndustryTypeChoices

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
    name = models.CharField(max_length=200, help_text="Vendor company name")
    vendor_type = models.CharField(
        max_length=20, 
        choices=VendorTypeChoices.choices,
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


class Customer(models.Model):
    """
    Customer model to store customer information with contact details
    """
    # Auto-generated customer ID
    c_id = models.CharField(
        max_length=10, 
        unique=True, 
        null=True,
        blank=True,
        editable=False,
        help_text="Auto-generated customer ID (C_001, C_002, etc.)"
    )
    
    name = models.CharField(
        max_length=200, 
        unique=True,
        help_text="Customer company name"
    )
    
    industry_type = models.CharField(
        max_length=50,
        choices=IndustryTypeChoices.choices,
        help_text="Type of industry the customer operates in"
    )
    
    # GST number validation - Indian GST format: 15 characters - OPTIONAL
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
        help_text="Complete customer address"
    )
    
    # Contact information - simplified structure
    point_of_contact = models.TextField(
        blank=True,
        help_text="Point of contact names and designations (as a single string)"
    )
    
    contact_no_1 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Primary contact number(s)"
    )
    
    contact_no_2 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Secondary contact number(s)"
    )
    
    email_id = models.EmailField(
        blank=True,
        null=True,
        help_text="Primary email address"
    )
    
    # Additional fields
    is_active = models.BooleanField(
        default=True,
        help_text="Is this customer currently active?"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the customer"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_customers'
    )

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.c_id:
            # Generate c_id: C_001, C_002, etc.
            last_customer = Customer.objects.order_by('c_id').last()
            
            if last_customer and last_customer.c_id:
                # Extract number from last c_id (e.g., "C_001" -> 1)
                try:
                    last_number = int(last_customer.c_id.split('_')[1])
                    next_number = last_number + 1
                except (IndexError, ValueError):
                    next_number = 1
            else:
                next_number = 1
            
            self.c_id = f'C_{next_number:03d}'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.c_id} - {self.name} ({self.get_industry_type_display()})"
    
    @property
    def primary_contact(self):
        """Return primary contact information"""
        if self.point_of_contact:
            # Return first 50 characters for display
            return self.point_of_contact[:50] + "..." if len(self.point_of_contact) > 50 else self.point_of_contact
        return "No primary contact"
    
    @property
    def all_contacts(self):
        """Return all contact information as a dictionary"""
        return {
            'point_of_contact': self.point_of_contact,
            'contact_no_1': self.contact_no_1,
            'contact_no_2': self.contact_no_2,
            'email_id': self.email_id
        }
    
    def get_contacts_display(self):
        """Get formatted contact display for admin"""
        if self.point_of_contact:
            return self.point_of_contact[:100] + "..." if len(self.point_of_contact) > 100 else self.point_of_contact
        return "No contacts"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Convert GST number to uppercase
        if self.gst_no:
            self.gst_no = self.gst_no.upper()
        
        # Convert customer name to title case for consistency
        if self.name:
            self.name = self.name.strip().title()