# Generated migration to fix transaction_id length issue

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0013_add_missing_handover_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventorytransaction',
            name='transaction_id',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]

