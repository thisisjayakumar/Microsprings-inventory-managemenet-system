from django.core.management.base import BaseCommand
import pandas as pd
import os
from processes.models import Material

class Command(BaseCommand):
    help = 'Import materials data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to Excel file containing materials data',
            required=True
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
            
            materials_created = 0
            
            for index, row in df.iterrows():
                try:
                    material_name = str(row.get('Material Name', '')).strip().lower()
                    material_type = str(row.get('Material Type', '')).strip().lower()
                    grade = str(row.get('Grade', '')).strip()
                    supplier_name = str(row.get('Supplier Name', '')).strip()
                    manufacturer = str(row.get('Manufacturer', '')).strip()
                    
                    if not all([material_name, material_type, grade]):
                        continue
                    
                    # Parse conditional fields
                    wire_diameter = row.get('Wire Diameter (mm)', None)
                    weight_kg = row.get('Weight (kg)', None)
                    thickness = row.get('Thickness (mm)', None)
                    quantity = row.get('Quantity', None)
                    
                    # Clean None/NaN values
                    wire_diameter = None if pd.isna(wire_diameter) else float(wire_diameter)
                    weight_kg = None if pd.isna(weight_kg) else float(weight_kg)
                    thickness = None if pd.isna(thickness) else float(thickness)
                    quantity = None if pd.isna(quantity) else float(quantity)
                    
                    # Create material
                    material = Material.objects.create(
                        material_name=material_name,
                        material_type=material_type,
                        grade=grade,
                        supplier_name=supplier_name,
                        manufacturer=manufacturer,
                        wire_diameter_mm=wire_diameter,
                        weight_kg=weight_kg,
                        thickness_mm=thickness,
                        quantity=quantity
                    )
                    
                    materials_created += 1
                    self.stdout.write(f'Created material: {material_name}')
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {index + 1}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported {materials_created} materials')
            )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading file: {str(e)}')
            )