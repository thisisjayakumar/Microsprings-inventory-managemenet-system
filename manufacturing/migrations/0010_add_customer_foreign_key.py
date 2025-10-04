# Generated manually to add customer foreign key to ManufacturingOrder

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('third_party', '0005_add_customer_c_id'),
        ('manufacturing', '0009_remove_manufacturingorder_customer_order_reference_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='manufacturingorder',
            name='customer',
            field=models.ForeignKey(
                blank=True, 
                help_text='Customer for this manufacturing order', 
                null=True, 
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='manufacturing_orders', 
                to='third_party.customer'
            ),
        ),
        migrations.AlterField(
            model_name='manufacturingorder',
            name='customer_name',
            field=models.CharField(
                blank=True, 
                help_text='Customer name (auto-filled from customer)', 
                max_length=200
            ),
        ),
    ]
