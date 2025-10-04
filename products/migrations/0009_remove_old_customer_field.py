# Generated manually to remove old customer field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_migrate_customer_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='customer',
        ),
    ]
