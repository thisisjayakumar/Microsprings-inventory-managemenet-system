from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product
from processes.models import BOM
from inventory.models import RawMaterial


class Command(BaseCommand):
    help = 'Populate Product table from BOM data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Starting to populate products from BOM data...'))
        
        # Get unique product codes from BOM
        bom_products = BOM.objects.filter(is_active=True).values('product_code', 'type').distinct()
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for bom_product in bom_products:
                product_code = bom_product['product_code']
                product_type = bom_product['type']
                
                # Get the material for this product from BOM
                bom_item_with_material = BOM.objects.filter(
                    product_code=product_code,
                    material__isnull=False,
                    is_active=True
                ).select_related('material').first()
                
                if not bom_item_with_material or not bom_item_with_material.material:
                    self.stdout.write(f"Skipping {product_code} - no material found in BOM")
                    continue
                
                # Check if product already exists
                product, created = Product.objects.get_or_create(
                    product_code=product_code,
                    defaults={
                        'product_type': 'spring' if product_type == 'spring' else 'stamping_part',
                        'material': bom_item_with_material.material
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"Created product: {product_code} with material {bom_item_with_material.material.material_code}")
                else:
                    updated_count += 1
                    self.stdout.write(f"Product already exists: {product_code}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {created_count + updated_count} products. '
                    f'Created: {created_count}, Already existed: {updated_count}'
                )
                )
