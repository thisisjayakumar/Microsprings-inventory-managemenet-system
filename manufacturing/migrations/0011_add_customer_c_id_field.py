# Generated manually to add customer_c_id field to ManufacturingOrder

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manufacturing', '0010_add_customer_foreign_key'),
        ('third_party', '0006_alter_customer_c_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manufacturingorder',
            name='customer',
            field=models.ForeignKey(
                blank=True, 
                help_text='Customer for this manufacturing order', 
                null=True, 
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='manufacturing_orders_old', 
                to='third_party.customer'
            ),
        ),
        migrations.AddField(
            model_name='manufacturingorder',
            name='customer_c_id',
            field=models.ForeignKey(
                blank=True, 
                help_text='Customer for this manufacturing order (references c_id)', 
                null=True, 
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='manufacturing_orders', 
                to='third_party.customer', 
                to_field='c_id'
            ),
        ),
    ]
