from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import Role


class Command(BaseCommand):
    help = 'Setup MSP-ERP role hierarchy and permissions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up MSP-ERP roles...'))
        
        roles_data = [
            {
                'name': 'admin',
                'description': 'System Administrator with full access',
                'hierarchy_level': 1,
                'permissions': {
                    'users': ['create', 'read', 'update', 'delete'],
                    'roles': ['create', 'read', 'update', 'delete'],
                    'manufacturing': ['create', 'read', 'update', 'delete'],
                    'inventory': ['create', 'read', 'update', 'delete'],
                    'quality': ['create', 'read', 'update', 'delete'],
                    'reports': ['create', 'read', 'update', 'delete'],
                    'settings': ['create', 'read', 'update', 'delete']
                },
                'restricted_departments': []  # No restrictions
            },
            {
                'name': 'manager',
                'description': 'Manager with high limited access - MO Management, Stock, Allocation, Reports, Part Master',
                'hierarchy_level': 2,
                'permissions': {
                    'users': ['read', 'update'],
                    'manufacturing_orders': ['create', 'read', 'update', 'delete'],
                    'inventory': ['read', 'update'],
                    'stock_allocation': ['create', 'read', 'update', 'delete'],
                    'part_master': ['create', 'read', 'update', 'delete'],
                    'reports': ['read'],
                    'quality': ['read'],
                    'processes': ['read']
                },
                'restricted_departments': []  # Access to all departments
            },
            {
                'name': 'supervisor',
                'description': 'Supervisor with limited access to process-specific tasks only',
                'hierarchy_level': 3,
                'permissions': {
                    'processes': ['read', 'update'],
                    'batches': ['read', 'update'],
                    'operators': ['read', 'update'],
                    'quality_checks': ['create', 'read', 'update'],
                    'machine_allocation': ['read', 'update']
                },
                'restricted_departments': ['coiling', 'tempering', 'plating', 'packing']
            },
            {
                'name': 'store_manager',
                'description': 'Store Manager with department-specific access (RM Store, FG Store)',
                'hierarchy_level': 4,
                'permissions': {
                    'inventory': ['create', 'read', 'update'],
                    'stock_transactions': ['create', 'read', 'update'],
                    'purchase_orders': ['read', 'update'],
                    'dispatch_orders': ['create', 'read', 'update'],
                    'packaging': ['read', 'update']
                },
                'restricted_departments': ['rm_store', 'fg_store']
            },
            {
                'name': 'operator',
                'description': 'Operator with minimal access for process execution',
                'hierarchy_level': 5,
                'permissions': {
                    'processes': ['read'],
                    'batches': ['read', 'update'],
                    'quality_checks': ['read'],
                    'machine_operations': ['read', 'update']
                },
                'restricted_departments': ['coiling', 'tempering', 'plating', 'packing', 'quality']
            }
        ]
        
        with transaction.atomic():
            for role_data in roles_data:
                role, created = Role.objects.get_or_create(
                    name=role_data['name'],
                    defaults={
                        'description': role_data['description'],
                        'hierarchy_level': role_data['hierarchy_level'],
                        'permissions': role_data['permissions'],
                        'restricted_departments': role_data['restricted_departments']
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created role: {role.get_name_display()}')
                    )
                else:
                    # Update existing role
                    role.description = role_data['description']
                    role.hierarchy_level = role_data['hierarchy_level']
                    role.permissions = role_data['permissions']
                    role.restricted_departments = role_data['restricted_departments']
                    role.save()
                    self.stdout.write(
                        self.style.WARNING(f'Updated role: {role.get_name_display()}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup MSP-ERP roles!')
        )
