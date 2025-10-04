# Generated manually to handle c_id field addition properly

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party', '0004_customer'),
    ]

    operations = [
        # Add c_id field as nullable first
        migrations.AddField(
            model_name='customer',
            name='c_id',
            field=models.CharField(
                blank=True, 
                editable=False, 
                help_text='Auto-generated customer ID (C_001, C_002, etc.)', 
                max_length=10, 
                null=True,
                unique=False  # Not unique initially
            ),
        ),
    ]
