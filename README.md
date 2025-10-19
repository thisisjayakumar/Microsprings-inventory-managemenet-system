# Microsprings Inventory Management System

A Django-based inventory management system with JWT authentication.

## Features

- ✅ JWT Authentication (Login, Register, Logout, Token Refresh)
- ✅ Custom User Model with extended fields
- ✅ Django REST Framework integration
- ✅ CORS support for frontend integration
- ✅ Admin panel integration
- 🚧 Inventory management (coming soon)

## Setup Instructions

### 1. Virtual Environment
The project already has a virtual environment set up. Activate it:
```bash
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser
```bash
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

## API Endpoints

### Authentication Endpoints
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user
- `POST /api/auth/token/refresh/` - Refresh JWT token
- `GET /api/auth/profile/me/` - Get current user profile
- `PUT /api/auth/profile/` - Update user profile
- `POST /api/auth/change-password/` - Change password
- `GET /api/auth/health/` - Health check

### Inventory Endpoints (Coming Soon)
- `GET /api/inventory/health/` - Health check

## Testing

Run the authentication test script:
```bash
# Make sure the server is running first
python manage.py runserver

# In another terminal
python test_auth.py
```

## Project Structure

```
microsprings_inventory_system/
├── authentication/          # JWT authentication app
│   ├── models.py           # Custom User model
│   ├── serializers.py      # API serializers
│   ├── views.py            # API views
│   ├── urls.py             # URL routing
│   └── admin.py            # Admin configuration
├── inventory/              # Inventory management app
├── microsprings_inventory_system/  # Main project settings
│   ├── settings.py         # Django settings
│   └── urls.py             # Main URL configuration
├── requirements.txt        # Python dependencies
└── manage.py              # Django management script
```

## Technologies Used

- Django 5.2.6
- Django REST Framework 3.15.2
- djangorestframework-simplejwt 5.3.0
- django-cors-headers 4.4.0
- python-decouple 3.8
- Pillow 10.4.0

## Next Steps

1. Implement inventory models (Product, Category, Stock, etc.)
2. Create inventory CRUD operations
3. Add inventory tracking and reporting
4. Implement user permissions and roles
5. Add frontend integration

---

# Enhanced Low-Level System Design for Inventory Management System

## Key Improvements Made

### 1. **Separation of Concerns & Modularity**
- Split complex models into focused, single-responsibility components
- Added proper audit trails and versioning
- Introduced configuration-driven workflows

### 2. **Future-Proofing Architecture**
- Template-based process flows for easy customization
- Event-driven architecture for integrations
- Flexible inventory tracking system

---

## 1. Core Foundation Models

### **User Management (Enhanced)**
```python
# Base User Model (Django's built-in User)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    date_of_joining = models.DateField()
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    permissions = models.JSONField(default=dict)  # Flexible permission system
    
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='roles_assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
```

---

## 2. Product & Specification Models (Redesigned)

### **Flexible Product Hierarchy**
```python
class MaterialType(models.Model):
    name = models.CharField(max_length=50, unique=True)  # 'Coil', 'Sheet', etc.
    properties_schema = models.JSONField(default=dict)  # Define what properties this material type needs
    
class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
class Product(models.Model):
    part_number = models.CharField(max_length=100, unique=True)
    part_name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    material_type = models.ForeignKey(MaterialType, on_delete=models.PROTECT)
    grade = models.CharField(max_length=50)
    unit_of_measurement = models.CharField(max_length=10, choices=[('Pcs', 'Pieces'), ('Kg', 'Kilograms')])
    
    # Dynamic properties based on material type
    properties = models.JSONField(default=dict)  # wire_diameter, thickness, etc.
    
    # Business logic
    is_active = models.BooleanField(default=True)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    standard_pack_size = models.IntegerField(default=1)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

class ProductSpecification(models.Model):
    """Version-controlled product specifications"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    version = models.CharField(max_length=20)
    specifications = models.JSONField()  # All technical specs
    is_current = models.BooleanField(default=True)
    effective_from = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

---

## 3. Process Flow Management (Template-Based)

### **Configurable Workflows**
```python
class ProcessTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    material_types = models.ManyToManyField(MaterialType)  # Which materials use this template
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='1.0')

class ProcessStep(models.Model):
    template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE, related_name='steps')
    step_name = models.CharField(max_length=100)
    sequence_order = models.PositiveIntegerField()
    
    # Step configuration
    is_mandatory = models.BooleanField(default=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True)
    machine_required = models.BooleanField(default=False)
    operator_required = models.BooleanField(default=True)
    
    # Quality parameters
    quality_checks = models.JSONField(default=dict)
    acceptable_scrap_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
class ProcessStepDependency(models.Model):
    step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='dependents')
    dependency_type = models.CharField(max_length=20, choices=[
        ('prerequisite', 'Must Complete Before'),
        ('parallel', 'Can Run Parallel'),
        ('optional', 'Optional Dependency')
    ])

# Link products to their process templates
class ProductProcessMapping(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    process_template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 4. Manufacturing & Production Models (Enhanced)

### **Comprehensive Order Management**
```python
class ManufacturingOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold')
    ]
    
    mo_id = models.CharField(max_length=20, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_ordered = models.PositiveIntegerField()
    
    # Planning
    planned_start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField()
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_supervisor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='supervised_orders')
    shift = models.CharField(max_length=10, choices=[('I', '9AM-5PM'), ('II', '5PM-2AM'), ('III', '2AM-9AM')])
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    
    # Business
    customer_order_reference = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_orders')

class Batch(models.Model):
    batch_id = models.CharField(max_length=20, unique=True)
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, related_name='batches')
    
    # Quantities
    planned_quantity = models.PositiveIntegerField()
    actual_quantity_started = models.PositiveIntegerField(default=0)
    
    # Timing
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    
    # Status
    current_process_step = models.ForeignKey(ProcessStep, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('created', 'Created'),
        ('rm_allocated', 'Raw Material Allocated'),
        ('in_process', 'In Process'),
        ('quality_check', 'Quality Check'),
        ('completed', 'Completed'),
        ('packed', 'Packed'),
        ('dispatched', 'Dispatched')
    ], default='created')
    
    # Metrics
    total_processing_time_minutes = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

class BatchProcessExecution(models.Model):
    """Actual execution of a process step for a batch"""
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='process_executions')
    process_step = models.ForeignKey(ProcessStep, on_delete=models.PROTECT)
    
    # Assignment
    assigned_operator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='operated_processes')
    assigned_machine = models.ForeignKey('Machine', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_supervisor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='supervised_processes')
    
    # Execution
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    
    # Results
    input_quantity = models.PositiveIntegerField()
    output_ok = models.PositiveIntegerField(default=0)
    output_rework = models.PositiveIntegerField(default=0)
    output_scrap = models.PositiveIntegerField(default=0)
    
    # Process parameters
    process_parameters = models.JSONField(default=dict)  # Temperature, pressure, etc.
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled')
    ], default='assigned')
    
    # Quality
    quality_check_passed = models.BooleanField(null=True, blank=True)
    quality_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 5. Resource Management

### **Machines & Equipment**
```python
class Machine(models.Model):
    machine_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    machine_type = models.CharField(max_length=50)
    
    # Capabilities
    supported_processes = models.ManyToManyField(ProcessStep, related_name='compatible_machines')
    capacity_per_hour = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('breakdown', 'Breakdown')
    ], default='available')
    
    # Location
    location = models.CharField(max_length=100)
    
    # Maintenance
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_due = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

class MachineSchedule(models.Model):
    """Track machine utilization"""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='schedule')
    batch_process = models.ForeignKey(BatchProcessExecution, on_delete=models.CASCADE)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled')
```

---

## 6. Inventory Management (Advanced)

### **Multi-Location Inventory Tracking**
```python
class Location(models.Model):
    """Physical locations within the facility"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    location_type = models.CharField(max_length=20, choices=[
        ('rm_store', 'Raw Material Store'),
        ('wip', 'Work In Progress'),
        ('fg_store', 'Finished Goods Store'),
        ('quality', 'Quality Control'),
        ('dispatch', 'Dispatch Area')
    ])
    parent_location = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class InventoryTransaction(models.Model):
    """Universal inventory tracking"""
    TRANSACTION_TYPES = [
        ('inward', 'Inward Receipt'),
        ('outward', 'Outward Issue'),
        ('transfer', 'Location Transfer'),
        ('adjustment', 'Stock Adjustment'),
        ('consumption', 'Process Consumption'),
        ('production', 'Process Output'),
        ('scrap', 'Scrap Generation'),
        ('return', 'Return to Stock')
    ]
    
    transaction_id = models.CharField(max_length=20, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # What
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Where
    location_from = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name='outgoing_transactions')
    location_to = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name='incoming_transactions')
    
    # How Much
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    idempotency_key = models.CharField(
        max_length=64,
        unique=False,              # we'll enforce uniqueness at DB level
        null=True,
        blank=True,
        help_text="Idempotency key for safe retries. Ensures no duplicate transaction on retries."
    )

    # When & Who
    transaction_datetime = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Reference
    reference_type = models.CharField(max_length=20, choices=[
        ('mo', 'Manufacturing Order'),
        ('po', 'Purchase Order'),
        ('process', 'Process Execution'),
        ('adjustment', 'Stock Adjustment')
    ], null=True, blank=True)
    reference_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Additional Info
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [
            models.Index(fields=['transaction_datetime']),
        ]

class StockBalance(models.Model):
    """Current stock levels - calculated/cached view"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)
    
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Allocated but not consumed
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # current - reserved
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'location', 'batch']
```

---

## 7. Quality & Traceability

### **Quality Management**
```python
class QualityCheckTemplate(models.Model):
    name = models.CharField(max_length=100)
    process_step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='quality_templates')
    check_parameters = models.JSONField()  # Define what to check
    acceptance_criteria = models.JSONField()  # Define pass/fail criteria
    is_mandatory = models.BooleanField(default=True)

class QualityCheck(models.Model):
    batch_process = models.ForeignKey(BatchProcessExecution, on_delete=models.CASCADE, related_name='quality_checks')
    template = models.ForeignKey(QualityCheckTemplate, on_delete=models.PROTECT)
    
    # Results
    measured_values = models.JSONField()
    overall_result = models.CharField(max_length=10, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('rework', 'Rework')])
    
    # Inspector
    inspector = models.ForeignKey(User, on_delete=models.PROTECT)
    check_datetime = models.DateTimeField()
    
    # Documentation
    photos = models.JSONField(default=list)  # URLs/paths to photos
    notes = models.TextField(blank=True)

class TraceabilityRecord(models.Model):
    """Complete traceability chain"""
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='traceability_records')
    
    # Upstream traceability
    raw_material_batches = models.JSONField(default=list)  # List of RM batch IDs used
    supplier_lot_numbers = models.JSONField(default=list)
    
    # Process traceability
    process_parameters_history = models.JSONField(default=dict)
    operator_history = models.JSONField(default=list)
    machine_history = models.JSONField(default=list)
    quality_results_summary = models.JSONField(default=dict)
    
    # Environmental conditions
    environmental_data = models.JSONField(default=dict)  # Temperature, humidity during processing
    
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 8. Packaging & Dispatch

### **Advanced Packaging Management**
```python
class PackagingType(models.Model):
    name = models.CharField(max_length=100)
    standard_quantity = models.PositiveIntegerField()
    applicable_products = models.ManyToManyField(Product)
    packaging_material_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)

class PackedItem(models.Model):
    package_id = models.CharField(max_length=30, unique=True)  # For QR code
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='packed_items')
    packaging_type = models.ForeignKey(PackagingType, on_delete=models.PROTECT)
    
    quantity = models.PositiveIntegerField()
    pack_datetime = models.DateTimeField()
    packed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('packed', 'Packed'),
        ('in_fg_store', 'In FG Store'),
        ('dispatched', 'Dispatched')
    ], default='packed')
    
    # QR Code data
    qr_code_data = models.TextField()  # JSON string with all traceability info
    
    # Location tracking
    current_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)

class DispatchOrder(models.Model):
    dispatch_id = models.CharField(max_length=20, unique=True)
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.PROTECT)
    
    # Customer details
    customer_name = models.CharField(max_length=200)
    delivery_address = models.TextField()
    
    # Dispatch details
    packed_items = models.ManyToManyField(PackedItem, related_name='dispatch_orders')
    dispatch_datetime = models.DateTimeField()
    dispatched_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Logistics
    vehicle_number = models.CharField(max_length=20, blank=True)
    driver_details = models.CharField(max_length=200, blank=True)
    
    # Documentation
    dispatch_note_generated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 9. Alerts & Notifications System

### **Event-Driven Notifications**
```python
class AlertRule(models.Model):
    name = models.CharField(max_length=100)
    trigger_condition = models.JSONField()  # Define conditions in JSON
    alert_type = models.CharField(max_length=20, choices=[
        ('low_stock', 'Low Stock'),
        ('delay', 'Process Delay'),
        ('quality_fail', 'Quality Failure'),
        ('machine_down', 'Machine Breakdown'),
        ('custom', 'Custom Rule')
    ])
    
    # Notification settings
    recipient_roles = models.ManyToManyField(Role)
    recipient_users = models.ManyToManyField(User, blank=True)
    notification_methods = models.JSONField(default=list)  # ['email', 'sms', 'in_app']
    
    is_active = models.BooleanField(default=True)
    
class Alert(models.Model):
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE)
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    
    # Context
    related_object_type = models.CharField(max_length=20, null=True, blank=True)  # 'batch', 'mo', 'machine'
    related_object_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed')
    ], default='active')
    
    # Timing
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

class NotificationLog(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    method = models.CharField(max_length=20)  # 'email', 'sms', 'in_app'
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed')
    ], default='pending')
```

---

## 10. Reporting & Analytics Models

### **Business Intelligence Foundation**
```python
class ReportTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    report_type = models.CharField(max_length=20, choices=[
        ('production', 'Production Report'),
        ('inventory', 'Inventory Report'),
        ('quality', 'Quality Report'),
        ('efficiency', 'Efficiency Report')
    ])
    
    # Query definition
    data_source_query = models.TextField()  # SQL or Django ORM query
    parameters = models.JSONField(default=dict)  # User-configurable parameters
    
    # Visualization
    chart_config = models.JSONField(default=dict)
    
    # Access
    accessible_roles = models.ManyToManyField(Role)
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

class ScheduledReport(models.Model):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    # Schedule
    schedule_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Cron')
    ])
    cron_expression = models.CharField(max_length=100, blank=True)
    
    # Parameters
    parameter_values = models.JSONField(default=dict)
    
    # Recipients
    recipients = models.ManyToManyField(User)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
```

Sync System:
1. Validate [ python3 manage.py validate_sync --action validate ]
2. Sync [ python3 manage.py validate_sync --action sync ]
3. Repair Sync - [ python3 manage.py fix_schema --action repair --backup ]
4. Dry run [ python3 manage.py validate_sync --action sync --dry-run ]
5.Report [ manage.py validate_sync --action report --output-file sync_report.json ]

---

## Key Architectural Benefits

### 1. **Scalability**
- **Horizontal scaling**: Models are designed to handle large datasets efficiently
- **Vertical scaling**: Flexible JSON fields allow adding new attributes without schema changes
- **Microservices ready**: Clear boundaries between modules

### 2. **Maintainability**
- **Single responsibility**: Each model has a focused purpose
- **Audit trails**: Complete change tracking across all entities
- **Version control**: Product specifications and process templates are versioned

### 3. **Flexibility**
- **Configuration-driven**: Process flows, quality checks, and alerts are configurable
- **Multi-tenant ready**: Can be extended to support multiple facilities
- **Integration ready**: Event-driven architecture supports future integrations

### 4. **Business Intelligence**
- **Rich data model**: Supports complex analytics and reporting
- **Real-time capabilities**: Inventory transactions and alerts support real-time monitoring
- **Traceability**: Complete chain of custody from raw material to dispatch

### 5. **Operational Excellence**
- **Resource optimization**: Machine and operator scheduling built-in
- **Quality assurance**: Integrated quality management with configurable checks
- **Exception handling**: Comprehensive alert system for proactive management

---

## Implementation Recommendations

### Phase 1: Core Foundation
1. User management and authentication
2. Basic product and inventory models
3. Simple manufacturing order flow

### Phase 2: Process Management
1. Template-based process flows
2. Machine scheduling
3. Quality management

### Phase 3: Advanced Features
1. Alert and notification system
2. Advanced reporting
3. Mobile optimization

### Phase 4: Analytics & Integration
1. Business intelligence dashboards
2. API development for integrations
3. Advanced traceability features

This design provides a robust foundation that can grow with your business needs while maintaining clean separation of concerns and supporting future requirements efficiently.
