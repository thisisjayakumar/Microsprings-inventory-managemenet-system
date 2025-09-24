from django.core.management.base import BaseCommand
import pandas as pd
import os
from your_app.models import Process, SubProcess

class Command(BaseCommand):
    help = 'Import process and subprocess data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to Excel file containing process data',
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
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            processes_created = 0
            subprocesses_created = 0
            
            for index, row in df.iterrows():
                try:
                    # Get process name from second column (assuming first is S.no)
                    process_name = str(row.iloc[1]).strip()
                    if pd.isna(process_name) or process_name == '' or process_name.lower() == 'nan':
                        continue
                    
                    # Create or get process
                    process_code = process_name.upper().replace(' ', '_')[:20]
                    process, created = Process.objects.get_or_create(
                        name=process_name,
                        defaults={'code': process_code}
                    )
                    
                    if created:
                        processes_created += 1
                        self.stdout.write(f'Created process: {process_name}')
                    
                    # Process subprocesses (from 3rd column onwards)
                    for col_index in range(2, len(row)):
                        subprocess_name = str(row.iloc[col_index]).strip()
                        
                        # Skip empty cells
                        if pd.isna(subprocess_name) or subprocess_name == '' or subprocess_name.lower() == 'nan':
                            continue
                        
                        # Create subprocess
                        subprocess_code = f"{process_code}_{subprocess_name.upper().replace(' ', '_')}"[:50]
                        subprocess, created = SubProcess.objects.get_or_create(
                            process=process,
                            name=subprocess_name,
                            defaults={'code': subprocess_code}
                        )
                        
                        if created:
                            subprocesses_created += 1
                            self.stdout.write(f'  Created subprocess: {subprocess_name}')
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {index + 1}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {processes_created} processes and {subprocesses_created} subprocesses'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading Excel file: {str(e)}')
            )