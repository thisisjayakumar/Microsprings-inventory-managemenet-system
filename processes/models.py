from django.db import models
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from inventory.models import RawMaterial


class Process(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SubProcess(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='subprocesses')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['process', 'name']

    def __str__(self):
        return f"{self.process.name} -> {self.name}"


class ProcessStep(models.Model):
    """
    Defines the sequence of process steps for manufacturing
    """
    step_name = models.CharField(max_length=100)
    step_code = models.CharField(max_length=50, unique=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='process_steps')
    subprocess = models.ForeignKey(
        SubProcess, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='process_steps'
    )
    sequence_order = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_order']
        unique_together = [['step_code', 'process']]

    def __str__(self):
        if self.subprocess:
            return f"{self.step_name} ({self.process.name} -> {self.subprocess.name})"
        return f"{self.step_name} ({self.process.name})"

    def clean(self):
        if self.subprocess and self.subprocess.process != self.process:
            raise ValidationError("Subprocess must belong to the selected process")

    @property
    def full_path(self):
        if self.subprocess:
            return f"{self.process.name} -> {self.subprocess.name} -> {self.step_name}"
        return f"{self.process.name} -> {self.step_name}"

class BOM(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('spring', 'Spring'),
        ('stamp', 'Stamp'),
    ]

    product_code = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    process_step = models.ForeignKey(
        ProcessStep, 
        on_delete=models.CASCADE,
        help_text="Specific process step with ordering"
    )
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_code','type']
        unique_together = [['product_code', 'process_step', 'material']]

    def __str__(self):
        return f"{self.product_code} ({self.type}) - {self.process_step.full_path}"

    @property
    def main_process(self):
        return self.process_step.process

    @property
    def subprocess(self):
        return self.process_step.subprocess

    def clean(self):
        # Add any BOM-specific validation here if needed
        super().clean()