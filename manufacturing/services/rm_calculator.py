"""
Raw Material Calculator Service
Calculates RM requirements for Manufacturing Orders based on product specifications
"""
from decimal import Decimal
from typing import Dict, Optional


class RMCalculator:
    """
    Service class to calculate raw material requirements for Manufacturing Orders
    """
    
    @staticmethod
    def calculate_rm_for_coil(
        quantity: int,
        grams_per_product: Decimal,
        tolerance_percentage: Decimal = Decimal('2.00'),
        scrap_percentage: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate RM requirement for coil materials (springs, wire forms, etc.)
        
        Args:
            quantity: Number of products to manufacture
            grams_per_product: Weight in grams per single product
            tolerance_percentage: Tolerance % for RM loss (default 2%)
            scrap_percentage: Expected scrap % (optional)
        
        Returns:
            Dictionary with calculation breakdown:
            {
                'base_grams': Base requirement in grams,
                'base_kg': Base requirement in kg,
                'tolerance_kg': Tolerance amount in kg,
                'total_with_tolerance_kg': Total with tolerance in kg,
                'scrap_kg': Scrap amount in kg (if scrap_percentage provided),
                'final_required_kg': Final RM required in kg
            }
        """
        if not grams_per_product or grams_per_product <= 0:
            raise ValueError("grams_per_product must be greater than 0")
        
        if quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        
        # Step 1: Calculate base requirement
        base_grams = Decimal(quantity) * grams_per_product
        base_kg = base_grams / Decimal('1000')
        
        # Step 2: Add tolerance
        tolerance_amount_kg = base_kg * (tolerance_percentage / Decimal('100'))
        total_with_tolerance_kg = base_kg + tolerance_amount_kg
        
        # Step 3: Add scrap if provided
        scrap_kg = Decimal('0')
        final_required_kg = total_with_tolerance_kg
        
        if scrap_percentage and scrap_percentage > 0:
            scrap_kg = total_with_tolerance_kg * (scrap_percentage / Decimal('100'))
            final_required_kg = total_with_tolerance_kg + scrap_kg
        
        return {
            'base_grams': round(base_grams, 3),
            'base_kg': round(base_kg, 3),
            'tolerance_percentage': tolerance_percentage,
            'tolerance_kg': round(tolerance_amount_kg, 3),
            'total_with_tolerance_kg': round(total_with_tolerance_kg, 3),
            'scrap_percentage': scrap_percentage or Decimal('0'),
            'scrap_kg': round(scrap_kg, 3),
            'final_required_kg': round(final_required_kg, 3)
        }
    
    @staticmethod
    def calculate_rm_for_sheet(
        quantity: int,
        product_length_mm: Decimal,
        product_breadth_mm: Decimal,
        sheet_length_mm: Decimal,
        sheet_breadth_mm: Decimal,
        tolerance_percentage: Decimal = Decimal('2.00'),
        scrap_percentage: Optional[Decimal] = None
    ) -> Dict[str, any]:
        """
        Calculate RM requirement for sheet materials (press components)
        
        Args:
            quantity: Number of products to manufacture
            product_length_mm: Product length in mm
            product_breadth_mm: Product breadth in mm
            sheet_length_mm: Sheet length in mm
            sheet_breadth_mm: Sheet breadth in mm
            tolerance_percentage: Tolerance % for RM loss (default 2%)
            scrap_percentage: Expected scrap % (optional)
        
        Returns:
            Dictionary with calculation breakdown:
            {
                'product_area_mm2': Product area in mm²,
                'sheet_area_mm2': Sheet area in mm²,
                'products_per_sheet': Number of products per sheet (theoretical),
                'base_sheets_required': Base sheets required,
                'tolerance_sheets': Tolerance amount in sheets,
                'total_with_tolerance_sheets': Total with tolerance,
                'scrap_sheets': Scrap amount in sheets,
                'final_required_sheets': Final sheets required (rounded up)
            }
        """
        if not all([product_length_mm, product_breadth_mm, sheet_length_mm, sheet_breadth_mm]):
            raise ValueError("All dimensions must be provided and greater than 0")
        
        if quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        
        # Step 1: Calculate areas
        product_area_mm2 = product_length_mm * product_breadth_mm
        sheet_area_mm2 = sheet_length_mm * sheet_breadth_mm
        
        # Step 2: Calculate how many products can be cut from one sheet
        # This is a simplified calculation - actual cutting may vary based on layout
        products_per_sheet_length = int(sheet_length_mm / product_length_mm)
        products_per_sheet_breadth = int(sheet_breadth_mm / product_breadth_mm)
        products_per_sheet = products_per_sheet_length * products_per_sheet_breadth
        
        if products_per_sheet == 0:
            raise ValueError("Product dimensions are larger than sheet dimensions")
        
        # Step 3: Calculate base sheets required
        base_sheets_required = Decimal(quantity) / Decimal(products_per_sheet)
        
        # Step 4: Add tolerance
        tolerance_sheets = base_sheets_required * (tolerance_percentage / Decimal('100'))
        total_with_tolerance_sheets = base_sheets_required + tolerance_sheets
        
        # Step 5: Add scrap if provided
        scrap_sheets = Decimal('0')
        final_required_sheets = total_with_tolerance_sheets
        
        if scrap_percentage and scrap_percentage > 0:
            scrap_sheets = total_with_tolerance_sheets * (scrap_percentage / Decimal('100'))
            final_required_sheets = total_with_tolerance_sheets + scrap_sheets
        
        # Round up to nearest whole sheet
        import math
        final_required_sheets_rounded = math.ceil(final_required_sheets)
        
        return {
            'product_area_mm2': round(product_area_mm2, 3),
            'sheet_area_mm2': round(sheet_area_mm2, 3),
            'products_per_sheet': products_per_sheet,
            'base_sheets_required': round(base_sheets_required, 3),
            'tolerance_percentage': tolerance_percentage,
            'tolerance_sheets': round(tolerance_sheets, 3),
            'total_with_tolerance_sheets': round(total_with_tolerance_sheets, 3),
            'scrap_percentage': scrap_percentage or Decimal('0'),
            'scrap_sheets': round(scrap_sheets, 3),
            'final_required_sheets': final_required_sheets_rounded,
            'final_required_sheets_decimal': round(final_required_sheets, 3)
        }
    
    @staticmethod
    def check_rm_availability(
        required_amount: Decimal,
        available_amount: Decimal,
        material_type: str = 'coil'
    ) -> Dict[str, any]:
        """
        Check if sufficient RM is available
        
        Args:
            required_amount: Required amount (kg for coil, sheets for sheet)
            available_amount: Available amount in stock
            material_type: 'coil' or 'sheet'
        
        Returns:
            Dictionary with availability status:
            {
                'is_available': True/False,
                'required': Required amount,
                'available': Available amount,
                'shortage': Shortage amount (if any),
                'unit': 'kg' or 'sheets'
            }
        """
        unit = 'kg' if material_type == 'coil' else 'sheets'
        is_available = available_amount >= required_amount
        shortage = max(Decimal('0'), required_amount - available_amount)
        
        return {
            'is_available': is_available,
            'required': round(required_amount, 3),
            'available': round(available_amount, 3),
            'shortage': round(shortage, 3),
            'unit': unit
        }
