from django.core.management.base import BaseCommand
import pandas as pd
import os
from your_app.models import Process, SubProcess, ProcessStep

class Command(BaseCommand):
    help = 'Import process steps data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to Excel file containing process steps data',
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
            
            steps_created = 0
            
            for index, row in df.iterrows():
                try:
                    step_name = str(row.get('Step Name', '')).strip()
                    step_code = str(row.get('Step Code', '')).strip()
                    process_name = str(row.get('Process Name', '')).strip()
                    subprocess_name = str(row.get('Subprocess Name', '')).strip()
                    sequence_order = int(row.get('Sequence Order', 1))
                    description = str(row.get('Description', '')).strip()
                    
                    if not step_name or not process_name:
                        continue
                    
                    # Get process
                    try:
                        process = Process.objects.get(name=process_name)
                    except Process.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(f'Process not found: {process_name}')
                        )
                        continue
                    
                    # Get subprocess if specified
                    subprocess = None
                    if subprocess_name and subprocess_name.lower() != 'nan':
                        try:
                            subprocess = SubProcess.objects.get(
                                process=process, 
                                name=subprocess_name
                            )
                        except SubProcess.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(f'Subprocess not found: {subprocess_name}')
                            )
                            continue
                    
                    # Create process step
                    process_step, created = ProcessStep.objects.get_or_create(
                        step_code=step_code,
                        process=process,
                        defaults={
                            'step_name': step_name,
                            'subprocess': subprocess,
                            'sequence_order': sequence_order,
                            'description': description if description != 'nan' else ''
                        }
                    )
                    
                    if created:
                        steps_created += 1
                        self.stdout.write(f'Created process step: {step_name}')
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {index + 1}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported {steps_created} process steps')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading Excel file: {str(e)}')
            )