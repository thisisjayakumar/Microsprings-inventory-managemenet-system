from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from inventory.models import RawMaterial, Location, ProductLocation, InventoryTransaction
from products.models import Product
from inventory.utils import generate_transaction_id

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize all raw materials and products to rm_store location with inventory transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to use for creating transactions (defaults to first admin user)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Create all required locations
        locations_to_create = [
            ('RM_STORE', 'rm_store'),
            ('COILING_ZONE', 'coiling_zone'),
            ('TEMPERING_ZONE', 'tempering_zone'),
            ('PLATING_ZONE', 'plating_zone'),
            ('PACKING_ZONE', 'packing_zone'),
            ('QC_ZONE', 'quality_zone'),
            ('PRODUCTION_ZONE', 'production_zone'),
            ('FG_STORE', 'fg'),
            ('DISPATCH_ZONE', 'dispatched')
        ]
        
        created_locations = []
        for code, name in locations_to_create:
            location, created = Location.objects.get_or_create(
                code=code,
                defaults={'location_name': name}
            )
            if created:
                created_locations.append(location)
                self.stdout.write(
                    self.style.SUCCESS(f'Created location: {location}')
                )
        
        if created_locations:
            self.stdout.write(f'Created {len(created_locations)} new locations')
        
        # Use rm_store as the default location for initialization
        rm_store_location = Location.objects.get(code='RM_STORE')
        
        # Get user for transactions
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} not found')
                )
                return
        else:
            # Get first admin user
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('No admin user found. Please specify --user-id')
                )
                return
        
        self.stdout.write(f'Using user: {user.username} for transactions')
        
        # Initialize raw materials
        self._initialize_raw_materials(rm_store_location, user, dry_run)
        
        # Initialize products
        self._initialize_products(rm_store_location, user, dry_run)
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Successfully initialized all inventory locations!')
            )

    def _initialize_raw_materials(self, rm_store_location, user, dry_run):
        """Initialize all raw materials to rm_store location"""
        self.stdout.write('\n--- Initializing Raw Materials ---')
        
        raw_materials = RawMaterial.objects.all()
        
        if not raw_materials.exists():
            self.stdout.write('No raw materials found')
            return
        
        for rm in raw_materials:
            # Check if location already exists
            existing_location = ProductLocation.objects.filter(raw_material=rm).first()
            
            if existing_location:
                self.stdout.write(f'RM {rm.material_code} already has location: {existing_location.current_location}')
                continue
            
            # Get quantity from stock balance or use default
            stock_balance = getattr(rm, 'stock_balances', None)
            if stock_balance and hasattr(stock_balance, 'first'):
                stock_record = stock_balance.first()
                quantity = stock_record.available_quantity if stock_record else 0
            else:
                quantity = 0  # Default quantity
            
            self.stdout.write(f'Initializing RM {rm.material_code} with quantity {quantity}')
            
            if not dry_run:
                with transaction.atomic():
                    # Create inventory transaction
                    transaction_id = generate_transaction_id('INIT')
                    inv_transaction = InventoryTransaction.objects.create(
                        transaction_id=transaction_id,
                        transaction_type='inward',
                        product=None,  # This is for raw material
                        location_from=None,
                        location_to=rm_store_location,
                        quantity=quantity,
                        transaction_datetime=timezone.now(),
                        created_by=user,
                        reference_type='adjustment',
                        reference_id='initial_setup',
                        notes=f'Initial location setup for raw material {rm.material_code}'
                    )
                    
                    # Create product location record
                    ProductLocation.objects.create(
                        raw_material=rm,
                        current_location=rm_store_location,
                        quantity=quantity,
                        last_moved_by=user,
                        last_transaction=inv_transaction
                    )

    def _initialize_products(self, rm_store_location, user, dry_run):
        """Initialize all products to rm_store location"""
        self.stdout.write('\n--- Initializing Products ---')
        
        products = Product.objects.all()
        
        if not products.exists():
            self.stdout.write('No products found')
            return
        
        for product in products:
            # Check if location already exists
            existing_location = ProductLocation.objects.filter(product=product).first()
            
            if existing_location:
                self.stdout.write(f'Product {product.product_code} already has location: {existing_location.current_location}')
                continue
            
            # Default quantity for products (they start with 0 until manufactured)
            quantity = 0
            
            self.stdout.write(f'Initializing Product {product.product_code} with quantity {quantity}')
            
            if not dry_run:
                with transaction.atomic():
                    # Create inventory transaction
                    transaction_id = generate_transaction_id('INIT')
                    inv_transaction = InventoryTransaction.objects.create(
                        transaction_id=transaction_id,
                        transaction_type='adjustment',
                        product=product,
                        location_from=None,
                        location_to=rm_store_location,
                        quantity=quantity,
                        transaction_datetime=timezone.now(),
                        created_by=user,
                        reference_type='adjustment',
                        reference_id='initial_setup',
                        notes=f'Initial location setup for product {product.product_code}'
                    )
                    
                    # Create product location record
                    ProductLocation.objects.create(
                        product=product,
                        current_location=rm_store_location,
                        quantity=quantity,
                        last_moved_by=user,
                        last_transaction=inv_transaction
                    )
