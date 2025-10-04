# Generated manually to migrate customer data from old field to new field

from django.db import migrations


def migrate_customer_data_forward(apps, schema_editor):
    """Copy customer data from old customer field to new customer_c_id field"""
    ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
    Customer = apps.get_model('third_party', 'Customer')
    
    updated_count = 0
    
    for mo in ManufacturingOrder.objects.select_related('customer').all():
        if mo.customer and mo.customer.c_id:
            # Find the customer by c_id and assign to the new field
            try:
                customer = Customer.objects.get(c_id=mo.customer.c_id)
                mo.customer_c_id = customer
                mo.save(update_fields=['customer_c_id'])
                updated_count += 1
            except Customer.DoesNotExist:
                print(f"Warning: Customer with c_id {mo.customer.c_id} not found for MO {mo.mo_id}")
    
    print(f"Migrated customer data for {updated_count} manufacturing orders")


def migrate_customer_data_reverse(apps, schema_editor):
    """Reverse migration - copy data back from customer_c_id to customer"""
    ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
    
    updated_count = 0
    
    for mo in ManufacturingOrder.objects.select_related('customer_c_id').all():
        if mo.customer_c_id:
            mo.customer = mo.customer_c_id
            mo.save(update_fields=['customer'])
            updated_count += 1
    
    print(f"Reversed customer data for {updated_count} manufacturing orders")


class Migration(migrations.Migration):

    dependencies = [
        ('manufacturing', '0011_add_customer_c_id_field'),
    ]

    operations = [
        migrations.RunPython(
            migrate_customer_data_forward,
            migrate_customer_data_reverse,
        ),
    ]
