from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch, Sum
from django.contrib.auth import get_user_model
from django.utils import timezone

from .permissions import IsManager, IsManagerOrSupervisor

from .models import ManufacturingOrder, PurchaseOrder, MOStatusHistory, POStatusHistory
from .serializers import (
    ManufacturingOrderListSerializer, ManufacturingOrderDetailSerializer,
    PurchaseOrderListSerializer, PurchaseOrderDetailSerializer,
    ProductDropdownSerializer, RawMaterialDropdownSerializer,
    VendorDropdownSerializer, UserDropdownSerializer,
    RawMaterialBasicSerializer, VendorBasicSerializer
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
