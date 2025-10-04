"""
Django Admin configuration for Vendor and Brand models.
Add this to your admin.py file.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Vendor, Brand, Customer


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'vendor_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def vendor_count(self, obj):
        """Display the number of vendors associated with this brand"""
        count = obj.vendors.count()
        if count > 0:
            return format_html(
                '<a href="{}?brands__id__exact={}">{} vendors</a>',
                '/admin/third_party/vendor/',
                obj.id,
                count
            )
        return '0 vendors'
    vendor_count.short_description = 'Vendors'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class VendorBrandInline(admin.TabularInline):
    """Inline to show brands in vendor admin"""
    model = Vendor.brands.through
    extra = 1
    verbose_name = "Brand"
    verbose_name_plural = "Brands"


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'vendor_type', 
        'service_type', 
        'brands_display', 
        'is_active', 
        'created_at'
    ]
    list_filter = [
        'vendor_type', 
        'service_type', 
        'is_active', 
        'brands',
        'created_at'
    ]
    search_fields = [
        'name', 
        'products_process', 
        'service_type',
        'brands__name',
        'gst_no',
        'contact_person'
    ]
    filter_horizontal = ['brands']  # Nice widget for many-to-many
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at', 'brands_list']
    
    def brands_display(self, obj):
        """Display brands in list view"""
        brands = obj.brands.all()[:3]  # Show max 3 brands in list
        if brands:
            brand_names = [brand.name for brand in brands]
            if obj.brands.count() > 3:
                brand_names.append(f"... +{obj.brands.count() - 3} more")
            return ", ".join(brand_names)
        return "No brands"
    brands_display.short_description = 'Brands'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'vendor_type', 'is_active')
        }),
        ('Products & Services', {
            'fields': ('products_process', 'service_type', 'brands')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'email', 'contact_no', 'address'),
            'classes': ('collapse',)
        }),
        ('Legal Information', {
            'fields': ('gst_no',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at', 'brands_list'),
            'classes': ('collapse',),
            'description': 'System generated information'
        }),
    )
    
    # Custom actions
    actions = ['make_active', 'make_inactive', 'export_vendors']
    
    def make_active(self, request, queryset):
        """Bulk action to activate vendors"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vendors were successfully marked as active.')
    make_active.short_description = "Mark selected vendors as active"
    
    def make_inactive(self, request, queryset):
        """Bulk action to deactivate vendors"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vendors were successfully marked as inactive.')
    make_inactive.short_description = "Mark selected vendors as inactive"
    
    def export_vendors(self, request, queryset):
        """Export selected vendors to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vendors_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Vendor Type', 'Products/Process', 'Service Type', 
            'Brands', 'GST No', 'Contact Person', 'Email', 'Phone', 'Address'
        ])
        
        for vendor in queryset:
            writer.writerow([
                vendor.name,
                vendor.get_vendor_type_display(),
                vendor.products_process,
                vendor.service_type,
                vendor.brands_list,
                vendor.gst_no or '',
                vendor.contact_person or '',
                vendor.email or '',
                vendor.contact_no or '',
                vendor.address or ''
            ])
        
        return response
    export_vendors.short_description = "Export selected vendors to CSV"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'c_id',
        'name', 
        'industry_type', 
        'gst_no',
        'primary_contact',
        'contact_no_1',
        'is_active', 
        'created_at'
    ]
    list_filter = [
        'industry_type', 
        'is_active', 
        'created_at'
    ]
    search_fields = [
        'c_id',
        'name', 
        'gst_no',
        'address',
        'point_of_contact',
        'contact_no_1',
        'contact_no_2',
        'email_id'
    ]
    ordering = ['name']
    readonly_fields = ['c_id', 'created_at', 'updated_at', 'all_contacts_display']
    
    def all_contacts_display(self, obj):
        """Display all contacts in a formatted way"""
        contacts = obj.all_contacts
        contact_html = "<div>"
        
        if contacts.get('point_of_contact'):
            contact_html += f"<strong>POC:</strong> {contacts['point_of_contact']}<br>"
        
        if contacts.get('contact_no_1'):
            contact_html += f"<strong>📞 Contact 1:</strong> {contacts['contact_no_1']}<br>"
        
        if contacts.get('contact_no_2'):
            contact_html += f"<strong>📞 Contact 2:</strong> {contacts['contact_no_2']}<br>"
        
        if contacts.get('email_id'):
            contact_html += f"<strong>✉️ Email:</strong> {contacts['email_id']}<br>"
        
        contact_html += "</div>"
        
        if contact_html == "<div></div>":
            return "No contacts"
        
        return format_html(contact_html)
    all_contacts_display.short_description = 'All Contacts'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('c_id', 'name', 'industry_type', 'is_active')
        }),
        ('Legal Information', {
            'fields': ('gst_no', 'address'),
        }),
        ('Contact Information', {
            'fields': ('point_of_contact', 'contact_no_1', 'contact_no_2', 'email_id'),
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at', 'all_contacts_display'),
            'classes': ('collapse',),
            'description': 'System generated information'
        }),
    )
    
    # Custom actions
    actions = ['make_active', 'make_inactive', 'export_customers']
    
    def make_active(self, request, queryset):
        """Bulk action to activate customers"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} customers were successfully marked as active.')
    make_active.short_description = "Mark selected customers as active"
    
    def make_inactive(self, request, queryset):
        """Bulk action to deactivate customers"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} customers were successfully marked as inactive.')
    make_inactive.short_description = "Mark selected customers as inactive"
    
    def export_customers(self, request, queryset):
        """Export selected customers to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'S.No', 'Customer ID', 'Customer Name', 'Industry Type', 'GST No.', 'Address',
            'Point of Contact', 'Contact No. 1', 'Contact No. 2', 'Email ID',
            'Is Active', 'Notes'
        ])
        
        for idx, customer in enumerate(queryset, 1):
            writer.writerow([
                idx,
                customer.c_id,
                customer.name,
                customer.get_industry_type_display(),
                customer.gst_no or '',
                customer.address,
                customer.point_of_contact or '',
                customer.contact_no_1 or '',
                customer.contact_no_2 or '',
                customer.email_id or '',
                'Yes' if customer.is_active else 'No',
                customer.notes or ''
            ])
        
        return response
    export_customers.short_description = "Export selected customers to CSV"