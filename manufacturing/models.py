from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid
from utils.enums import (
    MOStatusChoices, PriorityChoices, ShiftChoices, POStatusChoices,
    MaterialTypeChoices, ExecutionStatusChoices, StepStatusChoices,
    QualityStatusChoices, AlertTypeChoices, SeverityChoices,
    BatchStatusChoices, OutsourcingStatusChoices, MOApprovalWorkflowStatusChoices,
    ProcessAssignmentStatusChoices, BatchAllocationStatusChoices,
    ProcessExecutionActionChoices, FGVerificationStatusChoices,
    RMAllocationStatusChoices
)

User = get_user_model()


class ManufacturingOrder(models.Model):
    """
    Manufacturing Order (MO) - Production orders for finished goods
    Based on the Production Head Functions workflow
    """
    
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
    
    # Sheet-based RM Requirements (for press components using sheet materials)
    strips_required = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of strips required for this MO (for press components)"
    )
    total_pieces_from_strips = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total pieces that will be produced from strips"
    )
    excess_pieces = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Excess pieces due to strip constraints"
    )
    
    # RM Calculation Parameters
    tolerance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.00,
        help_text="Tolerance percentage for RM loss during process (e.g., 2.00 for ±2%)"
    )
    scrap_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected scrap percentage (optional, can be predicted from previous MOs)"
    )
    scrap_rm_weight = models.PositiveIntegerField(
        default=0,
        help_text="Raw material weight sent to scrap for this MO (in grams)"
    )
    
    # RM Release/Receive Tracking
    rm_released_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Actual RM released by RM Store Manager (in kg or sheets)"
    )
    
    # Assignment (optional - assigned later in workflow)
    # NOTE: assigned_rm_store removed - all RM store users see all MOs
    # NOTE: Supervisor is no longer assigned at MO level
    # Supervisors are tracked per work center (Process) in DailySupervisorStatus
    # and linked to operations via MOProcessExecution.assigned_supervisor
    shift = models.CharField(max_length=10, choices=ShiftChoices.choices, null=True, blank=True)
    
    # Planning dates
    planned_start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField()
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=MOStatusChoices.choices, default='on_hold')
    priority = models.CharField(max_length=10, choices=PriorityChoices.choices, default='medium')
    
    # Business details - customer field that references c_id
    customer_c_id = models.ForeignKey(
        'third_party.Customer', 
        to_field='c_id',
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='manufacturing_orders',
        help_text="Customer for this manufacturing order (references c_id)"
    )
    customer_name = models.CharField(max_length=200, blank=True, help_text="Customer name (auto-filled from customer)")
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
    
    def calculate_rm_requirements(self):
        """
        Calculate raw material requirements based on product type and material type
        For sheet-based products, calculates strips required for MO and sheets for RM ordering
        For coil-based products, calculates weight in kg
        """
        if not self.product_code:
            return
        
        product = self.product_code
        
        # For sheet-based press components - calculate strips for MO
        if product.product_type == 'press_component' and product.material_type == 'sheet':
            if product.pcs_per_strip and product.pcs_per_strip > 0:
                strip_calc = product.calculate_strips_required(self.quantity)
                self.strips_required = strip_calc.get('strips_required', 0)
                self.total_pieces_from_strips = strip_calc.get('total_pieces_from_strips', 0)
                self.excess_pieces = strip_calc.get('excess_pieces', 0)
        
        # For coil-based products (springs)
        elif product.material_type == 'coil' and product.grams_per_product:
            # Calculate based on grams per product
            total_grams = self.quantity * product.grams_per_product
            self.rm_required_kg = Decimal(str(total_grams / 1000))  # Convert to kg
            
            # Apply tolerance if set
            if self.tolerance_percentage:
                tolerance_factor = Decimal('1') + (Decimal(str(self.tolerance_percentage)) / Decimal('100'))
                self.rm_required_kg = self.rm_required_kg * tolerance_factor


class PurchaseOrder(models.Model):
    """
    Purchase Order (PO) - Orders for raw materials from vendors
    Based on the Production Head Functions workflow
    """
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
    material_type = models.CharField(max_length=20, choices=MaterialTypeChoices.choices, blank=True)
    
    # Auto-populated fields based on material selection
    # For Coil materials
    material_auto = models.CharField(max_length=100, blank=True, help_text="Auto-filled")
    grade_auto = models.CharField(max_length=50, blank=True, help_text="Auto-filled")
    wire_diameter_mm_auto = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for coil"
    )
    finishing_auto = models.CharField(max_length=100, blank=True, null=True, help_text="Auto-filled finishing")
    manufacturer_brand_auto = models.CharField(max_length=100, blank=True, null=True, help_text="Auto-filled manufacturer")
    kg_auto = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Auto-filled weight")
    
    # For Sheet materials  
    thickness_mm_auto = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Auto-filled for sheet"
    )
    sheet_roll_auto = models.CharField(max_length=50, blank=True, null=True, help_text="Auto-filled sheet/roll info")
    qty_sheets_auto = models.PositiveIntegerField(null=True, blank=True, help_text="Auto-filled number of sheets")
    
    # Vendor details (filtered based on material availability)
    vendor_name = models.ForeignKey(
        'third_party.Vendor',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Only show vendors who have this material"
    )
    vendor_address_auto = models.TextField(blank=True, null=True, help_text="Auto-filled from vendor")
    gst_no_auto = models.CharField(max_length=15, blank=True, null=True, help_text="Auto-filled from vendor")
    mob_no_auto = models.CharField(max_length=17, blank=True, null=True, help_text="Auto-filled from vendor")
    
    # Order details
    expected_date = models.DateField(help_text="Expected delivery date")
    quantity_ordered = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Quantity to order (in kg for coil, sheets for sheet material)"
    )
    quantity_received = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Actual quantity received (set when GRM is created)"
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=POStatusChoices.choices, default='po_initiated')
    
    # Workflow tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_po_orders'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cancelled_po_orders'
    )
    cancellation_reason = models.TextField(blank=True, help_text="Reason for cancellation")
    
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
            self.material_auto = self.rm_code.material_name
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
    mo = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, related_name='process_executions')
    process = models.ForeignKey('processes.Process', on_delete=models.CASCADE)
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=ExecutionStatusChoices.choices, default='pending')
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
    assigned_supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_process_executions',
        help_text="Supervisor assigned to this specific process"
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
    
    def can_user_access(self, user):
        """Check if user can access this process execution"""
        from authentication.models import ProcessSupervisor
        
        # Admin, manager, production_head can access all processes
        user_roles = user.user_roles.filter(is_active=True).values_list('role__name', flat=True)
        if any(role in ['admin', 'manager', 'production_head'] for role in user_roles):
            return True
        
        # Check if user is assigned as supervisor for this process
        if self.assigned_supervisor == user:
            return True
        
        # Check if user is a supervisor for this process's department
        if 'supervisor' in user_roles:
            try:
                user_profile = user.userprofile
                process_supervisor = ProcessSupervisor.objects.get(
                    supervisor=user,
                    department=user_profile.department,
                    is_active=True
                )
                # Check if this process matches the supervisor's process names
                return self.process.name in process_supervisor.process_names
            except:
                pass
        
        return False
    
    def auto_assign_supervisor(self):
        """
        Auto-assign the active supervisor for today's work center to this process execution
        Called when process execution starts
        """
        from processes.models import DailySupervisorStatus
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get today's supervisor status for this process (work center)
            today = timezone.now().date()
            supervisor_status = DailySupervisorStatus.objects.filter(
                date=today,
                work_center=self.process
            ).select_related('active_supervisor').first()
            
            if supervisor_status:
                self.assigned_supervisor = supervisor_status.active_supervisor
                self.save(update_fields=['assigned_supervisor', 'updated_at'])
                
                logger.info(
                    f'Auto-assigned supervisor {supervisor_status.active_supervisor.get_full_name()} '
                    f'to process execution {self.id} ({self.process.name})'
                )
                
                # Update activity log
                self._update_activity_log()
                
                return True
            else:
                logger.warning(
                    f'No supervisor status found for work center {self.process.name} '
                    f'on {today}. Run check_supervisor_attendance command.'
                )
                return False
        except Exception as e:
            logger.error(f'Error auto-assigning supervisor: {str(e)}', exc_info=True)
            return False
    
    def _update_activity_log(self):
        """Update supervisor activity log when operations are handled"""
        from processes.models import SupervisorActivityLog
        from django.db.models import F
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.assigned_supervisor:
            return
        
        try:
            today = timezone.now().date()
            
            # Get or create activity log for today
            log, created = SupervisorActivityLog.objects.get_or_create(
                date=today,
                work_center=self.process,
                active_supervisor=self.assigned_supervisor,
                defaults={
                    'mos_handled': 0,
                    'total_operations': 0,
                    'operations_completed': 0,
                    'operations_in_progress': 0,
                }
            )
            
            # Update counts based on status
            if self.status == 'in_progress':
                log.operations_in_progress = F('operations_in_progress') + 1
                log.total_operations = F('total_operations') + 1
            elif self.status == 'completed':
                log.operations_completed = F('operations_completed') + 1
                if log.operations_in_progress > 0:
                    log.operations_in_progress = F('operations_in_progress') - 1
            
            # Update processing time if completed
            if self.status == 'completed' and self.duration_minutes:
                log.total_processing_time_minutes = F('total_processing_time_minutes') + self.duration_minutes
            
            log.save()
            log.refresh_from_db()
            
            # Update MOs handled count (unique MOs)
            unique_mos = MOProcessExecution.objects.filter(
                process=self.process,
                assigned_supervisor=self.assigned_supervisor,
                actual_start_time__date=today
            ).values('mo').distinct().count()
            
            log.mos_handled = unique_mos
            log.save(update_fields=['mos_handled'])
            
        except Exception as e:
            logger.error(f'Error updating activity log: {str(e)}', exc_info=True)
    
    def get_next_process_execution(self):
        """Get the next process execution in sequence"""
        return MOProcessExecution.objects.filter(
            mo=self.mo,
            sequence_order__gt=self.sequence_order
        ).order_by('sequence_order').first()
    
    def complete_and_move_to_next(self, completed_by_user):
        """Complete this process and move MO to next process or FG store"""
        from authentication.models import ProcessSupervisor
        
        # Mark this process as completed
        self.status = 'completed'
        self.actual_end_time = timezone.now()
        self.save()
        
        # Get next process execution
        next_process = self.get_next_process_execution()
        
        if next_process:
            # Move to next process - assign appropriate supervisor
            next_process_department = self._get_process_department(next_process.process.name)
            
            if next_process_department:
                # Find supervisor for next process department
                next_supervisor = self._find_supervisor_for_department(next_process_department)
                if next_supervisor:
                    next_process.assigned_supervisor = next_supervisor
                    next_process.status = 'pending'
                    next_process.save()
                    
                    # NOTE: MO no longer has assigned_supervisor field
                    # Supervisor tracking is now at process execution level
                    
                    return {
                        'moved_to_next_process': True,
                        'next_process': next_process.process.name,
                        'next_supervisor': next_supervisor.full_name,
                        'next_process_execution_id': next_process.id
                    }
        
        # No next process - move to packing zone (mandatory step before FG store)
        packing_users = User.objects.filter(
            user_roles__role__name__in=['packing', 'fg_store'],
            user_roles__is_active=True
        ).first()
        
        if packing_users:
            # Update MO status to completed (but batches go to packing first)
            self.mo.status = 'completed'
            self.mo.actual_end_date = timezone.now()
            self.mo.save()
            
            return {
                'moved_to_packing': True,
                'packing_user': packing_users.full_name,
                'mo_completed': True,
                'next_step': 'packing'
            }
        
        return {
            'moved_to_packing': False,
            'error': 'No packing or FG store user found'
        }
    
    def _get_process_department(self, process_name):
        """Map process name to department"""
        process_department_mapping = {
            'Coiling Setup': 'coiling',
            'Coiling Operation': 'coiling', 
            'Coiling QC': 'coiling',
            'Tempering Setup': 'tempering',
            'Tempering Process': 'tempering',
            'Tempering QC': 'tempering',
            'Plating Preparation': 'plating',
            'Plating Process': 'plating',
            'Plating QC': 'plating',
            'Packing Setup': 'packing',
            'Packing Process': 'packing',
            'Label Printing': 'packing'
        }
        return process_department_mapping.get(process_name)
    
    def _find_supervisor_for_department(self, department):
        """Find an active supervisor for the given department"""
        from authentication.models import ProcessSupervisor
        
        process_supervisor = ProcessSupervisor.objects.filter(
            department=department,
            is_active=True
        ).first()
        
        return process_supervisor.supervisor if process_supervisor else None


class MOProcessStepExecution(models.Model):
    """
    Track individual process step execution within a process
    """
    process_execution = models.ForeignKey(
        MOProcessExecution, 
        on_delete=models.CASCADE, 
        related_name='step_executions'
    )
    process_step = models.ForeignKey('processes.ProcessStep', on_delete=models.CASCADE)
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=StepStatusChoices.choices, default='pending')
    quality_status = models.CharField(max_length=20, choices=QualityStatusChoices.choices, default='pending')
    
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
        if (self.quantity_processed and self.quantity_processed > 0 and 
            self.quantity_passed is not None):
            return (self.quantity_passed / self.quantity_processed) * 100
        return 0


class MOProcessAlert(models.Model):
    """
    Alerts and notifications for process execution issues
    """
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
    
    alert_type = models.CharField(max_length=20, choices=AlertTypeChoices.choices)
    severity = models.CharField(max_length=10, choices=SeverityChoices.choices, default='medium')
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


class Batch(models.Model):
    """
    Production Batch - Breaks down Manufacturing Orders into manageable production units
    
    Key Concept: 1 MO can have multiple Batches until total batch quantities fulfill MO target quantity
    """
    # Auto-generated unique identifier
    batch_id = models.CharField(max_length=30, unique=True, editable=False)
    
    # Relationships
    mo = models.ForeignKey(
        ManufacturingOrder, 
        on_delete=models.CASCADE, 
        related_name='batches',
        help_text="Parent Manufacturing Order"
    )
    
    # IMPORTANT: Direct product reference for easy access and data integrity
    product_code = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='batches',
        help_text="Product being manufactured in this batch (should match MO product)"
    )
    
    # Quantities
    planned_quantity = models.PositiveIntegerField(
        help_text="Planned quantity for this batch"
    )
    actual_quantity_started = models.PositiveIntegerField(
        default=0,
        help_text="Actual quantity that started production"
    )
    actual_quantity_completed = models.PositiveIntegerField(
        default=0,
        help_text="Actual quantity completed successfully"
    )
    scrap_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Quantity scrapped during production"
    )
    scrap_rm_weight = models.PositiveIntegerField(
        default=0,
        help_text="Raw material weight sent to scrap (in grams)"
    )
    
    # Timing
    planned_start_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Planned start date for this batch"
    )
    planned_end_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Planned completion date for this batch"
    )
    actual_start_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Actual start date"
    )
    actual_end_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Actual completion date"
    )
    
    # Status and Progress
    status = models.CharField(
        max_length=20, 
        choices=BatchStatusChoices.choices, 
        default='created'
    )
    progress_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Overall completion percentage"
    )
    
    # Process tracking
    current_process_step = models.ForeignKey(
        'processes.ProcessStep',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Current process step being executed"
    )
    
    # Assignment
    assigned_operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_batches',
        help_text="Primary operator assigned to this batch"
    )
    assigned_supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_batches',
        help_text="Supervisor overseeing this batch"
    )
    
    # Metrics
    total_processing_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent in processing"
    )
    
    # Additional tracking
    notes = models.TextField(
        blank=True,
        help_text="Any special notes or instructions for this batch"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_batches'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Production Batch'
        verbose_name_plural = 'Production Batches'
        ordering = ['-created_at']
        
        # Ensure data integrity
        indexes = [
            models.Index(fields=['mo', 'status']),
            models.Index(fields=['product_code', 'status']),
            models.Index(fields=['batch_id']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate batch_id if not set
        if not self.batch_id:
            # Format: BATCH-MO_ID-SEQUENCE
            # Example: BATCH-MO-20250927-0001-001
            existing_batches = Batch.objects.filter(
                mo=self.mo
            ).count()
            sequence = existing_batches + 1
            self.batch_id = f"BATCH-{self.mo.mo_id}-{sequence:03d}"
        
        # Validate product_code matches MO product
        if self.mo and self.product_code:
            if self.mo.product_code != self.product_code:
                raise ValueError(
                    f"Batch product_code ({self.product_code}) must match "
                    f"MO product_code ({self.mo.product_code})"
                )
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.batch_id} - {self.product_code.product_code} (Qty: {self.planned_quantity})"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on actual vs planned quantity"""
        if self.planned_quantity and self.planned_quantity > 0 and self.actual_quantity_completed is not None:
            return (self.actual_quantity_completed / self.planned_quantity) * 100
        return 0


class OutsourcingRequest(models.Model):
    """
    Outsourcing Request - Track items sent to external vendors for processing
    """
    # Auto-generated fields
    request_id = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Basic info
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_outsourcing_requests')
    vendor = models.ForeignKey('third_party.Vendor', on_delete=models.PROTECT, related_name='outsourcing_requests')
    
    # Dates
    date_sent = models.DateField(null=True, blank=True)
    expected_return_date = models.DateField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=OutsourcingStatusChoices.choices, default='draft')
    
    # Collection info
    collected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='collected_outsourcing_requests'
    )
    collection_date = models.DateField(null=True, blank=True)
    
    # Contact person at vendor
    vendor_contact_person = models.CharField(max_length=100, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Outsourcing Request'
        verbose_name_plural = 'Outsourcing Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['vendor']),
            models.Index(fields=['created_by']),
            models.Index(fields=['expected_return_date']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate request_id if not set
        if not self.request_id:
            from django.utils import timezone
            now = timezone.now()
            date_str = now.strftime('%Y%m%d')
            
            # Get next sequence number for today
            existing_requests = OutsourcingRequest.objects.filter(
                request_id__startswith=f'OUT-{date_str}'
            ).count()
            sequence = existing_requests + 1
            self.request_id = f'OUT-{date_str}-{sequence:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.request_id} - {self.vendor.name} ({self.get_status_display()})"
    
    @property
    def is_overdue(self):
        """Check if the request is overdue"""
        if self.status in ['returned', 'closed']:
            return False
        from django.utils import timezone
        return self.expected_return_date < timezone.now().date()
    
    @property
    def total_items(self):
        """Get total number of items in this request"""
        return self.items.count()
    
    @property
    def total_qty(self):
        """Get total quantity across all items"""
        return sum(item.qty or 0 for item in self.items.all())
    
    @property
    def total_kg(self):
        """Get total weight across all items"""
        return sum(item.kg or 0 for item in self.items.all())


class OutsourcedItem(models.Model):
    """
    Individual items within an outsourcing request
    """
    request = models.ForeignKey(OutsourcingRequest, on_delete=models.CASCADE, related_name='items')
    
    # Product info
    mo_number = models.CharField(max_length=20, help_text="Manufacturing Order number")
    product_code = models.CharField(max_length=120, help_text="Product code")
    
    # Quantities
    qty = models.PositiveIntegerField(null=True, blank=True, help_text="Quantity in pieces")
    kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Weight in kg")
    
    # Return tracking
    returned_qty = models.PositiveIntegerField(default=0, help_text="Returned quantity in pieces")
    returned_kg = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Returned weight in kg")
    
    # Additional info
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Outsourced Item'
        verbose_name_plural = 'Outsourced Items'
        ordering = ['mo_number', 'product_code']
        indexes = [
            models.Index(fields=['request', 'mo_number']),
            models.Index(fields=['product_code']),
        ]
    
    def __str__(self):
        return f"{self.mo_number} - {self.product_code} (Qty: {self.qty}, Kg: {self.kg})"
    
    def clean(self):
        """Validate that at least qty or kg is provided"""
        if not self.qty and not self.kg:
            from django.core.exceptions import ValidationError
            raise ValidationError("Either quantity or weight must be provided")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# Enhanced Manufacturing Workflow Models

class MOApprovalWorkflow(models.Model):
    """
    Track MO approval workflow from creation to manager approval
    """
    mo = models.OneToOneField(
        ManufacturingOrder, 
        on_delete=models.CASCADE, 
        related_name='approval_workflow'
    )
    
    # Approval tracking
    status = models.CharField(max_length=30, choices=MOApprovalWorkflowStatusChoices.choices, default='pending_manager_approval')
    
    # Manager approval
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_mo_workflows'
    )
    manager_approval_notes = models.TextField(blank=True)
    
    # RM Store allocation
    rm_store_allocated_at = models.DateTimeField(null=True, blank=True)
    rm_store_allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rm_allocated_mo_workflows'
    )
    rm_allocation_notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'MO Approval Workflow'
        verbose_name_plural = 'MO Approval Workflows'
    
    def __str__(self):
        return f"{self.mo.mo_id} - {self.get_status_display()}"


class ProcessAssignment(models.Model):
    """
    Track process assignments by Production Head to operators
    """
    mo_process_execution = models.ForeignKey(
        MOProcessExecution,
        on_delete=models.CASCADE,
        related_name='process_assignments'
    )
    
    # Assignment details
    assigned_operator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='assigned_processes'
    )
    assigned_supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_process_assignments'
    )
    
    # Assignment tracking
    status = models.CharField(max_length=20, choices=ProcessAssignmentStatusChoices.choices, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_process_assignments'
    )
    
    # Acceptance tracking
    accepted_at = models.DateTimeField(null=True, blank=True)
    acceptance_notes = models.TextField(blank=True)
    
    # Reassignment tracking
    previous_operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='previous_process_assignments'
    )
    reassigned_at = models.DateTimeField(null=True, blank=True)
    reassignment_reason = models.TextField(blank=True)
    
    # Completion tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Process Assignment'
        verbose_name_plural = 'Process Assignments'
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.mo_process_execution.mo.mo_id} - {self.mo_process_execution.process.name} -> {self.assigned_operator.email}"


class BatchAllocation(models.Model):
    """
    Track batch allocation from RM Store to specific processes
    """
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    
    # Allocation details
    allocated_to_process = models.ForeignKey(
        'processes.Process',
        on_delete=models.CASCADE,
        related_name='batch_allocations'
    )
    allocated_to_operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='allocated_batches'
    )
    
    # Heat number allocation (for raw materials)
    heat_numbers = models.ManyToManyField(
        'inventory.HeatNumber',
        related_name='batch_allocations',
        blank=True,
        help_text="Heat numbers allocated to this batch"
    )
    
    # Allocation tracking
    status = models.CharField(max_length=20, choices=BatchAllocationStatusChoices.choices, default='allocated')
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_batch_allocations'
    )
    
    # Transfer tracking
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_batch_allocations'
    )
    
    # Location tracking
    current_location = models.CharField(max_length=100, blank=True)
    location_notes = models.TextField(blank=True)
    
    # Audit
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Batch Allocation'
        verbose_name_plural = 'Batch Allocations'
        ordering = ['-allocated_at']
    
    def __str__(self):
        return f"{self.batch.batch_id} -> {self.allocated_to_process.name}"


class ProcessExecutionLog(models.Model):
    """
    Detailed log of process execution by operators
    """
    batch_allocation = models.ForeignKey(
        BatchAllocation,
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    
    # Execution details
    action = models.CharField(max_length=20, choices=ProcessExecutionActionChoices.choices)
    performed_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='process_execution_logs'
    )
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Details
    notes = models.TextField(blank=True)
    quantity_processed = models.PositiveIntegerField(null=True, blank=True)
    quality_status = models.CharField(max_length=20, blank=True)
    
    # Location
    location = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Process Execution Log'
        verbose_name_plural = 'Process Execution Logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.batch_allocation.batch.batch_id} - {self.get_action_display()} by {self.performed_by.email}"


class FinishedGoodsVerification(models.Model):
    """
    Track finished goods verification and quality check
    """
    batch = models.OneToOneField(
        Batch,
        on_delete=models.CASCADE,
        related_name='fg_verification'
    )
    
    # Verification details
    status = models.CharField(max_length=30, choices=FGVerificationStatusChoices.choices, default='pending_verification')
    
    # Quality check
    quality_checked_at = models.DateTimeField(null=True, blank=True)
    quality_checked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quality_checked_batches'
    )
    quality_notes = models.TextField(blank=True)
    
    # Final verification
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_fg_batches'
    )
    verification_notes = models.TextField(blank=True)
    
    # Dispatch tracking
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatched_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_batches'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Finished Goods Verification'
        verbose_name_plural = 'Finished Goods Verifications'
    
    def __str__(self):
        return f"{self.batch.batch_id} - {self.get_status_display()}"


class RawMaterialAllocation(models.Model):
    """
    Track raw material allocations/reservations for Manufacturing Orders
    Supports priority-based swapping before MO approval
    """
    # MO and RM references
    mo = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name='rm_allocations',
        help_text="Manufacturing Order this allocation is for"
    )
    raw_material = models.ForeignKey(
        'inventory.RawMaterial',
        on_delete=models.PROTECT,
        related_name='mo_allocations',
        help_text="Raw material being allocated"
    )
    
    # Allocation details
    allocated_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Quantity of raw material allocated in KG"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=RMAllocationStatusChoices.choices,
        default='reserved'
    )
    
    # Swapping tracking
    can_be_swapped = models.BooleanField(
        default=True,
        help_text="Can this allocation be swapped to higher priority MO?"
    )
    swapped_to_mo = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_allocations_received',
        help_text="MO to which this allocation was swapped"
    )
    swapped_at = models.DateTimeField(null=True, blank=True)
    swapped_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_swaps_performed'
    )
    swap_reason = models.TextField(blank=True)
    
    # Locking (on MO approval)
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this allocation was locked (MO approved)"
    )
    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_allocations_locked'
    )
    
    # Allocation timestamps
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_allocations_created'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Raw Material Allocation'
        verbose_name_plural = 'Raw Material Allocations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mo', 'status']),
            models.Index(fields=['raw_material', 'status']),
            models.Index(fields=['can_be_swapped']),
        ]
    
    def __str__(self):
        return f"{self.mo.mo_id} - {self.raw_material.material_code} ({self.allocated_quantity_kg}kg) - {self.status}"
    
    def lock_allocation(self, locked_by_user):
        """
        Lock this allocation (called when MO is approved)
        Once locked, allocation cannot be swapped
        """
        if self.status == 'locked':
            return False
        
        self.status = 'locked'
        self.can_be_swapped = False
        self.locked_at = timezone.now()
        self.locked_by = locked_by_user
        self.save()
        
        # Deduct from available stock
        from inventory.models import RMStockBalanceHeat
        stock_balance = RMStockBalanceHeat.objects.filter(
            raw_material=self.raw_material
        ).first()
        
        if stock_balance:
            stock_balance.total_available_quantity_kg -= self.allocated_quantity_kg
            stock_balance.save()
        
        return True
    
    def swap_to_mo(self, target_mo, swapped_by_user, reason=""):
        """
        Swap this allocation to a higher priority MO
        """
        if not self.can_be_swapped or self.status == 'locked':
            return False, "Allocation is locked and cannot be swapped"
        
        # Check priority
        priority_order = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}
        source_priority = priority_order.get(self.mo.priority, 0)
        target_priority = priority_order.get(target_mo.priority, 0)
        
        if target_priority <= source_priority:
            return False, f"Target MO priority ({target_mo.priority}) must be higher than source MO priority ({self.mo.priority})"
        
        # Perform swap
        old_mo = self.mo
        self.status = 'swapped'
        self.swapped_to_mo = target_mo
        self.swapped_at = timezone.now()
        self.swapped_by = swapped_by_user
        self.swap_reason = reason
        self.can_be_swapped = False
        self.save()
        
        # Create new allocation for target MO
        new_allocation = RawMaterialAllocation.objects.create(
            mo=target_mo,
            raw_material=self.raw_material,
            allocated_quantity_kg=self.allocated_quantity_kg,
            status='reserved',
            can_be_swapped=True,
            allocated_by=swapped_by_user,
            notes=f"Swapped from {old_mo.mo_id} due to higher priority"
        )
        
        return True, f"Allocation swapped from {old_mo.mo_id} to {target_mo.mo_id}"
    
    def release_allocation(self):
        """
        Release this allocation back to stock (e.g., when MO is cancelled)
        """
        if self.status == 'locked':
            # Add back to available stock
            from inventory.models import RMStockBalanceHeat
            stock_balance = RMStockBalanceHeat.objects.filter(
                raw_material=self.raw_material
            ).first()
            
            if stock_balance:
                stock_balance.total_available_quantity_kg += self.allocated_quantity_kg
                stock_balance.save()
        
        self.status = 'released'
        self.can_be_swapped = False
        self.save()
        
        return True


class RMAllocationHistory(models.Model):
    """
    Track history of RM allocation changes (swaps, locks, releases)
    """
    allocation = models.ForeignKey(
        RawMaterialAllocation,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    action = models.CharField(
        max_length=50,
        help_text="Action performed (reserved, swapped, locked, released)"
    )
    from_mo = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_allocation_history_from'
    )
    to_mo = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rm_allocation_history_to'
    )
    
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=3)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'RM Allocation History'
        verbose_name_plural = 'RM Allocation Histories'
        ordering = ['-performed_at']
    
    def __str__(self):
        return f"{self.action} - {self.allocation.mo.mo_id} ({self.performed_at})"