# Generated manually to remove old customer field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manufacturing', '0012_migrate_customer_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='manufacturingorder',
            name='customer',
        ),
    ]
