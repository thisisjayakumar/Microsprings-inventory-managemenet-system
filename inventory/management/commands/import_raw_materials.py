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
                finishing = row["FINISHING"].strip() if "FINISHING" in row and row["FINISHING"] else None

                # numeric fields
                wire_dia = (
                    row["Wire Diameter"].replace("mm", "").strip()
                    if row.get("Wire Diameter")
                    else None
                )
                thickness = (
                    row["Thickness (mm)"].replace("mm", "").strip()
                    if row.get("Thickness (mm)")
                    else None
                )

                self.stdout.write(
                    f"[{'DRY' if dry_run else 'SAVE'}] "
                    f"Type={material_type}, Name={material_name}, Grade={grade}, "
                    f"WireDia={wire_dia}, Thickness={thickness}, Finishing={finishing}"
                )

                if not dry_run:
                    raw_mat, created = RawMaterial.objects.update_or_create(
                        material_type=material_type,
                        material_name=self._map_material_name(material_name),
                        grade=grade,
                        wire_diameter_mm=float(wire_dia) if wire_dia else None,
                        thickness_mm=float(thickness) if thickness else None,
                        defaults={
                            "finishing": self._map_finishing(finishing),
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Raw materials {'previewed' if dry_run else 'imported/updated'} successfully"
            )
        )

    def _map_material_name(self, name):
        """Map CSV material names to choices in RawMaterial model"""
        name = name.lower()
        if "spring steel" in name or "st " in name:
            return "spring"
        elif "stainless" in name or "ss" in name:
            return "stain"
        elif "mild" in name or "ms" in name:
            return "ms"
        return "spring"  # fallback

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
