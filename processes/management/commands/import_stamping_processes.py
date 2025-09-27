# process/management/commands/import_stamping_processes.py
import csv
from django.core.management.base import BaseCommand
from processes.models import Process, SubProcess, ProcessStep, BOM


class Command(BaseCommand):
    help = "Import stamping product processes from CSV (with dry run option)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to Stamping processes CSV")
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
                product_code = row["ProductCode"].strip()
                sequence = 1

                for col in [c for c in reader.fieldnames if c != "ProductCode"]:
                    subprocess_name = row[col].strip() if row[col] else None
                    if not subprocess_name:
                        continue

                    self.stdout.write(
                        f"[{'DRY' if dry_run else 'SAVE'}] "
                        f"Product={product_code}, Process={col}, SubProcess={subprocess_name}, Seq={sequence}"
                    )

                    if not dry_run:
                        process, _ = Process.objects.get_or_create(
                            name=col.strip(), defaults={"code": abs(hash(col)) % 10000}
                        )

                        subprocess, _ = SubProcess.objects.get_or_create(
                            process=process, name=subprocess_name
                        )

                        step, _ = ProcessStep.objects.update_or_create(
                            step_code=f"{product_code}-{col}-{sequence}",
                            process=process,
                            defaults={
                                "step_name": subprocess_name,
                                "subprocess": subprocess,
                                "sequence_order": sequence,
                            },
                        )

                        BOM.objects.update_or_create(
                            product_code=product_code,
                            type="stamp",
                            process_step=step,
                            defaults={"is_active": True},
                        )

                    sequence += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Stamping processes {'previewed' if dry_run else 'imported/updated'} successfully"
            )
        )
