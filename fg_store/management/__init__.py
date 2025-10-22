from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

from fg_store.models import DispatchBatch, DispatchTransaction, FGStockAlert, DispatchOrder
from manufacturing.models import ManufacturingOrder, Batch
from products.models import Product
from third_party.models import Customer

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for FG Store & Dispatch system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing FG Store data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing FG Store data...')
            DispatchTransaction.objects.all().delete()
            DispatchBatch.objects.all().delete()
            DispatchOrder.objects.all().delete()
            FGStockAlert.objects.all().delete()

        self.stdout.write('Creating sample FG Store data...')

        # Get or create users
        supervisor, created = User.objects.get_or_create(
            email='fg_supervisor@example.com',
            defaults={
                'username': 'fg_supervisor',
                'first_name': 'FG',
                'last_name': 'Supervisor',
                'is_active': True
            }
        )

        store_manager, created = User.objects.get_or_create(
            email='fg_manager@example.com',
            defaults={
                'username': 'fg_manager',
                'first_name': 'FG',
                'last_name': 'Manager',
                'is_active': True
            }
        )

        # Get existing data
        customers = Customer.objects.all()[:5]
        products = Product.objects.all()[:10]
        completed_mos = ManufacturingOrder.objects.filter(status='completed')[:20]

        if not customers.exists():
            self.stdout.write(self.style.WARNING('No customers found. Please create customers first.'))
            return

        if not products.exists():
            self.stdout.write(self.style.WARNING('No products found. Please create products first.'))
            return

        if not completed_mos.exists():
            self.stdout.write(self.style.WARNING('No completed MOs found. Please create and complete some MOs first.'))
            return

        # Create Dispatch Batches
        dispatch_batches = []
        for mo in completed_mos:
            # Create 1-3 batches per MO
            num_batches = random.randint(1, 3)
            for i in range(num_batches):
                batch = DispatchBatch.objects.create(
                    mo=mo,
                    production_batch=mo.batches.first() if mo.batches.exists() else None,
                    product_code=mo.product_code,
                    quantity_produced=random.randint(100, 1000),
                    quantity_packed=random.randint(50, 800),
                    quantity_dispatched=random.randint(0, 200),
                    loose_stock=random.randint(0, 50),
                    status=random.choice(['pending_dispatch', 'partially_dispatched', 'fully_dispatched']),
                    location_in_store=f"Rack-{random.randint(1, 10)}-{random.randint(1, 5)}",
                    packing_date=timezone.now() - timedelta(days=random.randint(1, 30)),
                    packing_supervisor=supervisor,
                    created_by=store_manager
                )
                dispatch_batches.append(batch)

        self.stdout.write(f'Created {len(dispatch_batches)} dispatch batches')

        # Create Dispatch Transactions
        transactions = []
        for batch in dispatch_batches[:15]:  # Create transactions for first 15 batches
            if batch.quantity_dispatched > 0:
                transaction = DispatchTransaction.objects.create(
                    mo=batch.mo,
                    dispatch_batch=batch,
                    customer_c_id=batch.mo.customer_c_id,
                    quantity_dispatched=batch.quantity_dispatched,
                    supervisor_id=supervisor,
                    status=random.choice(['confirmed', 'pending_confirmation']),
                    notes=f'Sample dispatch transaction for {batch.batch_id}',
                    delivery_reference=f'DEL-{random.randint(1000, 9999)}',
                    created_by=store_manager
                )
                if transaction.status == 'confirmed':
                    transaction.confirmed_at = timezone.now() - timedelta(days=random.randint(1, 10))
                    transaction.save()
                transactions.append(transaction)

        self.stdout.write(f'Created {len(transactions)} dispatch transactions')

        # Create Dispatch Orders
        dispatch_orders = []
        for mo in completed_mos[:10]:
            order = DispatchOrder.objects.create(
                mo=mo,
                customer_c_id=mo.customer_c_id,
                total_quantity_ordered=mo.quantity,
                total_quantity_dispatched=random.randint(0, mo.quantity),
                dispatch_date=mo.delivery_date,
                status=random.choice(['draft', 'confirmed', 'partially_dispatched', 'fully_dispatched']),
                special_instructions=f'Special handling required for {mo.product_code.product_code}',
                delivery_address=mo.customer_c_id.address if mo.customer_c_id else '',
                created_by=store_manager
            )
            dispatch_orders.append(order)

        self.stdout.write(f'Created {len(dispatch_orders)} dispatch orders')

        # Create Stock Alerts
        stock_alerts = []
        for product in products[:5]:
            alert_types = ['low_stock', 'expiring', 'overstock']
            alert_type = random.choice(alert_types)
            
            alert_data = {
                'product_code': product,
                'alert_type': alert_type,
                'severity': random.choice(['low', 'medium', 'high', 'critical']),
                'description': f'Alert for {product.product_code} - {alert_type}',
                'is_active': True,
                'created_by': store_manager
            }

            if alert_type == 'low_stock':
                alert_data['min_stock_level'] = random.randint(10, 100)
            elif alert_type == 'overstock':
                alert_data['max_stock_level'] = random.randint(500, 2000)
            elif alert_type == 'expiring':
                alert_data['expiry_days_threshold'] = random.randint(7, 30)

            alert = FGStockAlert.objects.create(**alert_data)
            stock_alerts.append(alert)

        self.stdout.write(f'Created {len(stock_alerts)} stock alerts')

        # Update MO statuses based on dispatch completion
        for mo in completed_mos:
            total_dispatched = DispatchBatch.objects.filter(mo=mo).aggregate(
                total=models.Sum('quantity_dispatched')
            )['total'] or 0
            
            if total_dispatched >= mo.quantity:
                mo.status = 'dispatched'
                mo.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample FG Store data:\n'
                f'- {len(dispatch_batches)} dispatch batches\n'
                f'- {len(transactions)} dispatch transactions\n'
                f'- {len(dispatch_orders)} dispatch orders\n'
                f'- {len(stock_alerts)} stock alerts\n'
                f'- Updated MO statuses based on dispatch completion'
            )
        )
