#!/usr/bin/env python
"""
Quick test script to verify sheet calculation functionality
Run with: python test_sheet_calculation.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')
django.setup()

from products.models import Product
from inventory.models import RawMaterial
from manufacturing.models import ManufacturingOrder
from third_party.models import Customer
from django.contrib.auth import get_user_model

User = get_user_model()

def test_sheet_calculation():
    """Test the sheet calculation functionality"""
    
    print("=" * 80)
    print("SHEET CALCULATION TEST")
    print("=" * 80)
    
    # Get or create a test sheet material
    material, created = RawMaterial.objects.get_or_create(
        material_code='TEST-SHEET-SS304-1.5',
        defaults={
            'material_name': 'Sheet-SS Stainless Steel-304-1.50mm',
            'material_type': 'sheet',
            'grade': '304',
            'thickness_mm': 1.5,
            'length_mm': 2500,
            'breadth_mm': 1250,
            'finishing': 'bright'
        }
    )
    print(f"\n✓ Material: {material}")
    
    # Get or create a test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer for Sheet Calc',
        defaults={
            'industry_type': 'automotive',
            'address': 'Test Address'
        }
    )
    print(f"✓ Customer: {customer}")
    
    # Create or update a test product with sheet calculation data
    product, created = Product.objects.update_or_create(
        product_code='TEST-PRESS-COMPONENT-001',
        defaults={
            'product_type': 'press_component',
            'material': material,
            'customer_c_id': customer,
            # Sheet calculation data
            'whole_sheet_length_mm': 2500,
            'whole_sheet_breadth_mm': 1250,
            'strip_length_mm': 560,
            'strip_breadth_mm': 50,
            'strips_per_sheet': 50,  # How many strips from one whole sheet
            'pcs_per_strip': 13       # How many finished parts per strip
        }
    )
    
    print(f"\n✓ Product: {product}")
    print(f"  - Pcs per Strip: {product.pcs_per_strip}")
    print(f"  - Strips per Sheet: {product.strips_per_sheet}")
    print(f"  - Has Sheet Calc Data: {all([product.strips_per_sheet, product.pcs_per_strip])}")
    
    # Test calculation for different quantities
    test_quantities = [100, 1430, 5000, 10000]
    
    print("\n" + "=" * 80)
    print("STRIP CALCULATION RESULTS (for MO)")
    print("=" * 80)
    
    for qty in test_quantities:
        result = product.calculate_strips_required(qty)
        print(f"\nQuantity: {qty} pieces")
        print(f"  → Strips Required: {result['strips_required']}")
        print(f"  → Total Pieces from Strips: {result['total_pieces_from_strips']}")
        print(f"  → Excess Pieces: {result['excess_pieces']}")
        print(f"  → Pcs per Strip: {result['pcs_per_strip']}")
    
    # Test RM ordering calculation
    print("\n" + "=" * 80)
    print("RM ORDERING CALCULATION RESULTS (sheets for strips)")
    print("=" * 80)
    
    test_strips_needed = [100, 500, 1000, 2000]
    for strips in test_strips_needed:
        result = product.calculate_sheets_for_rm_ordering(strips)
        print(f"\nStrips Needed: {strips}")
        print(f"  → Sheets Required: {result['sheets_required']}")
        print(f"  → Total Strips from Sheets: {result['total_strips_from_sheets']}")
        print(f"  → Excess Strips: {result['excess_strips']}")
        print(f"  → Strips per Sheet: {result['strips_per_sheet']}")
    
    # Test with Manufacturing Order
    print("\n" + "=" * 80)
    print("MANUFACTURING ORDER TEST")
    print("=" * 80)
    
    # Get a test user
    user = User.objects.first()
    if not user:
        print("\n⚠ No user found. Skipping MO test.")
        return
    
    from django.utils import timezone
    from datetime import timedelta
    
    # Create a test MO
    mo = ManufacturingOrder.objects.create(
        product_code=product,
        quantity=5000,
        planned_start_date=timezone.now(),
        planned_end_date=timezone.now() + timedelta(days=7),
        created_by=user
    )
    
    print(f"\n✓ Manufacturing Order Created: {mo.mo_id}")
    print(f"  - Quantity: {mo.quantity}")
    print(f"  - Strips Required (before calc): {mo.strips_required}")
    print(f"  - Total Pieces from Strips (before calc): {mo.total_pieces_from_strips}")
    print(f"  - Excess Pieces (before calc): {mo.excess_pieces}")
    print(f"  - RM Required (kg) (before calc): {mo.rm_required_kg}")
    
    # Manually trigger calculation
    print("\n  Triggering calculate_rm_requirements()...")
    mo.calculate_rm_requirements()
    mo.save()
    
    print(f"\n  - Strips Required (after calc): {mo.strips_required}")
    print(f"  - Total Pieces from Strips (after calc): {mo.total_pieces_from_strips}")
    print(f"  - Excess Pieces (after calc): {mo.excess_pieces}")
    print(f"  - RM Required (kg) (after calc): {mo.rm_required_kg}")
    
    # Clean up test MO
    mo.delete()
    print(f"\n✓ Test MO deleted")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    try:
        test_sheet_calculation()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
