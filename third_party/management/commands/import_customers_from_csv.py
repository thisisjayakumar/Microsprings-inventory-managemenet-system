"""
Management command to import customer data from CSV file
Expected CSV format:
S.No,Customer Table,Industry Type,GST No.,Address,Point of Contact- Name,Designation,Contact No.,Email _ID,Cust_ID
"""

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from third_party.models import Customer

User = get_user_model()


class Command(BaseCommand):
    help = 'Import customer data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing customer data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing customer data before importing',
        )
        parser.add_argument(
            '--skip-header',
            action='store_true',
            default=True,
            help='Skip the first row (header row) - default is True',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        # Check if file exists
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV file "{csv_file_path}" does not exist.')

        # Clear existing data if requested
        if options['clear'] and not options['dry_run']:
            self.stdout.write('Clearing existing customer data...')
            Customer.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared existing customer data')
            )

        # Get or create a default user for created_by field
        try:
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
        except:
            default_user = None

        # Industry type mapping - map CSV values to our model choices
        industry_mapping = {
            'Brake Industry': 'brake_industry',
            'Automotive': 'automotive',
            'Temperature Sensor': 'temperature_sensor',
            'Instruments': 'instruments',
            'Thermal Ceramics': 'thermal_ceramics',
            'Electric Loco Shed': 'electric_loco_shed',
            'Seating System': 'seating_system',
            'Harness': 'harness',
            'Technology & Services': 'technology_services',
            'TECHNOLOGY': 'technology',
            'Technology': 'technology',
            'Motor Electronics': 'motor_electronics',
            'SPRINGS': 'springs',
            'Springs': 'springs',
            'AUTOMOTIVE': 'automotive',
            'Other': 'other',
        }

        created_count = 0
        updated_count = 0
        error_count = 0
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.reader(csvfile, delimiter=delimiter)
                
                # Skip header if requested
                if options['skip_header']:
                    next(reader, None)
                
                for row_num, row in enumerate(reader, start=2 if options['skip_header'] else 1):
                    try:
                        # Handle empty rows
                        if not any(row) or len(row) < 2:
                            continue
                            
                        # Ensure we have enough columns (pad with empty strings if needed)
                        while len(row) < 10:
                            row.append('')
                        
                        # Extract data from CSV row
                        s_no = row[0].strip() if row[0] else ''
                        customer_name = row[1].strip() if row[1] else ''
                        industry_type_raw = row[2].strip() if row[2] else ''
                        gst_no = row[3].strip() if row[3] else ''
                        address = row[4].strip() if row[4] else ''
                        point_of_contact = row[5].strip() if row[5] else ''
                        designation = row[6].strip() if row[6] else ''
                        contact_no = row[7].strip() if row[7] else ''
                        email_id = row[8].strip() if row[8] else ''
                        cust_id = row[9].strip() if row[9] else ''
                        
                        # Skip rows without customer name
                        if not customer_name:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Skipping - no customer name')
                            )
                            continue
                        
                        # Validate c_id format if provided
                        if cust_id and not cust_id.startswith('C_'):
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Row {row_num}: Invalid c_id format "{cust_id}" for {customer_name}, should start with "C_"'
                                )
                            )
                            cust_id = ''  # Clear invalid c_id
                        
                        # Map industry type
                        industry_type = industry_mapping.get(industry_type_raw, 'other')
                        if industry_type_raw and industry_type == 'other' and industry_type_raw != 'Other':
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Row {row_num}: Unknown industry type "{industry_type_raw}", using "other"'
                                )
                            )
                        
                        # Combine point of contact with designation if both exist
                        if point_of_contact and designation:
                            full_poc = f"{point_of_contact} ({designation})"
                        elif point_of_contact:
                            full_poc = point_of_contact
                        elif designation:
                            full_poc = designation
                        else:
                            full_poc = ''
                        
                        # Clean GST number
                        if gst_no:
                            gst_no = gst_no.upper().replace(' ', '')
                            if len(gst_no) != 15:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'Row {row_num}: Invalid GST number length for {customer_name}: {gst_no}'
                                    )
                                )
                                gst_no = ''  # Clear invalid GST
                        
                        # Split contact numbers if multiple are provided
                        contact_parts = [c.strip() for c in contact_no.split(',') if c.strip()]
                        contact_no_1 = contact_parts[0] if len(contact_parts) > 0 else ''
                        contact_no_2 = contact_parts[1] if len(contact_parts) > 1 else ''
                        
                        # If there are more than 2 contact numbers, add them to contact_no_2
                        if len(contact_parts) > 2:
                            contact_no_2 = ', '.join(contact_parts[1:])
                        
                        customer_data = {
                            'name': customer_name,
                            'c_id': cust_id if cust_id else None,
                            'industry_type': industry_type,
                            'gst_no': gst_no if gst_no else None,
                            'address': address,
                            'point_of_contact': full_poc,
                            'contact_no_1': contact_no_1,
                            'contact_no_2': contact_no_2,
                            'email_id': email_id if email_id else None,
                            'is_active': True,
                            'created_by': default_user
                        }
                        
                        if options['dry_run']:
                            c_id_info = f" -> {cust_id}" if cust_id else ""
                            self.stdout.write(
                                f'Row {row_num}: Would import - {customer_name} ({industry_type}){c_id_info}'
                            )
                            created_count += 1
                        else:
                            # Check for c_id conflicts if c_id is provided
                            if cust_id:
                                existing_customer_with_c_id = Customer.objects.filter(c_id=cust_id).first()
                                if existing_customer_with_c_id and existing_customer_with_c_id.name != customer_name:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f'Row {row_num}: c_id "{cust_id}" already assigned to "{existing_customer_with_c_id.name}". '
                                            f'Cannot assign to "{customer_name}"'
                                        )
                                    )
                                    error_count += 1
                                    continue
                            
                            # Check if customer already exists by name
                            try:
                                existing_customer = Customer.objects.get(name=customer_name)
                                
                                # Update existing customer
                                for field, value in customer_data.items():
                                    if field not in ['name', 'created_by']:  # Don't update name and created_by
                                        setattr(existing_customer, field, value)
                                existing_customer.save()
                                updated_count += 1
                                c_id_info = f" -> {cust_id}" if cust_id else ""
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Updated - {customer_name}{c_id_info}')
                                )
                                
                            except Customer.DoesNotExist:
                                # Create new customer
                                try:
                                    customer = Customer.objects.create(**customer_data)
                                    created_count += 1
                                    c_id_info = f" -> {cust_id}" if cust_id else ""
                                    self.stdout.write(
                                        self.style.SUCCESS(f'Row {row_num}: Created - {customer_name}{c_id_info}')
                                    )
                                except Exception as create_error:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f'Row {row_num}: Error creating customer "{customer_name}": {str(create_error)}'
                                        )
                                    )
                                    error_count += 1
                                    continue
                    
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing row - {str(e)}')
                        )
                        self.stdout.write(f'Row data: {row}')
                        continue

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        # Summary
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nDry run completed!\n'
                    f'Would create: {created_count} customers\n'
                    f'Errors: {error_count} rows'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nImport completed!\n'
                    f'Created: {created_count} customers\n'
                    f'Updated: {updated_count} customers\n'
                    f'Errors: {error_count} rows\n'
                    f'Total processed: {created_count + updated_count} customers'
                )
            )

            # Display database summary
            total_customers = Customer.objects.count()
            active_customers = Customer.objects.filter(is_active=True).count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nDatabase Summary:\n'
                    f'Total customers: {total_customers}\n'
                    f'Active customers: {active_customers}\n'
                    f'Inactive customers: {total_customers - active_customers}'
                )
            )
