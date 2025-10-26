from django.db import models
from django.contrib.auth import get_user_model
from utils.enums import QualityResultChoices

User = get_user_model()


class QualityCheckTemplate(models.Model):
    """
    Template for quality checks
    """
    name = models.CharField(max_length=100)
    process_step = models.ForeignKey('processes.ProcessStep', on_delete=models.CASCADE, related_name='quality_templates')
    check_parameters = models.JSONField()  # Define what to check
    acceptance_criteria = models.JSONField()  # Define pass/fail criteria
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Quality Check Template'
        verbose_name_plural = 'Quality Check Templates'

    def __str__(self):
        return f"{self.name} - {self.process_step.step_name}"


class QualityCheck(models.Model):
    """
    Actual quality check results
    """
    manufacturing_order = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.CASCADE, related_name='quality_checks', null=True, blank=True)
    template = models.ForeignKey(QualityCheckTemplate, on_delete=models.PROTECT)
    
    # Results
    measured_values = models.JSONField()
    overall_result = models.CharField(max_length=10, choices=QualityResultChoices.choices)
    
    # Inspector
    inspector = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quality_inspections')
    check_datetime = models.DateTimeField()
    
    # Documentation
    photos = models.JSONField(default=list)  # URLs/paths to photos
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Quality Check'
        verbose_name_plural = 'Quality Checks'

    def __str__(self):
        return f"{self.batch_process.batch.batch_id} - {self.template.name} - {self.overall_result}"


class TraceabilityRecord(models.Model):
    """
    Complete traceability chain
    """
    manufacturing_order = models.ForeignKey('manufacturing.ManufacturingOrder', on_delete=models.CASCADE, related_name='traceability_records', null=True, blank=True)
    
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

    class Meta:
        verbose_name = 'Traceability Record'
        verbose_name_plural = 'Traceability Records'

    def __str__(self):
        return f"Traceability - {self.batch.batch_id}"