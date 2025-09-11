from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ManufacturingOrder(models.Model):
    """
    Comprehensive order management
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]
    
    SHIFT_CHOICES = [
        ('I', '9AM-5PM'),
        ('II', '5PM-2AM'),
        ('III', '2AM-9AM')
    ]
    
    mo_id = models.CharField(max_length=20, unique=True)
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='manufacturing_orders')
    quantity_ordered = models.PositiveIntegerField()
    
    # Planning
    planned_start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField()
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_supervisor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='supervised_orders')
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Business
    customer_order_reference = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_orders')

    class Meta:
        verbose_name = 'Manufacturing Order'
        verbose_name_plural = 'Manufacturing Orders'

    def __str__(self):
        return f"{self.mo_id} - {self.product.part_number}"


class Batch(models.Model):
    """
    Production batches within manufacturing orders
    """
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('rm_allocated', 'Raw Material Allocated'),
        ('in_process', 'In Process'),
        ('quality_check', 'Quality Check'),
        ('completed', 'Completed'),
        ('packed', 'Packed'),
        ('dispatched', 'Dispatched')
    ]
    
    batch_id = models.CharField(max_length=20, unique=True)
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, related_name='batches')
    
    # Quantities
    planned_quantity = models.PositiveIntegerField()
    actual_quantity_started = models.PositiveIntegerField(default=0)
    
    # Timing
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    
    # Status
    current_process_step = models.ForeignKey('processes.ProcessStep', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    
    # Metrics
    total_processing_time_minutes = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'

    def __str__(self):
        return f"{self.batch_id} - {self.mo.mo_id}"


class BatchProcessExecution(models.Model):
    """
    Actual execution of a process step for a batch
    """
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled')
    ]
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='process_executions')
    process_step = models.ForeignKey('processes.ProcessStep', on_delete=models.PROTECT)
    
    # Assignment
    assigned_operator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='operated_processes')
    assigned_machine = models.ForeignKey('resources.Machine', on_delete=models.SET_NULL, null=True, blank=True)
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    # Quality
    quality_check_passed = models.BooleanField(null=True, blank=True)
    quality_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Batch Process Execution'
        verbose_name_plural = 'Batch Process Executions'

    def __str__(self):
        return f"{self.batch.batch_id} - {self.process_step.step_name}"