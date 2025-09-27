"""
Management command to import vendor data from CSV file.

Usage:
python manage.py import_vendors path/to/vendors.csv
"""

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from third_party.models import Vendor, Brand  # Replace 'myapp' with your actual app name

User = get_user_model()


class Command(BaseCommand):
    help = 'Import vendor data from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing vendor data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the command without actually saving data to database',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing vendors if they already exist (based on name)',
        )
        parser.add_argument(
            '--created-by',
            type=str,
            help='Username of the user who should be recorded as creator of vendors',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        created_by_username = options.get('created_by')
        
        # Get the user who should be recorded as creator
        created_by_user = None
        if created_by_username:
            try:
                created_by_user = User.objects.get(username=created_by_username)
                self.stdout.write(f'Creator user: {created_by_user}')
            except User.DoesNotExist:
                raise CommandError(f'User "{created_by_username}" does not exist.')
        
        # Check if file exists
        if not os.path.exists(csv_file_path):
            raise CommandError(f'File "{csv_file_path}" does not exist.')
        
        # Counters for reporting
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        brands_created_count = 0
        
        self.stdout.write(f'Starting import from: {csv_file_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                # Use DictReader to handle CSV with headers
                reader = csv.DictReader(file)
                
                # Required headers
                required_headers = ['Name', 'RM/OS', 'Products/Process', 'Type', 'Brands']
                
                # Optional headers that can be in the CSV
                optional_headers = ['GST_No', 'Address', 'Contact_No', 'Email', 'Contact_Person']
                
                # Validate required headers
                missing_headers = set(required_headers) - set(reader.fieldnames)
                if missing_headers:
                    raise CommandError(f'Missing required headers: {missing_headers}')
                
                # Check for optional headers
                available_optional = set(optional_headers) & set(reader.fieldnames)
                if available_optional:
                    self.stdout.write(f'Found optional headers: {", ".join(available_optional)}')
                else:
                    self.stdout.write('No optional headers found (GST_No, Address, Contact_No, Email, Contact_Person)')
                
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                        try:
                            # Clean and prepare data
                            name = row['Name'].strip()
                            rm_os = row['RM/OS'].strip().upper()
                            products_process = row['Products/Process'].strip()
                            service_type = row['Type'].strip()
                            brands_text = row['Brands'].strip() if row['Brands'] else ''
                            
                            # Handle optional fields from CSV
                            gst_no = row.get('GST_No', '').strip() if row.get('GST_No') else ''
                            address = row.get('Address', '').strip() if row.get('Address') else ''
                            contact_no = row.get('Contact_No', '').strip() if row.get('Contact_No') else ''
                            email = row.get('Email', '').strip() if row.get('Email') else ''
                            contact_person = row.get('Contact_Person', '').strip() if row.get('Contact_Person') else ''
                            
                            # Process brands - create Brand objects or get existing ones
                            brand_objects = []
                            if brands_text:
                                # Remove surrounding quotes if present
                                brands_text = brands_text.strip('"').strip("'")
                                # Split by comma and clean each brand name
                                brand_names = [brand.strip().title() for brand in brands_text.split(',') if brand.strip()]
                                
                                # Keep track of brands we've already processed in this dry run
                                if dry_run and not hasattr(self, '_dry_run_brands_seen'):
                                    self._dry_run_brands_seen = set()
                                
                                for brand_name in brand_names:
                                    if not dry_run:
                                        # Normal processing
                                        brand, brand_created = Brand.objects.get_or_create(
                                            name=brand_name,
                                            defaults={'is_active': True}
                                        )
                                        brand_objects.append(brand)
                                        if brand_created:
                                            brands_created_count += 1
                                            self.stdout.write(f'  → Created brand: {brand_name}')
                                    else:
                                        # Dry run processing
                                        try:
                                            brand = Brand.objects.get(name=brand_name)
                                            # Brand already exists in database
                                            from types import SimpleNamespace
                                            brand_obj = SimpleNamespace(name=brand_name)
                                            brand_objects.append(brand_obj)
                                        except Brand.DoesNotExist:
                                            # Brand doesn't exist - would be created
                                            from types import SimpleNamespace
                                            brand_obj = SimpleNamespace(name=brand_name)
                                            brand_objects.append(brand_obj)
                                            
                                            # Only show "would create" message once per brand
                                            if brand_name not in self._dry_run_brands_seen:
                                                self.stdout.write(f'  → [DRY RUN] Would create brand: {brand_name}')
                                                brands_created_count += 1
                                                self._dry_run_brands_seen.add(brand_name)
                            
                            # Validate required fields
                            if not name:
                                self.stdout.write(
                                    self.style.ERROR(f'Row {row_num}: Name is required')
                                )
                                error_count += 1
                                continue
                            
                            # Map RM/OS to vendor_type
                            if rm_os == 'RM':
                                vendor_type = 'rm_vendor'
                            elif rm_os == 'OS':
                                vendor_type = 'outsource_vendor'
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f'Row {row_num}: Invalid RM/OS value "{rm_os}". Must be "RM" or "OS"')
                                )
                                error_count += 1
                                continue
                            
                            # Check if vendor already exists
                            vendor_defaults = {
                                'vendor_type': vendor_type,
                                'products_process': products_process,
                                'service_type': service_type,
                                'is_active': True,
                            }
                            
                            # Add optional fields to defaults if they have values
                            if gst_no:
                                vendor_defaults['gst_no'] = gst_no.upper()
                            if address:
                                vendor_defaults['address'] = address
                            if contact_no:
                                vendor_defaults['contact_no'] = contact_no
                            if email:
                                vendor_defaults['email'] = email.lower()
                            if contact_person:
                                vendor_defaults['contact_person'] = contact_person
                            if created_by_user:
                                vendor_defaults['created_by'] = created_by_user
                            
                            vendor, created = Vendor.objects.get_or_create(
                                name=name,
                                defaults=vendor_defaults
                            )
                            
                            # Add brands to vendor (works for both new and existing vendors)
                            if brand_objects and not dry_run:
                                vendor.brands.set(brand_objects)
                            
                            if created:
                                if not dry_run:
                                    brands_display = f" | Brands: {', '.join([getattr(b, 'name', str(b)) for b in brand_objects])}" if brand_objects else ""
                                    optional_info = []
                                    if gst_no: optional_info.append(f"GST: {gst_no}")
                                    if contact_person: optional_info.append(f"Contact: {contact_person}")
                                    optional_display = f" | {', '.join(optional_info)}" if optional_info else ""
                                    self.stdout.write(f'✓ Created: {name} ({vendor_type}){brands_display}{optional_display}')
                                else:
                                    brands_display = f" | Brands: {', '.join([getattr(b, 'name', str(b)) for b in brand_objects])}" if brand_objects else ""
                                    optional_info = []
                                    if gst_no: optional_info.append(f"GST: {gst_no}")
                                    if contact_person: optional_info.append(f"Contact: {contact_person}")
                                    optional_display = f" | {', '.join(optional_info)}" if optional_info else ""
                                    self.stdout.write(f'[DRY RUN] Would create: {name} ({vendor_type}){brands_display}{optional_display}')
                                created_count += 1
                            else:
                                if update_existing:
                                    # Update existing vendor
                                    vendor.vendor_type = vendor_type
                                    vendor.products_process = products_process
                                    vendor.service_type = service_type
                                    
                                    # Update optional fields if provided
                                    if gst_no:
                                        vendor.gst_no = gst_no.upper()
                                    if address:
                                        vendor.address = address
                                    if contact_no:
                                        vendor.contact_no = contact_no
                                    if email:
                                        vendor.email = email.lower()
                                    if contact_person:
                                        vendor.contact_person = contact_person
                                    
                                    if not dry_run:
                                        vendor.save()
                                        # Update brands relationship
                                        vendor.brands.set(brand_objects)
                                        brands_display = f" | Brands: {', '.join([getattr(b, 'name', str(b)) for b in brand_objects])}" if brand_objects else ""
                                        self.stdout.write(f'✓ Updated: {name}{brands_display}')
                                    else:
                                        brands_display = f" | Brands: {', '.join([getattr(b, 'name', str(b)) for b in brand_objects])}" if brand_objects else ""
                                        self.stdout.write(f'[DRY RUN] Would update: {name}{brands_display}')
                                    updated_count += 1
                                else:
                                    self.stdout.write(
                                        self.style.WARNING(f'⚠ Skipped (already exists): {name}')
                                    )
                                    skipped_count += 1
                        
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Row {row_num}: Error processing {row.get("Name", "Unknown")}: {e}')
                            )
                            error_count += 1
                            continue
                    
                    if dry_run:
                        # Rollback transaction for dry run
                        transaction.set_rollback(True)
        
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {e}')
        
        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('IMPORT SUMMARY:')
        self.stdout.write('='*50)
        self.stdout.write(f'Vendors Created: {created_count}')
        self.stdout.write(f'Vendors Updated: {updated_count}')
        self.stdout.write(f'Vendors Skipped: {skipped_count}')
        self.stdout.write(f'Brands Created: {brands_created_count}')
        self.stdout.write(f'Errors: {error_count}')
        self.stdout.write(f'Total processed: {created_count + updated_count + skipped_count + error_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETE - No data was actually saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nImport completed successfully!'))