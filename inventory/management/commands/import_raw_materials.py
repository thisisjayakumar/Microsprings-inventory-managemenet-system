# inventory/management/commands/import_raw_materials.py
import csv
from django.core.management.base import BaseCommand
from inventory.models import RawMaterial


class Command(BaseCommand):
    help = "Import raw materials from CSV into RawMaterial model (with finishing)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to materials CSV")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to the database",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                material_type = row["Material_Type"].strip().lower()  # Coil / Sheet
                material_name = row["Material_Name"].strip()
                grade = row["Grade"].strip() if row["Grade"] else ""
                finishing = row["Finishing"].strip() if row.get("Finishing") else None
                # Use the last Material Code column (rightmost one)
                material_code = row.get("Material Code", "").strip()
                if not material_code and len([k for k in row.keys() if "Material Code" in k]) > 1:
                    # If there are multiple Material Code columns, use the last non-empty one
                    for key in reversed([k for k in row.keys() if "Material Code" in k]):
                        if row.get(key, "").strip():
                            material_code = row[key].strip()
                            break
                
                # Skip row if material_code is empty (required field)
                if not material_code:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping row - Material Code is required but empty")
                    )
                    continue

                # numeric fields
                wire_dia = (
                    row["Wire Diameter"].replace("mm", "").strip()
                    if row.get("Wire Diameter") and row["Wire Diameter"].strip()
                    else None
                )
                thickness = (
                    row["Thickness"].replace("mm", "").strip()
                    if row.get("Thickness") and row["Thickness"].strip()
                    else None
                )
                
                # Additional fields that might be in CSV
                weight_kg = None
                quantity = None
                
                # Check for weight/quantity columns (these might not exist in all CSVs)
                if row.get("Weight"):
                    weight_str = row["Weight"].replace("kg", "").strip()
                    weight_kg = float(weight_str) if weight_str else None
                    
                if row.get("Quantity"):
                    quantity_str = row["Quantity"].replace("kg", "").strip()
                    quantity = float(quantity_str) if quantity_str else None

                self.stdout.write(
                    f"[{'DRY' if dry_run else 'SAVE'}] "
                    f"Code={material_code}, Type={material_type}, Name={material_name}, Grade={grade}, "
                    f"WireDia={wire_dia}, Thickness={thickness}, Weight={weight_kg}, Quantity={quantity}, Finishing={finishing}"
                )

                if not dry_run:
                    raw_mat, created = RawMaterial.objects.update_or_create(
                        material_code=material_code,
                        defaults={
                            "material_type": material_type,
                            "material_name": material_name,  # Use complete name from CSV
                            "grade": grade,
                            "wire_diameter_mm": float(wire_dia) if wire_dia else None,
                            "thickness_mm": float(thickness) if thickness else None,
                            "weight_kg": weight_kg,
                            "quantity": quantity,
                            "finishing": self._map_finishing(finishing),
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Raw materials {'previewed' if dry_run else 'imported/updated'} successfully"
            )
        )

    def _map_finishing(self, finishing):
        """Map CSV finishing text to RawMaterial.FINISHING_CHOICES"""
        if not finishing:
            return None
        f = finishing.lower()
        if "soap" in f:
            return "soap_coated"
        if "bright" in f:
            return "bright"
        return None  # fallback if not in choices
