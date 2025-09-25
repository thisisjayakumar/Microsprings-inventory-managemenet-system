from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch, Sum
from django.contrib.auth import get_user_model
from django.utils import timezone

from .permissions import IsManager, IsManagerOrSupervisor

from .models import (
    ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory,
    MOProcessExecution, MOProcessStepExecution, MOProcessAlert
)
from .serializers import (
    ManufacturingOrderListSerializer, ManufacturingOrderDetailSerializer,
    PurchaseOrderListSerializer, PurchaseOrderDetailSerializer,
    ProductDropdownSerializer, RawMaterialDropdownSerializer,
    VendorDropdownSerializer, UserDropdownSerializer,
    RawMaterialBasicSerializer, VendorBasicSerializer,
    ManufacturingOrderWithProcessesSerializer, MOProcessExecutionListSerializer,
    MOProcessExecutionDetailSerializer, MOProcessStepExecutionSerializer,
    MOProcessAlertSerializer
)
from products.models import Product
from inventory.models import RawMaterial
from third_party.models import Vendor

User = get_user_model()


class ManufacturingOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Manufacturing Orders with optimized queries and filtering
    Only managers can create/edit MOs, supervisors can view and change status
    """
    permission_classes = [IsManagerOrSupervisor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'shift', 'material_type', 'assigned_supervisor']
    search_fields = ['mo_id', 'product_code__product_code', 'product_code__part_number', 'customer_order_reference']
    ordering_fields = ['created_at', 'planned_start_date', 'delivery_date', 'mo_id']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        queryset = ManufacturingOrder.objects.select_related(
            'product_code', 'assigned_supervisor', 'created_by', 
            'gm_approved_by', 'rm_allocated_by'
        ).prefetch_related(
            Prefetch('status_history', queryset=MOStatusHistory.objects.select_related('changed_by'))
        )
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        return queryset

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ManufacturingOrderListSerializer
        return ManufacturingOrderDetailSerializer

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change MO status with validation"""
        mo = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status transition
        valid_statuses = dict(ManufacturingOrder.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = mo.status
        mo.status = new_status
        
        # Update workflow timestamps based on status
        if new_status == 'submitted':
            mo.submitted_at = timezone.now()
        elif new_status == 'gm_approved':
            mo.gm_approved_at = timezone.now()
            mo.gm_approved_by = request.user
        elif new_status == 'rm_allocated':
            mo.rm_allocated_at = timezone.now()
            mo.rm_allocated_by = request.user
        elif new_status == 'in_progress' and not mo.actual_start_date:
            mo.actual_start_date = timezone.now()
        elif new_status == 'completed' and not mo.actual_end_date:
            mo.actual_end_date = timezone.now()
        
        mo.save()
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
            notes=notes
        )
        
        serializer = self.get_serializer(mo)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for MOs"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'draft': queryset.filter(status='draft').count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
            'overdue': queryset.filter(
                planned_end_date__lt=timezone.now(),
                status__in=['draft', 'approved', 'in_progress']
            ).count(),
            'by_priority': {
                'high': queryset.filter(priority='high').count(),
                'medium': queryset.filter(priority='medium').count(),
                'low': queryset.filter(priority='low').count(),
            }
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def products(self, request):
        """Get products for dropdown"""
        products = Product.objects.filter(is_active=True).order_by('product_code')
        serializer = ProductDropdownSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def supervisors(self, request):
        """Get supervisors for dropdown"""
        # You might want to filter by role/permission here
        supervisors = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        serializer = UserDropdownSerializer(supervisors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def process_tracking(self, request, pk=None):
        """Get MO with detailed process tracking information"""
        mo = self.get_object()
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def initialize_processes(self, request, pk=None):
        """Initialize process executions for an MO based on product BOM"""
        mo = self.get_object()
        
        if mo.status != 'rm_allocated':
            return Response(
                {'error': 'MO must be in rm_allocated status to initialize processes'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get processes from BOM for this product
        from processes.models import BOM
        bom_items = BOM.objects.filter(
            product_code=mo.product_code.product_code,
            is_active=True
        ).select_related('process_step__process').distinct('process_step__process')
        
        if not bom_items:
            return Response(
                {'error': 'No processes found for this product'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create process executions
        sequence = 1
        for bom_item in bom_items:
            process = bom_item.process_step.process
            
            # Check if execution already exists
            execution, created = MOProcessExecution.objects.get_or_create(
                mo=mo,
                process=process,
                defaults={
                    'sequence_order': sequence,
                    'status': 'pending'
                }
            )
            
            if created:
                sequence += 1
        
        # Update MO status
        mo.status = 'in_progress'
        mo.actual_start_date = timezone.now()
        mo.save()
        
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response(serializer.data)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Purchase Orders with optimized queries and filtering
    Only managers can create/edit POs
    """
    permission_classes = [IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'material_type', 'vendor_name', 'expected_date']
    search_fields = ['po_id', 'rm_code__product_code', 'vendor_name__name']
    ordering_fields = ['created_at', 'expected_date', 'po_id', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        queryset = PurchaseOrder.objects.select_related(
            'rm_code', 'vendor_name', 'created_by', 'gm_approved_by', 
            'po_created_by', 'rejected_by'
        ).prefetch_related(
            Prefetch('status_history', queryset=POStatusHistory.objects.select_related('changed_by'))
        )
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        return queryset

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return PurchaseOrderListSerializer
        return PurchaseOrderDetailSerializer

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change PO status with validation"""
        po = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        rejection_reason = request.data.get('rejection_reason', '')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status transition
        valid_statuses = dict(PurchaseOrder.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = po.status
        po.status = new_status
        
        # Update workflow timestamps based on status
        if new_status == 'submitted':
            po.submitted_at = timezone.now()
        elif new_status == 'gm_approved':
            po.gm_approved_at = timezone.now()
            po.gm_approved_by = request.user
        elif new_status == 'gm_created_po':
            po.po_created_at = timezone.now()
            po.po_created_by = request.user
        elif new_status == 'rejected':
            po.rejected_at = timezone.now()
            po.rejected_by = request.user
            po.rejection_reason = rejection_reason
        
        po.save()
        
        # Create status history
        POStatusHistory.objects.create(
            po=po,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
            notes=notes
        )
        
        serializer = self.get_serializer(po)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for POs"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'draft': queryset.filter(status='draft').count(),
            'gm_approved': queryset.filter(status='gm_approved').count(),
            'completed': queryset.filter(status='completed').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'overdue': queryset.filter(
                expected_date__lt=timezone.now().date(),
                status__in=['draft', 'submitted', 'gm_approved', 'gm_created_po']
            ).count(),
            'total_value': queryset.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def raw_materials(self, request):
        """Get raw materials for dropdown"""
        raw_materials = RawMaterial.objects.all().order_by('material_name', 'grade')
        serializer = RawMaterialDropdownSerializer(raw_materials, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vendors(self, request):
        """Get vendors for dropdown, optionally filtered by material"""
        vendors = Vendor.objects.filter(is_active=True)
        
        # Filter by vendor type if specified
        vendor_type = request.query_params.get('vendor_type')
        if vendor_type:
            vendors = vendors.filter(vendor_type=vendor_type)
        
        vendors = vendors.order_by('name')
        serializer = VendorDropdownSerializer(vendors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def material_details(self, request):
        """Get material details for auto-population"""
        material_id = request.query_params.get('material_id')
        if not material_id:
            return Response({'error': 'material_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            material = RawMaterial.objects.get(id=material_id)
            serializer = RawMaterialBasicSerializer(material)
            return Response(serializer.data)
        except RawMaterial.DoesNotExist:
            return Response({'error': 'Material not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def vendor_details(self, request):
        """Get vendor details for auto-population"""
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response({'error': 'vendor_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vendor = Vendor.objects.get(id=vendor_id)
            serializer = VendorBasicSerializer(vendor)
            return Response(serializer.data)
        except Vendor.DoesNotExist:
            return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)


class MOProcessExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MO Process Execution tracking
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mo', 'process', 'status', 'assigned_operator']
    search_fields = ['mo__mo_id', 'process__name', 'assigned_operator__first_name', 'assigned_operator__last_name']
    ordering_fields = ['sequence_order', 'planned_start_time', 'actual_start_time', 'progress_percentage']
    ordering = ['mo', 'sequence_order']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        return MOProcessExecution.objects.select_related(
            'mo', 'process', 'assigned_operator'
        ).prefetch_related('step_executions', 'alerts')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return MOProcessExecutionListSerializer
        return MOProcessExecutionDetailSerializer

    @action(detail=True, methods=['post'])
    def start_process(self, request, pk=None):
        """Start a process execution"""
        execution = self.get_object()
        
        if execution.status != 'pending':
            return Response(
                {'error': 'Process can only be started from pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        execution.status = 'in_progress'
        execution.actual_start_time = timezone.now()
        execution.assigned_operator = request.user
        execution.save()
        
        # Create step executions if they don't exist
        process_steps = execution.process.process_steps.all().order_by('sequence_order')
        for step in process_steps:
            MOProcessStepExecution.objects.get_or_create(
                process_execution=execution,
                process_step=step,
                defaults={'status': 'pending'}
            )
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_process(self, request, pk=None):
        """Complete a process execution"""
        execution = self.get_object()
        
        if execution.status != 'in_progress':
            return Response(
                {'error': 'Process must be in progress to complete'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if all steps are completed
        incomplete_steps = execution.step_executions.exclude(status='completed').count()
        if incomplete_steps > 0:
            return Response(
                {'error': f'{incomplete_steps} steps are still incomplete'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        execution.status = 'completed'
        execution.actual_end_time = timezone.now()
        execution.progress_percentage = 100
        execution.save()
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update process progress"""
        execution = self.get_object()
        progress = request.data.get('progress_percentage')
        notes = request.data.get('notes', '')
        
        if progress is None or not (0 <= float(progress) <= 100):
            return Response(
                {'error': 'Valid progress_percentage (0-100) is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        execution.progress_percentage = progress
        if notes:
            execution.notes = notes
        execution.save()
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_mo(self, request):
        """Get process executions for a specific MO"""
        mo_id = request.query_params.get('mo_id')
        if not mo_id:
            return Response(
                {'error': 'mo_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        executions = self.get_queryset().filter(mo_id=mo_id)
        serializer = self.get_serializer(executions, many=True)
        return Response(serializer.data)


class MOProcessStepExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MO Process Step Execution tracking
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['process_execution', 'process_step', 'status', 'quality_status', 'operator']
    search_fields = ['process_step__step_name', 'operator__first_name', 'operator__last_name']
    ordering_fields = ['process_step__sequence_order', 'actual_start_time', 'efficiency_percentage']
    ordering = ['process_execution', 'process_step__sequence_order']
    serializer_class = MOProcessStepExecutionSerializer

    def get_queryset(self):
        """Optimized queryset with select_related"""
        return MOProcessStepExecution.objects.select_related(
            'process_execution__mo', 'process_step', 'operator'
        )

    @action(detail=True, methods=['post'])
    def start_step(self, request, pk=None):
        """Start a process step"""
        step_execution = self.get_object()
        
        if step_execution.status != 'pending':
            return Response(
                {'error': 'Step can only be started from pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        step_execution.status = 'in_progress'
        step_execution.actual_start_time = timezone.now()
        step_execution.operator = request.user
        step_execution.save()
        
        serializer = self.get_serializer(step_execution)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_step(self, request, pk=None):
        """Complete a process step with quality data"""
        step_execution = self.get_object()
        data = request.data
        
        if step_execution.status != 'in_progress':
            return Response(
                {'error': 'Step must be in progress to complete'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update step data
        step_execution.status = 'completed'
        step_execution.actual_end_time = timezone.now()
        step_execution.quantity_processed = data.get('quantity_processed', 0)
        step_execution.quantity_passed = data.get('quantity_passed', 0)
        step_execution.quantity_failed = data.get('quantity_failed', 0)
        step_execution.quality_status = data.get('quality_status', 'passed')
        step_execution.operator_notes = data.get('operator_notes', '')
        step_execution.quality_notes = data.get('quality_notes', '')
        
        # Calculate scrap percentage
        if step_execution.quantity_processed > 0:
            step_execution.scrap_percentage = (
                step_execution.quantity_failed / step_execution.quantity_processed
            ) * 100
        
        step_execution.save()
        
        # Update parent process progress
        process_execution = step_execution.process_execution
        total_steps = process_execution.step_executions.count()
        completed_steps = process_execution.step_executions.filter(status='completed').count()
        
        if total_steps > 0:
            progress = (completed_steps / total_steps) * 100
            process_execution.progress_percentage = progress
            process_execution.save()
        
        serializer = self.get_serializer(step_execution)
        return Response(serializer.data)


class MOProcessAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MO Process Alerts
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['process_execution', 'alert_type', 'severity', 'is_resolved']
    search_fields = ['title', 'description', 'process_execution__mo__mo_id']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    serializer_class = MOProcessAlertSerializer

    def get_queryset(self):
        """Optimized queryset with select_related"""
        return MOProcessAlert.objects.select_related(
            'process_execution__mo', 'created_by', 'resolved_by'
        )

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_notes = resolution_notes
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """Get active (unresolved) alerts"""
        alerts = self.get_queryset().filter(is_resolved=False)
        
        # Filter by MO if specified
        mo_id = request.query_params.get('mo_id')
        if mo_id:
            alerts = alerts.filter(process_execution__mo_id=mo_id)
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
