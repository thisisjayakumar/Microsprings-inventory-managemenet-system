from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch

from .models import Process, SubProcess, ProcessStep, BOM
from .serializers import (
    ProcessListSerializer, ProcessDetailSerializer,
    SubProcessListSerializer, SubProcessDetailSerializer,
    ProcessStepListSerializer, ProcessStepDetailSerializer,
    BOMListSerializer, BOMDetailSerializer,
    ProcessDropdownSerializer, SubProcessDropdownSerializer,
    ProcessStepDropdownSerializer, RawMaterialDropdownSerializer
)
from inventory.models import RawMaterial


class ProcessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Process with optimized queries and filtering
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'code']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Optimized queryset with prefetch_related"""
        return Process.objects.prefetch_related(
            'subprocesses', 'process_steps'
        )

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ProcessListSerializer
        return ProcessDetailSerializer

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get processes for dropdown"""
        processes = Process.objects.filter(is_active=True).order_by('name')
        serializer = ProcessDropdownSerializer(processes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def subprocesses(self, request, pk=None):
        """Get subprocesses for a specific process"""
        process = self.get_object()
        subprocesses = process.subprocesses.all()
        serializer = SubProcessListSerializer(subprocesses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def process_steps(self, request, pk=None):
        """Get process steps for a specific process"""
        process = self.get_object()
        process_steps = process.process_steps.all().order_by('sequence_order')
        serializer = ProcessStepListSerializer(process_steps, many=True)
        return Response(serializer.data)


class SubProcessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SubProcess with optimized queries and filtering
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['process']
    search_fields = ['name', 'description', 'process__name']
    ordering_fields = ['name', 'created_at', 'process__name']
    ordering = ['process__name', 'name']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        return SubProcess.objects.select_related('process').prefetch_related('process_steps')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return SubProcessListSerializer
        return SubProcessDetailSerializer

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get subprocesses for dropdown, optionally filtered by process"""
        subprocesses = SubProcess.objects.select_related('process')
        
        # Filter by process if specified
        process_id = request.query_params.get('process_id')
        if process_id:
            subprocesses = subprocesses.filter(process_id=process_id)
        
        subprocesses = subprocesses.order_by('process__name', 'name')
        serializer = SubProcessDropdownSerializer(subprocesses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def process_steps(self, request, pk=None):
        """Get process steps for a specific subprocess"""
        subprocess = self.get_object()
        process_steps = subprocess.process_steps.all().order_by('sequence_order')
        serializer = ProcessStepListSerializer(process_steps, many=True)
        return Response(serializer.data)


class ProcessStepViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProcessStep with optimized queries and filtering
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['process', 'subprocess']
    search_fields = ['step_name', 'step_code', 'description', 'process__name', 'subprocess__name']
    ordering_fields = ['step_name', 'sequence_order', 'created_at']
    ordering = ['sequence_order']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        return ProcessStep.objects.select_related(
            'process', 'subprocess'
        ).prefetch_related('bom_set__material')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ProcessStepListSerializer
        return ProcessStepDetailSerializer

    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get process steps for dropdown, optionally filtered by process or subprocess"""
        process_steps = ProcessStep.objects.select_related('process', 'subprocess')
        
        # Filter by process if specified
        process_id = request.query_params.get('process_id')
        if process_id:
            process_steps = process_steps.filter(process_id=process_id)
        
        # Filter by subprocess if specified
        subprocess_id = request.query_params.get('subprocess_id')
        if subprocess_id:
            process_steps = process_steps.filter(subprocess_id=subprocess_id)
        
        process_steps = process_steps.order_by('sequence_order')
        serializer = ProcessStepDropdownSerializer(process_steps, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def bom_items(self, request, pk=None):
        """Get BOM items for a specific process step"""
        process_step = self.get_object()
        bom_items = process_step.bom_set.select_related('material').filter(is_active=True)
        serializer = BOMListSerializer(bom_items, many=True)
        return Response(serializer.data)


class BOMViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BOM with optimized queries and filtering
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'process_step', 'material', 'is_active']
    search_fields = [
        'product_code', 'process_step__step_name', 'process_step__process__name',
        'material__product_code', 'material__material_name'
    ]
    ordering_fields = ['product_code', 'type', 'created_at']
    ordering = ['product_code', 'type']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        return BOM.objects.select_related(
            'process_step__process', 'process_step__subprocess', 'material'
        )

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return BOMListSerializer
        return BOMDetailSerializer

    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get BOM items filtered by product code and type"""
        product_code = request.query_params.get('product_code')
        product_type = request.query_params.get('type')
        
        if not product_code:
            return Response(
                {'error': 'product_code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            product_code=product_code,
            is_active=True
        )
        
        if product_type:
            queryset = queryset.filter(type=product_type)
        
        # Order by process step sequence
        queryset = queryset.order_by('process_step__sequence_order')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def raw_materials(self, request):
        """Get raw materials for dropdown"""
        raw_materials = RawMaterial.objects.all().order_by('material_name', 'grade')
        serializer = RawMaterialDropdownSerializer(raw_materials, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for BOM"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'active': queryset.filter(is_active=True).count(),
            'inactive': queryset.filter(is_active=False).count(),
            'by_type': {
                'spring': queryset.filter(type='spring').count(),
                'stamp': queryset.filter(type='stamp').count(),
            },
            'unique_products': queryset.values('product_code').distinct().count(),
            'unique_materials': queryset.values('material').distinct().count(),
        }
        
        return Response(stats)
