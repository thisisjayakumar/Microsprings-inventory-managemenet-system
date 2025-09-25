from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class ManufacturingOrder(models.Model):
    """
    Manufacturing Order (MO) - Production orders for finished goods
    Based on the Production Head Functions workflow
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('gm_approved', 'GM Approved'),
        ('rm_allocated', 'RM Allocated'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    SHIFT_CHOICES = [
        ('I', '9AM-5PM'),
        ('II', '5PM-2AM'),
        ('III', '2AM-9AM')
    ]
    
    # Auto-generated fields
    mo_id = models.CharField(max_length=20, unique=True, editable=False)
    date_time = models.DateTimeField(auto_now_add=True)
    
    # Product details
    product_code = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='manufacturing_orders')
    quantity = models.PositiveIntegerField(help_text="Quantity to manufacture")
    
    # Auto-populated from product selection
    product_type = models.CharField(max_length=50, blank=True, help_text="Auto-filled: Spring/Stamping Part")
    material_name = models.CharField(max_length=100, blank=True, help_text="Auto-filled from product")
    material_type = models.CharField(max_length=20, blank=True, help_text="Auto-filled: Coil/Sheet")
    grade = models.CharField(max_length=50, blank=True, help_text="Auto-filled material grade")
    
    # Conditional fields based on material type
    # For Coil materials
    wire_diameter_mm = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for coil materials"
    )
    thickness_mm = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for sheet materials"
    )
    finishing = models.CharField(max_length=100, blank=True, help_text="Material finishing details")
    manufacturer_brand = models.CharField(max_length=100, blank=True, help_text="Material manufacturer")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    # Raw Material Requirements (calculated)
    loose_fg_stock = models.PositiveIntegerField(default=0, help_text="Available finished goods stock")
    rm_required_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Raw material required in kg")
    
    # Assignment
    assigned_supervisor = models.ForeignKey(
        User, on_delete=models.PROTECT, 
        related_name='supervised_mo_orders',
        help_text="Supervisor allocates operator"
    )
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    
    # Planning dates
    planned_start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField()
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Business details
    customer_order_reference = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Workflow tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    gm_approved_at = models.DateTimeField(null=True, blank=True)
    gm_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gm_approved_mo_orders'
    )
    rm_allocated_at = models.DateTimeField(null=True, blank=True)
    rm_allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rm_allocated_mo_orders'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_mo_orders')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Manufacturing Order'
        verbose_name_plural = 'Manufacturing Orders'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.mo_id:
            # Generate MO ID: MO-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_mo = ManufacturingOrder.objects.filter(
                mo_id__startswith=f'MO-{today}'
            ).order_by('mo_id').last()
            
            if last_mo:
                last_sequence = int(last_mo.mo_id.split('-')[-1])
                sequence = last_sequence + 1
            else:
                sequence = 1
            
            self.mo_id = f'MO-{today}-{sequence:04d}'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mo_id} - {self.product_code.product_code} (Qty: {self.quantity})"


class PurchaseOrder(models.Model):
    """
    Purchase Order (PO) - Orders for raw materials from vendors
    Based on the Production Head Functions workflow
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('gm_approved', 'GM Approved'),
        ('gm_created_po', 'GM Created PO'),
        ('vendor_confirmed', 'Vendor Confirmed'),
        ('partially_received', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ]
    
    MATERIAL_TYPE_CHOICES = [
        ('coil', 'Coil'),
        ('sheet', 'Sheet')
    ]
    
    # Auto-generated fields
    po_id = models.CharField(max_length=20, unique=True, editable=False)
    date_time = models.DateTimeField(auto_now_add=True)
    
    # Material selection
    rm_code = models.ForeignKey(
        'inventory.RawMaterial', 
        on_delete=models.PROTECT, 
        related_name='purchase_orders',
        help_text="Select from dropdown - auto fills other details"
    )
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, blank=True)
    
    # Auto-populated fields based on material selection
    # For Coil materials
    material_auto = models.CharField(max_length=100, blank=True, help_text="Auto-filled")
    grade_auto = models.CharField(max_length=50, blank=True, help_text="Auto-filled")
    wire_diameter_mm_auto = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for coil"
    )
    finishing_auto = models.CharField(max_length=100, blank=True, help_text="Auto-filled finishing")
    manufacturer_brand_auto = models.CharField(max_length=100, blank=True, help_text="Auto-filled manufacturer")
    kg_auto = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Auto-filled weight")
    
    # For Sheet materials  
    thickness_mm_auto = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for sheet"
    )
    sheet_roll_auto = models.CharField(max_length=50, blank=True, help_text="Auto-filled sheet/roll info")
    qty_sheets_auto = models.PositiveIntegerField(null=True, blank=True, help_text="Auto-filled number of sheets")
    
    # Vendor details (filtered based on material availability)
    vendor_name = models.ForeignKey(
        'third_party.Vendor',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Only show vendors who have this material"
    )
    vendor_address_auto = models.TextField(blank=True, help_text="Auto-filled from vendor")
    gst_no_auto = models.CharField(max_length=15, blank=True, help_text="Auto-filled from vendor")
    mob_no_auto = models.CharField(max_length=17, blank=True, help_text="Auto-filled from vendor")
    
    # Order details
    expected_date = models.DateField(help_text="Expected delivery date")
    quantity_ordered = models.PositiveIntegerField(help_text="Quantity to order")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Workflow tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    gm_approved_at = models.DateTimeField(null=True, blank=True)
    gm_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gm_approved_po_orders'
    )
    po_created_at = models.DateTimeField(null=True, blank=True)
    po_created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='po_created_orders'
    )
    
    # Rejection handling
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rejected_po_orders'
    )
    rejection_reason = models.TextField(blank=True)
    
    # Additional details
    terms_conditions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_po_orders')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.po_id:
            # Generate PO ID: PO-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_po = PurchaseOrder.objects.filter(
                po_id__startswith=f'PO-{today}'
            ).order_by('po_id').last()
            
            if last_po:
                last_sequence = int(last_po.po_id.split('-')[-1])
                sequence = last_sequence + 1
            else:
                sequence = 1
            
            self.po_id = f'PO-{today}-{sequence:04d}'
        
        # Auto-populate fields based on rm_code selection
        if self.rm_code:
            self.material_type = self.rm_code.material_type
            self.material_auto = self.rm_code.get_material_name_display()
            self.grade_auto = self.rm_code.grade
            
            if self.rm_code.material_type == 'coil':
                self.wire_diameter_mm_auto = self.rm_code.wire_diameter_mm
                self.kg_auto = self.rm_code.weight_kg
            elif self.rm_code.material_type == 'sheet':
                self.thickness_mm_auto = self.rm_code.thickness_mm
                self.qty_sheets_auto = self.rm_code.quantity
        
        # Auto-populate vendor details
        if self.vendor_name:
            self.vendor_address_auto = self.vendor_name.address
            self.gst_no_auto = self.vendor_name.gst_no
            self.mob_no_auto = self.vendor_name.contact_no
        
        # Calculate total amount
        if self.quantity_ordered and self.unit_price:
            self.total_amount = self.quantity_ordered * self.unit_price
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.po_id} - {self.vendor_name.name} (Qty: {self.quantity_ordered})"


class MOStatusHistory(models.Model):
    """
    Track status changes for Manufacturing Orders
    """
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'MO Status History'
        verbose_name_plural = 'MO Status Histories'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.mo.mo_id}: {self.from_status} → {self.to_status}"


class POStatusHistory(models.Model):
    """
    Track status changes for Purchase Orders
    """
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'PO Status History'
        verbose_name_plural = 'PO Status Histories'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.po.po_id}: {self.from_status} → {self.to_status}"


class MOProcessExecution(models.Model):
    """
    Track process execution for Manufacturing Orders
    Links MO to specific processes and tracks their progress
    """
    EXECUTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, related_name='process_executions')
    process = models.ForeignKey('processes.Process', on_delete=models.CASCADE)
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=EXECUTION_STATUS_CHOICES, default='pending')
    sequence_order = models.IntegerField(help_text="Order of execution for this MO")
    
    # Timing
    planned_start_time = models.DateTimeField(null=True, blank=True)
    planned_end_time = models.DateTimeField(null=True, blank=True)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_process_executions'
    )
    
    # Progress tracking
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['mo', 'sequence_order']
        unique_together = [['mo', 'process']]
    
    def __str__(self):
        return f"{self.mo.mo_id} - {self.process.name} ({self.status})"
    
    @property
    def duration_minutes(self):
        """Calculate actual duration in minutes"""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def is_overdue(self):
        """Check if process is overdue"""
        if self.planned_end_time and self.status not in ['completed', 'skipped']:
            return timezone.now() > self.planned_end_time
        return False


class MOProcessStepExecution(models.Model):
    """
    Track individual process step execution within a process
    """
    STEP_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    QUALITY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('rework_required', 'Rework Required'),
    ]
    
    process_execution = models.ForeignKey(
        MOProcessExecution, 
        on_delete=models.CASCADE, 
        related_name='step_executions'
    )
    process_step = models.ForeignKey('processes.ProcessStep', on_delete=models.CASCADE)
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=STEP_STATUS_CHOICES, default='pending')
    quality_status = models.CharField(max_length=20, choices=QUALITY_STATUS_CHOICES, default='pending')
    
    # Timing
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Quality & Output
    quantity_processed = models.PositiveIntegerField(default=0)
    quantity_passed = models.PositiveIntegerField(default=0)
    quantity_failed = models.PositiveIntegerField(default=0)
    scrap_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Assignment
    operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operated_step_executions'
    )
    
    # Notes and observations
    operator_notes = models.TextField(blank=True)
    quality_notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['process_execution', 'process_step__sequence_order']
        unique_together = [['process_execution', 'process_step']]
    
    def __str__(self):
        return f"{self.process_execution.mo.mo_id} - {self.process_step.step_name} ({self.status})"
    
    @property
    def duration_minutes(self):
        """Calculate step duration in minutes"""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def efficiency_percentage(self):
        """Calculate efficiency based on passed vs processed quantity"""
        if self.quantity_processed > 0:
            return (self.quantity_passed / self.quantity_processed) * 100
        return 0


class MOProcessAlert(models.Model):
    """
    Alerts and notifications for process execution issues
    """
    ALERT_TYPE_CHOICES = [
        ('delay', 'Process Delay'),
        ('quality_issue', 'Quality Issue'),
        ('equipment_failure', 'Equipment Failure'),
        ('material_shortage', 'Material Shortage'),
        ('operator_issue', 'Operator Issue'),
        ('custom', 'Custom Alert'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    process_execution = models.ForeignKey(
        MOProcessExecution, 
        on_delete=models.CASCADE, 
        related_name='alerts'
    )
    step_execution = models.ForeignKey(
        MOProcessStepExecution, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='alerts'
    )
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_alerts'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_alerts'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.process_execution.mo.mo_id} - {self.title} ({self.severity})"