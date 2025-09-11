from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.hashers import make_password
from authentication.models import CustomUser, UserProfile, Role, UserRole, ProcessSupervisor
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create demo users for MSP-ERP system testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of demo users to create (default: 20)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(f'Creating {count} demo users...')
        
        # Demo user templates
        user_templates = [
            # Managers
            {
                'role': 'manager',
                'department': 'admin',
                'users': [
                    ('John', 'Manager', 'john.manager@microsprings.com', 'MGR001'),
                    ('Sarah', 'Wilson', 'sarah.wilson@microsprings.com', 'MGR002'),
                ]
            },
            # Supervisors
            {
                'role': 'supervisor',
                'department': 'coiling',
                'users': [
                    ('Mike', 'Supervisor', 'mike.coiling@microsprings.com', 'SUP001'),
                    ('Lisa', 'Chen', 'lisa.chen@microsprings.com', 'SUP002'),
                ]
            },
            {
                'role': 'supervisor',
                'department': 'tempering',
                'users': [
                    ('David', 'Smith', 'david.tempering@microsprings.com', 'SUP003'),
                ]
            },
            {
                'role': 'supervisor',
                'department': 'plating',
                'users': [
                    ('Anna', 'Johnson', 'anna.plating@microsprings.com', 'SUP004'),
                ]
            },
            {
                'role': 'supervisor',
                'department': 'packing',
                'users': [
                    ('Robert', 'Brown', 'robert.packing@microsprings.com', 'SUP005'),
                ]
            },
            # Store Managers
            {
                'role': 'store_manager',
                'department': 'rm_store',
                'users': [
                    ('Emily', 'Davis', 'emily.rmstore@microsprings.com', 'STM001'),
                ]
            },
            {
                'role': 'store_manager',
                'department': 'fg_store',
                'users': [
                    ('James', 'Miller', 'james.fgstore@microsprings.com', 'STM002'),
                ]
            },
            # Operators
            {
                'role': 'operator',
                'department': 'coiling',
                'users': [
                    ('Tom', 'Anderson', 'tom.coiling@microsprings.com', 'OP001'),
                    ('Maria', 'Garcia', 'maria.coiling@microsprings.com', 'OP002'),
                    ('Chris', 'Taylor', 'chris.coiling@microsprings.com', 'OP003'),
                ]
            },
            {
                'role': 'operator',
                'department': 'tempering',
                'users': [
                    ('Jennifer', 'White', 'jennifer.tempering@microsprings.com', 'OP004'),
                    ('Michael', 'Lee', 'michael.tempering@microsprings.com', 'OP005'),
                ]
            },
            {
                'role': 'operator',
                'department': 'plating',
                'users': [
                    ('Jessica', 'Martinez', 'jessica.plating@microsprings.com', 'OP006'),
                    ('Daniel', 'Wilson', 'daniel.plating@microsprings.com', 'OP007'),
                ]
            },
            {
                'role': 'operator',
                'department': 'packing',
                'users': [
                    ('Ashley', 'Moore', 'ashley.packing@microsprings.com', 'OP008'),
                    ('Ryan', 'Jackson', 'ryan.packing@microsprings.com', 'OP009'),
                ]
            },
        ]
        
        shifts = ['I', 'II', 'III']
        designations = {
            'manager': 'Production Manager',
            'supervisor': 'Process Supervisor',
            'store_manager': 'Store Manager',
            'operator': 'Machine Operator'
        }
        
        created_count = 0
        
        try:
            with transaction.atomic():
                for template in user_templates:
                    role_name = template['role']
                    department = template['department']
                    
                    try:
                        role = Role.objects.get(name=role_name)
                    except Role.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(f'Role {role_name} not found. Run setup_roles first.')
                        )
                        continue
                    
                    for first_name, last_name, email, emp_id in template['users']:
                        if created_count >= count:
                            break
                        
                        # Skip if user exists
                        if CustomUser.objects.filter(email=email).exists():
                            continue
                        
                        # Create user
                        user = CustomUser.objects.create(
                            username=email,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            password=make_password('demo123'),  # Default demo password
                            is_active=True
                        )
                        
                        # Create profile
                        UserProfile.objects.create(
                            user=user,
                            employee_id=emp_id,
                            designation=designations[role_name],
                            department=department,
                            shift=random.choice(shifts) if role_name == 'operator' else None,
                            date_of_joining=date.today() - timedelta(days=random.randint(30, 365)),
                            phone_number=f'+1-555-{random.randint(1000, 9999)}',
                            is_active=True
                        )
                        
                        # Assign role
                        UserRole.objects.create(
                            user=user,
                            role=role,
                            assigned_by=None,
                            is_active=True
                        )
                        
                        # Create process supervisor assignments for supervisors
                        if role_name == 'supervisor':
                            process_names = {
                                'coiling': ['Coiling Setup', 'Coiling Operation', 'Coiling QC'],
                                'tempering': ['Tempering Setup', 'Tempering Process', 'Tempering QC'],
                                'plating': ['Plating Preparation', 'Plating Process', 'Plating QC'],
                                'packing': ['Packing Setup', 'Packing Process', 'Label Printing']
                            }
                            
                            ProcessSupervisor.objects.create(
                                supervisor=user,
                                process_names=process_names.get(department, []),
                                department=department,
                                is_active=True
                            )
                        
                        created_count += 1
                        self.stdout.write(f'Created: {email} ({role_name})')
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created {created_count} demo users!')
                )
                self.stdout.write(
                    self.style.WARNING('Default password for all demo users: demo123')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating demo users: {str(e)}')
            )
