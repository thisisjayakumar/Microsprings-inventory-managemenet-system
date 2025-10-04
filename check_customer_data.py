import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')
django.setup()

from products.models import Product
from manufacturing.serializers import ProductBasicSerializer

# Check products and their customer data
products = Product.objects.select_related('customer_c_id').all()[:5]

print(f"Found {products.count()} products total")
print("\nChecking first 5 products:")

for product in products:
    print(f"\nProduct: {product.product_code}")
    print(f"  customer_c_id field: {product.customer_c_id}")
    if product.customer_c_id:
        print(f"  Customer name: {product.customer_c_id.name}")
        print(f"  Customer c_id: {product.customer_c_id.c_id}")
    
    # Test serialization
    serializer = ProductBasicSerializer(product)
    data = serializer.data
    print(f"  Serialized customer_name: {data.get('customer_name')}")
    print(f"  Serialized customer_id: {data.get('customer_id')}")
