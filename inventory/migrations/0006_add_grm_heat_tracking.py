# Generated migration for GRM and Heat Number tracking

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_productlocation'),
        ('manufacturing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GRMReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grm_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('truck_number', models.CharField(blank=True, help_text='Truck/Van number', max_length=20)),
                ('driver_name', models.CharField(blank=True, max_length=100)),
                ('driver_contact', models.CharField(blank=True, max_length=15)),
                ('receipt_date', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending Receipt'), ('partial', 'Partially Received'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('total_items_received', models.PositiveIntegerField(default=0)),
                ('total_items_expected', models.PositiveIntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('quality_check_passed', models.BooleanField(default=False)),
                ('quality_check_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('purchase_order', models.ForeignKey(help_text='Purchase Order this GRM is for', on_delete=django.db.models.deletion.PROTECT, related_name='grm_receipts', to='manufacturing.purchaseorder')),
                ('quality_check_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quality_checked_grms', to=settings.AUTH_USER_MODEL)),
                ('received_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grm_receipts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'GRM Receipt',
                'verbose_name_plural': 'GRM Receipts',
                'ordering': ['-receipt_date'],
            },
        ),
        migrations.CreateModel(
            name='HeatNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('heat_number', models.CharField(help_text='Heat number from supplier', max_length=50)),
                ('coils_received', models.PositiveIntegerField(default=0, help_text='Number of coils received for this heat number')),
                ('total_weight_kg', models.DecimalField(decimal_places=3, help_text='Total weight in KG for this heat number', max_digits=10)),
                ('sheets_received', models.PositiveIntegerField(default=0, help_text='Number of sheets received (for sheet materials)')),
                ('quality_certificate_number', models.CharField(blank=True, max_length=100)),
                ('test_certificate_date', models.DateField(blank=True, null=True)),
                ('storage_location', models.CharField(blank=True, help_text='Physical location in RM store', max_length=100)),
                ('rack_number', models.CharField(blank=True, max_length=50)),
                ('shelf_number', models.CharField(blank=True, max_length=50)),
                ('is_available', models.BooleanField(default=True, help_text='Is this heat number still available for use')),
                ('consumed_quantity_kg', models.DecimalField(decimal_places=3, default=0, help_text='Quantity consumed from this heat number', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('grm_receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='heat_numbers', to='inventory.grmreceipt')),
                ('raw_material', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='heat_numbers', to='inventory.rawmaterial')),
            ],
            options={
                'verbose_name': 'Heat Number',
                'verbose_name_plural': 'Heat Numbers',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RMStockBalanceHeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_available_quantity_kg', models.DecimalField(decimal_places=3, default=0, help_text='Total available quantity across all heat numbers', max_digits=10)),
                ('total_coils_available', models.PositiveIntegerField(default=0, help_text='Total coils available across all heat numbers')),
                ('total_sheets_available', models.PositiveIntegerField(default=0, help_text='Total sheets available across all heat numbers')),
                ('active_heat_numbers_count', models.PositiveIntegerField(default=0, help_text='Number of active heat numbers with available stock')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('last_transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.inventorytransaction')),
                ('raw_material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='heat_stock_balances', to='inventory.rawmaterial')),
            ],
            options={
                'verbose_name': 'RM Stock Balance (Heat Tracked)',
                'verbose_name_plural': 'RM Stock Balances (Heat Tracked)',
            },
        ),
        migrations.CreateModel(
            name='InventoryTransactionHeat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_kg', models.DecimalField(decimal_places=3, help_text='Quantity in KG for this transaction', max_digits=10)),
                ('coils_count', models.PositiveIntegerField(default=0, help_text='Number of coils involved (for coil materials)')),
                ('sheets_count', models.PositiveIntegerField(default=0, help_text='Number of sheets involved (for sheet materials)')),
                ('grm_number', models.CharField(help_text='GRM number for traceability', max_length=20)),
                ('heat_number', models.ForeignKey(help_text='Specific heat number involved in this transaction', on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='inventory.heatnumber')),
                ('inventory_transaction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='heat_transaction', to='inventory.inventorytransaction')),
            ],
            options={
                'verbose_name': 'Inventory Transaction Heat',
                'verbose_name_plural': 'Inventory Transactions Heat',
            },
        ),
        migrations.AddIndex(
            model_name='grmreceipt',
            index=models.Index(fields=['grm_number'], name='inventory_grmreceipt_grm_number_idx'),
        ),
        migrations.AddIndex(
            model_name='grmreceipt',
            index=models.Index(fields=['receipt_date'], name='inventory_grmreceipt_receipt_date_idx'),
        ),
        migrations.AddIndex(
            model_name='grmreceipt',
            index=models.Index(fields=['status'], name='inventory_grmreceipt_status_idx'),
        ),
        migrations.AddIndex(
            model_name='heatnumber',
            index=models.Index(fields=['heat_number'], name='inventory_heatnumber_heat_number_idx'),
        ),
        migrations.AddIndex(
            model_name='heatnumber',
            index=models.Index(fields=['grm_receipt', 'raw_material'], name='inventory_heatnumber_grm_raw_idx'),
        ),
        migrations.AddIndex(
            model_name='heatnumber',
            index=models.Index(fields=['is_available'], name='inventory_heatnumber_is_available_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorytransactionheat',
            index=models.Index(fields=['heat_number'], name='inventory_inventorytransactionheat_heat_number_idx'),
        ),
        migrations.AddIndex(
            model_name='inventorytransactionheat',
            index=models.Index(fields=['grm_number'], name='inventory_inventorytransactionheat_grm_number_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='heatnumber',
            unique_together={('heat_number', 'grm_receipt', 'raw_material')},
        ),
        migrations.AlterUniqueTogether(
            name='rmstockbalanceheat',
            unique_together={('raw_material',)},
        ),
    ]
