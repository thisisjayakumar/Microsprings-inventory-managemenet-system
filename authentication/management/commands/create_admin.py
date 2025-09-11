from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.hashers import make_password
from authentication.models import CustomUser, UserProfile, Role, UserRole
from datetime import date


class Command(BaseCommand):
    help = 'Create admin user for MSP-ERP system'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email address')
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--first-name', type=str, default='System', help='First name')
        parser.add_argument('--last-name', type=str, default='Administrator', help='Last name')
        parser.add_argument('--employee-id', type=str, default='ADMIN001', help='Employee ID')

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        
        if not email:
            email = input('Enter admin email: ')
        
        if not password:
            import getpass
            password = getpass.getpass('Enter admin password: ')
        
        if CustomUser.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists!')
            )
            return
        
        try:
            with transaction.atomic():
                # Create admin user
                admin_user = CustomUser.objects.create(
                    username=email,
                    email=email,
                    first_name=options.get('first_name', 'System'),
                    last_name=options.get('last_name', 'Administrator'),
                    password=make_password(password),
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                
                # Create user profile
                UserProfile.objects.create(
                    user=admin_user,
                    employee_id=options.get('employee_id', 'ADMIN001'),
                    designation='System Administrator',
                    department='admin',
                    date_of_joining=date.today(),
                    phone_number='',
                    is_active=True
                )
                
                # Assign admin role
                admin_role = Role.objects.get(name='admin')
                UserRole.objects.create(
                    user=admin_user,
                    role=admin_role,
                    assigned_by=None,
                    is_active=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created admin user: {email}')
                )
                
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Admin role not found. Please run setup_roles command first.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )
