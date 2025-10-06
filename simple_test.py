#!/usr/bin/env python3
"""
Simple test to check if the models are working correctly
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')
django.setup()

def test_models():
    print("Testing models...")

    # Test Product model
    from products.models import Product
    print(f"Product model fields: {[f.name for f in Product._meta.fields if not f.many_to_one and not f.one_to_one]}")

    # Test ManufacturingOrder model
    from manufacturing.models import ManufacturingOrder
    print(f"MO model fields: {[f.name for f in ManufacturingOrder._meta.fields if not f.many_to_one and not f.one_to_one]}")

    print("Models loaded successfully!")

if __name__ == '__main__':
    try:
        test_models()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
