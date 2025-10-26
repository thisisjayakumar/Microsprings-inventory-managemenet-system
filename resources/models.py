from django.db import models
from django.contrib.auth import get_user_model
from utils.enums import MachineStatusChoices, MachineScheduleStatusChoices

User = get_user_model()


class Machine(models.Model):
    machine_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    machine_type = models.CharField(max_length=50)
    
    # Capabilities
    supported_processes = models.ManyToManyField('processes.ProcessStep', related_name='compatible_machines')
    capacity_per_hour = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=MachineStatusChoices.choices, default='available')
    
    # Location
    location = models.CharField(max_length=100)
    
    # Maintenance
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_due = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Machine'
        verbose_name_plural = 'Machines'

    def __str__(self):
        return f"{self.machine_id} - {self.name}"


class MachineSchedule(models.Model):
    """
    Track machine utilization
    """
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='schedule')
    manufacturing_order = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.CASCADE, null=True, blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=MachineScheduleStatusChoices.choices, default='scheduled')

    class Meta:
        verbose_name = 'Machine Schedule'
        verbose_name_plural = 'Machine Schedules'

    def __str__(self):
        return f"{self.machine.machine_id} - {self.batch_process.batch.batch_id}"