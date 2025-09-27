"""
Management command to validate and display vendor data after import.

Usage:
python manage.py validate_vendors
"""

from django.core.management.base import BaseCommand
from third_party.models import Vendor, Brand  # Replace 'myapp' with your actual app name


class Command(BaseCommand):
    help = 'Validate and display imported vendor data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--show-brands',
            action='store_true',
            help='Show detailed brand information',
        )
        parser.add_argument(
            '--vendor-type',
            type=str,
            choices=['rm_vendor', 'outsource_vendor'],
            help='Filter by vendor type',
        )
        parser.add_argument(
            '--has-brands',
            action='store_true',
            help='Show only vendors that have brands',
        )

    def handle(self, *args, **options):
        show_brands = options['show_brands']
        vendor_type = options['vendor_type']
        has_brands = options['has_brands']
        
        # Get vendors based on filters
        vendors = Vendor.objects.all()
        if vendor_type:
            vendors = vendors.filter(vendor_type=vendor_type)
        if has_brands:
            vendors = vendors.filter(brands__isnull=False).distinct()
        
        vendors = vendors.prefetch_related('brands').order_by('name')
        
        # Display summary
        self.stdout.write('='*70)
        self.stdout.write('VENDOR DATA VALIDATION REPORT')
        self.stdout.write('='*70)
        
        total_vendors = Vendor.objects.count()
        rm_vendors = Vendor.objects.filter(vendor_type='rm_vendor').count()
        os_vendors = Vendor.objects.filter(vendor_type='outsource_vendor').count()
        active_vendors = Vendor.objects.filter(is_active=True).count()
        vendors_with_brands = Vendor.objects.filter(brands__isnull=False).distinct().count()
        total_brands = Brand.objects.count()
        active_brands = Brand.objects.filter(is_active=True).count()
        
        self.stdout.write(f'Total Vendors: {total_vendors}')
        self.stdout.write(f'  ├─ RM Vendors: {rm_vendors}')
        self.stdout.write(f'  └─ Outsource Vendors: {os_vendors}')
        self.stdout.write(f'Active Vendors: {active_vendors}')
        self.stdout.write(f'Vendors with Brands: {vendors_with_brands}')
        self.stdout.write(f'Total Brands: {total_brands} (Active: {active_brands})')
        
        if show_brands:
            self.stdout.write('\n' + '='*50)
            self.stdout.write('BRAND DETAILS:')
            self.stdout.write('='*50)
            
            brands = Brand.objects.prefetch_related('vendors').order_by('name')
            for brand in brands:
                vendor_count = brand.vendors.count()
                status = "✓" if brand.is_active else "✗"
                self.stdout.write(f'{status} {brand.name} ({vendor_count} vendors)')
                
                if vendor_count > 0:
                    vendor_names = [v.name for v in brand.vendors.all()[:3]]
                    if vendor_count > 3:
                        vendor_names.append(f"... +{vendor_count - 3} more")
                    self.stdout.write(f'   └─ {", ".join(vendor_names)}')
        
        # Display filtered vendors
        self.stdout.write('\n' + '='*50)
        filter_text = []
        if vendor_type:
            filter_text.append(f'Type: {vendor_type}')
        if has_brands:
            filter_text.append('Has brands')
        
        if filter_text:
            self.stdout.write(f'VENDORS ({", ".join(filter_text)}):')
        else:
            self.stdout.write('ALL VENDORS:')
        self.stdout.write('='*50)
        
        if not vendors.exists():
            self.stdout.write(self.style.WARNING('No vendors found matching the criteria.'))
            return
        
        for vendor in vendors:
            # Status indicators
            status = "✓" if vendor.is_active else "✗"
            type_indicator = "RM" if vendor.vendor_type == 'rm_vendor' else "OS"
            
            # Brand information
            brands = vendor.brands.all()
            if brands:
                brand_names = [b.name for b in brands]
                brands_text = f" | Brands: {', '.join(brand_names)}"
            else:
                brands_text = " | No brands"
            
            # Service type
            service_text = f" | {vendor.service_type}" if vendor.service_type else ""
            
            self.stdout.write(
                f'{status} [{type_indicator}] {vendor.name}{service_text}{brands_text}'
            )
            
            # Show products/process if available
            if vendor.products_process:
                self.stdout.write(f'   └─ Products: {vendor.products_process}')
        
        # Data integrity checks
        self.stdout.write('\n' + '='*50)
        self.stdout.write('DATA INTEGRITY CHECKS:')
        self.stdout.write('='*50)
        
        # Check for vendors without names
        nameless_vendors = Vendor.objects.filter(name='')
        if nameless_vendors.exists():
            self.stdout.write(
                self.style.ERROR(f'⚠ Found {nameless_vendors.count()} vendors without names')
            )
        else:
            self.stdout.write(self.style.SUCCESS('✓ All vendors have names'))
        
        # Check for duplicate vendor names
        from django.db.models import Count
        duplicate_names = Vendor.objects.values('name').annotate(
            count=Count('name')
        ).filter(count__gt=1)
        
        if duplicate_names.exists():
            self.stdout.write(
                self.style.WARNING(f'⚠ Found {duplicate_names.count()} duplicate vendor names:')
            )
            for dup in duplicate_names:
                self.stdout.write(f'   - "{dup["name"]}" ({dup["count"]} times)')
        else:
            self.stdout.write(self.style.SUCCESS('✓ No duplicate vendor names'))
        
        # Check for brands without vendors
        orphaned_brands = Brand.objects.filter(vendors__isnull=True)
        if orphaned_brands.exists():
            self.stdout.write(
                self.style.WARNING(f'⚠ Found {orphaned_brands.count()} brands without vendors:')
            )
            for brand in orphaned_brands:
                self.stdout.write(f'   - {brand.name}')
        else:
            self.stdout.write(self.style.SUCCESS('✓ All brands are associated with vendors'))
        
        self.stdout.write('\n' + self.style.SUCCESS('Validation complete!'))