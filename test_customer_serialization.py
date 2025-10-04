#!/usr/bin/env python
"""
Test script to check if customer data is being properly serialized
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')
django.setup()

from products.models import Product
from manufacturing.serializers import ProductBasicSerializer

def test_customer_serialization():
    print("Testing customer serialization...")
    
    # Get a product with customer data
    try:
        product = Product.objects.select_related('customer_c_id', 'material').first()
        if not product:
            print("No products found in database")
            return
        
        print(f"Found product: {product.product_code}")
        print(f"Customer C_ID field: {product.customer_c_id}")
        
        if product.customer_c_id:
            print(f"Customer name: {product.customer_c_id.name}")
            print(f"Customer c_id: {product.customer_c_id.c_id}")
        else:
            print("No customer assigned to this product")
        
        # Test serialization
        serializer = ProductBasicSerializer(product)
        data = serializer.data
        
        print("\nSerialized data:")
        print(f"Customer name: {data.get('customer_name')}")
        print(f"Customer ID: {data.get('customer_id')}")
        
        # Print full serialized data
        print(f"\nFull serialized product data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_customer_serialization()
