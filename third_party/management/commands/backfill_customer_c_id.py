"""
Management command to backfill c_id for existing customers
Run this command after adding the c_id field to Customer model
Uses CSV file to map customer names to specific c_id values
"""

import csv
import os
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db import transaction
from third_party.models import Customer


class Command(BaseCommand):
    help = 'Backfill c_id for existing customers using CSV mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Path to CSV file with customer name and c_id mappings (columns: Customer Name *, Cust_ID)',
            required=True,
        )
        parser.add_argument(
            '--similarity-threshold',
            type=float,
            default=0.8,
            help='Similarity threshold for fuzzy name matching (0.0-1.0, default: 0.8)',
        )

    def similarity(self, a, b):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    def load_csv_mappings(self, csv_file_path):
        """Load customer name to c_id mappings from CSV file"""
        mappings = {}
        
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Check if required columns exist
            if 'Customer Name *' not in reader.fieldnames or 'Cust_ID' not in reader.fieldnames:
                available_columns = ', '.join(reader.fieldnames)
                raise ValueError(
                    f"CSV file must contain 'Customer Name *' and 'Cust_ID' columns. "
                    f"Found columns: {available_columns}"
                )
            
            for row in reader:
                customer_name = row['Customer Name *'].strip()
                c_id = row['Cust_ID'].strip()
                
                if customer_name and c_id:
                    mappings[customer_name] = c_id
        
        return mappings

    def find_best_match(self, customer_name, csv_mappings, threshold):
        """Find the best matching customer name from CSV mappings"""
        best_match = None
        best_score = 0
        
        for csv_name in csv_mappings.keys():
            score = self.similarity(customer_name, csv_name)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = csv_name
        
        return best_match, best_score

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        csv_file = options['csv_file']
        similarity_threshold = options['similarity_threshold']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Load CSV mappings
        try:
            csv_mappings = self.load_csv_mappings(csv_file)
            self.stdout.write(f'Loaded {len(csv_mappings)} customer mappings from CSV')
        except (FileNotFoundError, ValueError) as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        # Get all customers (both with and without c_id for potential conflicts)
        all_customers = Customer.objects.all().order_by('id')
        customers_to_update = []
        
        # Check for existing c_id conflicts
        existing_c_ids = set(Customer.objects.exclude(c_id__isnull=True).exclude(c_id='').values_list('c_id', flat=True))
        csv_c_ids = set(csv_mappings.values())
        conflicting_c_ids = existing_c_ids.intersection(csv_c_ids)
        
        if conflicting_c_ids:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Found {len(conflicting_c_ids)} c_id conflicts: {", ".join(sorted(conflicting_c_ids))}'
                )
            )

        # Process each customer
        matched_count = 0
        unmatched_count = 0
        updated_count = 0
        skipped_count = 0
        
        for customer in all_customers:
            # Skip customers that already have the correct c_id from CSV
            if customer.c_id and customer.c_id in csv_c_ids:
                # Check if the current c_id matches the expected one for this customer
                best_match, score = self.find_best_match(customer.name, csv_mappings, similarity_threshold)
                if best_match and csv_mappings[best_match] == customer.c_id:
                    self.stdout.write(f'✓ Customer "{customer.name}" already has correct c_id: {customer.c_id}')
                    skipped_count += 1
                    continue
            
            # Find best match in CSV
            best_match, score = self.find_best_match(customer.name, csv_mappings, similarity_threshold)
            
            if best_match:
                target_c_id = csv_mappings[best_match]
                
                # Check if target c_id is already assigned to another customer
                existing_customer_with_c_id = Customer.objects.filter(c_id=target_c_id).exclude(id=customer.id).first()
                
                if existing_customer_with_c_id:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Conflict: c_id "{target_c_id}" is already assigned to "{existing_customer_with_c_id.name}". '
                            f'Cannot assign to "{customer.name}" (matched with "{best_match}", similarity: {score:.2f})'
                        )
                    )
                    continue
                
                customers_to_update.append({
                    'customer': customer,
                    'csv_name': best_match,
                    'target_c_id': target_c_id,
                    'similarity': score
                })
                
                self.stdout.write(
                    f'✓ Match found: "{customer.name}" -> "{best_match}" (similarity: {score:.2f}) -> {target_c_id}'
                )
                matched_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'✗ No match found for customer: "{customer.name}"')
                )
                unmatched_count += 1

        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'- Customers matched: {matched_count}')
        self.stdout.write(f'- Customers unmatched: {unmatched_count}')
        self.stdout.write(f'- Customers already correct: {skipped_count}')
        self.stdout.write(f'- Customers to update: {len(customers_to_update)}')

        if not customers_to_update:
            self.stdout.write(self.style.SUCCESS('No customers need to be updated'))
            return

        if not dry_run:
            self.stdout.write('\nProceeding with updates...')
            with transaction.atomic():
                for item in customers_to_update:
                    customer = item['customer']
                    old_c_id = customer.c_id
                    new_c_id = item['target_c_id']
                    
                    customer.c_id = new_c_id
                    customer.save(update_fields=['c_id'])
                    
                    self.stdout.write(
                        f'Updated "{customer.name}": {old_c_id or "None"} -> {new_c_id}'
                    )
                    updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated {updated_count} customers with c_id'
                    )
                )
        else:
            self.stdout.write('\nDry run - showing what would be updated:')
            for item in customers_to_update:
                customer = item['customer']
                old_c_id = customer.c_id
                new_c_id = item['target_c_id']
                
                self.stdout.write(
                    f'Would update "{customer.name}": {old_c_id or "None"} -> {new_c_id}'
                )

        self.stdout.write(
            self.style.SUCCESS('Command completed successfully')
        )
