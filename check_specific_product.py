import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')
django.setup()

from products.models import Product
from manufacturing.serializers import ProductBasicSerializer

# Check the specific product from the URL
product_code = "AVASARALA-Gas Actuator Spring-A304622-0.60mm"

try:
    product = Product.objects.select_related('customer_c_id', 'material').get(product_code=product_code)
    print(f"Found product: {product.product_code}")
    print(f"Product ID: {product.id}")
    print(f"customer_c_id field: {product.customer_c_id}")
    
    if product.customer_c_id:
        print(f"Customer name: {product.customer_c_id.name}")
        print(f"Customer c_id: {product.customer_c_id.c_id}")
    else:
        print("No customer assigned to this product")
    
    # Test serialization
    serializer = ProductBasicSerializer(product)
    data = serializer.data
    
    print(f"\nSerialized customer_name: {data.get('customer_name')}")
    print(f"Serialized customer_id: {data.get('customer_id')}")
    
    print(f"\nFull serialized data:")
    import json
    print(json.dumps(data, indent=2, default=str))
    
except Product.DoesNotExist:
    print(f"Product '{product_code}' not found")
    
    # Show available products
    print("\nAvailable products:")
    products = Product.objects.all()[:10]
    for p in products:
        print(f"  - {p.product_code}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
