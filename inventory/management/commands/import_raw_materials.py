import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from inventory.models import RawMaterial, RMStockBalance


class Command(BaseCommand):
    help = "Import raw materials from CSV into RawMaterial model (with finishing + stock balance)"

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
                    for key in reversed([k for k in row.keys() if "Material Code" in k]):
                        if row.get(key, "").strip():
                            material_code = row[key].strip()
                            break

                if not material_code:
                    self.stdout.write(
                        self.style.WARNING("Skipping row - Material Code is required but empty")
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

                # Additional fields
                weight_kg = None
                available_quantity = None

                if row.get("Weight"):
                    w = row["Weight"].replace("kg", "").strip()
                    try:
                        weight_kg = Decimal(w) if w else None
                    except InvalidOperation:
                        weight_kg = None

                if row.get("available_quantity"):
                    qty_str = row["available_quantity"].replace("kg", "").strip()
                    try:
                        available_quantity = Decimal(qty_str) if qty_str else None
                    except InvalidOperation:
                        available_quantity = None

                self.stdout.write(
                    f"[{'DRY' if dry_run else 'SAVE'}] "
                    f"Code={material_code}, Type={material_type}, Name={material_name}, Grade={grade}, "
                    f"WireDia={wire_dia}, Thickness={thickness}, Weight={weight_kg}, "
                    f"AvailableQty={available_quantity}, Finishing={finishing}"
                )

                if not dry_run:
                    raw_mat, created = RawMaterial.objects.update_or_create(
                        material_code=material_code,
                        defaults={
                            "material_type": material_type,
                            "material_name": material_name,
                            "grade": grade,
                            "wire_diameter_mm": Decimal(wire_dia) if wire_dia else None,
                            "thickness_mm": Decimal(thickness) if thickness else None,
                            "weight_kg": weight_kg,
                            "finishing": self._map_finishing(finishing),
                        },
                    )

                    # Insert or update RMStockBalance
                    if available_quantity is not None:
                        RMStockBalance.objects.update_or_create(
                            raw_material=raw_mat,
                            defaults={"available_quantity": available_quantity},
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
        return None
