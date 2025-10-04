import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from products.models import Product
from third_party.models import Customer
from inventory.models import RawMaterial


class Command(BaseCommand):
    help = 'Import products with customer relationships from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing product data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']

        if not os.path.exists(csv_file):
            raise CommandError(f'CSV file "{csv_file}" does not exist.')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made to the database')
            )

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Expected columns: Product_Code, Cust_ID, IPC (Internal Product Code)
                expected_columns = ['Product_Code', 'Cust_ID', 'IPC (Internal Product Code)']
                
                if not all(col in reader.fieldnames for col in expected_columns):
                    raise CommandError(
                        f'CSV file must contain columns: {", ".join(expected_columns)}\n'
                        f'Found columns: {", ".join(reader.fieldnames)}'
                    )

                products_created = 0
                products_updated = 0
                errors = []

                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                        try:
                            product_code = row['Product_Code'].strip()
                            cust_id = row['Cust_ID'].strip()
                            internal_product_code = row['IPC (Internal Product Code)'].strip()

                            if not product_code or not cust_id or not internal_product_code:
                                errors.append(f'Row {row_num}: Missing required data')
                                continue

                            # Find customer
                            try:
                                customer = Customer.objects.get(c_id=cust_id)
                            except Customer.DoesNotExist:
                                errors.append(f'Row {row_num}: Customer with ID "{cust_id}" not found')
                                continue

                            # Check if product exists
                            product, created = Product.objects.get_or_create(
                                product_code=product_code,
                                defaults={
                                    'internal_product_code': internal_product_code,
                                    'customer': customer,
                                    'material': None,  # You'll need to set this separately
                                    'product_type': 'spring',  # Default value
                                    'spring_type': 'tension',  # Default value
                                }
                            )

                            if created:
                                products_created += 1
                                self.stdout.write(
                                    f'Created product: {product_code} for customer {customer.c_id}'
                                )
                            else:
                                # Update existing product with customer and internal code
                                product.customer = customer
                                product.internal_product_code = internal_product_code
                                if not dry_run:
                                    product.save()
                                products_updated += 1
                                self.stdout.write(
                                    f'Updated product: {product_code} with customer {customer.c_id}'
                                )

                        except Exception as e:
                            errors.append(f'Row {row_num}: {str(e)}')

                    if dry_run:
                        # Rollback transaction in dry run mode
                        transaction.set_rollback(True)

                # Print summary
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS(f'IMPORT SUMMARY:'))
                self.stdout.write(f'Products created: {products_created}')
                self.stdout.write(f'Products updated: {products_updated}')
                
                if errors:
                    self.stdout.write(self.style.ERROR(f'Errors encountered: {len(errors)}'))
                    for error in errors:
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
                else:
                    self.stdout.write(self.style.SUCCESS('No errors encountered!'))

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING('\nDRY RUN COMPLETED - No changes were made to the database')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('\nImport completed successfully!')
                    )

        except Exception as e:
            raise CommandError(f'Error processing CSV file: {str(e)}')
