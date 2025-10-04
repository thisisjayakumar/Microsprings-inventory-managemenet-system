# Generated manually to add customer_c_id field

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_product_customer'),
        ('third_party', '0006_alter_customer_c_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='customer_c_id',
            field=models.ForeignKey(
                blank=True, 
                help_text='Customer associated with this product (references c_id)', 
                null=True, 
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='products', 
                to='third_party.customer', 
                to_field='c_id'
            ),
        ),
    ]