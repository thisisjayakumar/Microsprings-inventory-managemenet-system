from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ProcessTemplate(models.Model):
    """
    Configurable workflow templates
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    material_types = models.ManyToManyField('products.MaterialType', related_name='process_templates')  # Which materials use this template
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='1.0')

    class Meta:
        verbose_name = 'Process Template'
        verbose_name_plural = 'Process Templates'

    def __str__(self):
        return f"{self.name} v{self.version}"


class ProcessStep(models.Model):
    """
    Individual steps within a process template
    """
    template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE, related_name='steps')
    step_name = models.CharField(max_length=100)
    sequence_order = models.PositiveIntegerField()
    
    # Step configuration
    is_mandatory = models.BooleanField(default=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    machine_required = models.BooleanField(default=False)
    operator_required = models.BooleanField(default=True)
    
    # Quality parameters
    quality_checks = models.JSONField(default=dict)
    acceptable_scrap_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ['template', 'sequence_order']
        ordering = ['template', 'sequence_order']
        verbose_name = 'Process Step'
        verbose_name_plural = 'Process Steps'

    def __str__(self):
        return f"{self.template.name} - {self.sequence_order}. {self.step_name}"


class ProcessStepDependency(models.Model):
    """
    Dependencies between process steps
    """
    DEPENDENCY_CHOICES = [
        ('prerequisite', 'Must Complete Before'),
        ('parallel', 'Can Run Parallel'),
        ('optional', 'Optional Dependency')
    ]
    
    step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name='dependents')
    dependency_type = models.CharField(max_length=20, choices=DEPENDENCY_CHOICES)

    class Meta:
        unique_together = ['step', 'depends_on']
        verbose_name = 'Process Step Dependency'
        verbose_name_plural = 'Process Step Dependencies'

    def __str__(self):
        return f"{self.step.step_name} {self.dependency_type} {self.depends_on.step_name}"


class ProductProcessMapping(models.Model):
    """
    Link products to their process templates
    """
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='process_mappings')
    process_template = models.ForeignKey(ProcessTemplate, on_delete=models.CASCADE, related_name='product_mappings')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product', 'process_template']
        verbose_name = 'Product Process Mapping'
        verbose_name_plural = 'Product Process Mappings'

    def __str__(self):
        return f"{self.product.part_number} -> {self.process_template.name}"