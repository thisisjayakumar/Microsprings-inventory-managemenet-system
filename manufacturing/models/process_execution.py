"""
Process Execution Models
Track process execution for Manufacturing Orders
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

from utils.enums import (
    ExecutionStatusChoices,
    StepStatusChoices,
    QualityStatusChoices,
    AlertTypeChoices,
    SeverityChoices
)

logger = logging.getLogger(__name__)
User = get_user_model()


class MOProcessExecution(models.Model):
    """
    Track process execution for Manufacturing Orders
    Links MO to specific processes and tracks their progress
    """
    mo = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.CASCADE, related_name='process_executions')
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
        
        user_roles = user.user_roles.filter(is_active=True).values_list('role__name', flat=True)
        if any(role in ['admin', 'manager', 'production_head'] for role in user_roles):
            return True
        
        if self.assigned_supervisor == user:
            return True
        
        if 'supervisor' in user_roles:
            try:
                user_profile = user.userprofile
                process_supervisor = ProcessSupervisor.objects.get(
                    supervisor=user,
                    department=user_profile.department,
                    is_active=True
                )
                return self.process.name in process_supervisor.process_names
            except:
                pass
        
        return False
    
    def auto_assign_supervisor(self):
        """Auto-assign the active supervisor for today's work center"""
        from processes.models import DailySupervisorStatus
        
        try:
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
        
        if not self.assigned_supervisor:
            return
        
        try:
            today = timezone.now().date()
            
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
            
            if self.status == 'in_progress':
                log.operations_in_progress = F('operations_in_progress') + 1
                log.total_operations = F('total_operations') + 1
            elif self.status == 'completed':
                log.operations_completed = F('operations_completed') + 1
                if log.operations_in_progress > 0:
                    log.operations_in_progress = F('operations_in_progress') - 1
            
            if self.status == 'completed' and self.duration_minutes:
                log.total_processing_time_minutes = F('total_processing_time_minutes') + self.duration_minutes
            
            log.save()
            log.refresh_from_db()
            
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
        
        self.status = 'completed'
        self.actual_end_time = timezone.now()
        self.save()
        
        next_process = self.get_next_process_execution()
        
        if next_process:
            next_process_department = self._get_process_department(next_process.process.name)
            
            if next_process_department:
                next_supervisor = self._find_supervisor_for_department(next_process_department)
                if next_supervisor:
                    next_process.assigned_supervisor = next_supervisor
                    next_process.status = 'pending'
                    next_process.save()
                    
                    return {
                        'moved_to_next_process': True,
                        'next_process': next_process.process.name,
                        'next_supervisor': next_supervisor.full_name,
                        'next_process_execution_id': next_process.id
                    }
        
        packing_users = User.objects.filter(
            user_roles__role__name__in=['packing', 'fg_store'],
            user_roles__is_active=True
        ).first()
        
        if packing_users:
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
    """Track individual process step execution within a process"""
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
    """Alerts and notifications for process execution issues"""
    process_execution = models.ForeignKey(
        MOProcessExecution,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    step_execution = models.ForeignKey(
        MOProcessStepExecution,
        on_delete=models.CASCADE,
        null=True, blank=True,
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

