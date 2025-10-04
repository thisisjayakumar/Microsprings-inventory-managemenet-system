# Generated manually to migrate customer data from old field to new field

from django.db import migrations


def migrate_customer_data_forward(apps, schema_editor):
    """Copy customer data from old customer field to new customer_c_id field"""
    Product = apps.get_model('products', 'Product')
    Customer = apps.get_model('third_party', 'Customer')
    
    updated_count = 0
    
    for product in Product.objects.select_related('customer').all():
        if product.customer and product.customer.c_id:
            # Find the customer by c_id and assign to the new field
            try:
                customer = Customer.objects.get(c_id=product.customer.c_id)
                product.customer_c_id = customer
                product.save(update_fields=['customer_c_id'])
                updated_count += 1
            except Customer.DoesNotExist:
                print(f"Warning: Customer with c_id {product.customer.c_id} not found for product {product.product_code}")
    
    print(f"Migrated customer data for {updated_count} products")


def migrate_customer_data_reverse(apps, schema_editor):
    """Reverse migration - copy data back from customer_c_id to customer"""
    Product = apps.get_model('products', 'Product')
    
    updated_count = 0
    
    for product in Product.objects.select_related('customer_c_id').all():
        if product.customer_c_id:
            product.customer = product.customer_c_id
            product.save(update_fields=['customer'])
            updated_count += 1
    
    print(f"Reversed customer data for {updated_count} products")


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_add_customer_c_id_field'),
    ]

    operations = [
        migrations.RunPython(
            migrate_customer_data_forward,
            migrate_customer_data_reverse,
        ),
    ]
