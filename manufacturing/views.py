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
    ProductBasicSerializer, RawMaterialBasicSerializer, VendorBasicSerializer,
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
            'product_code', 'product_code__customer_c_id', 'customer_c_id', 'assigned_supervisor', 'created_by', 
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
        products = Product.objects.all().order_by('product_code')
        
        # If no products in Product table, get unique products from BOM
        if not products.exists():
            from processes.models import BOM
            
            # Get unique product codes from BOM
            bom_products = BOM.objects.filter(is_active=True).values('product_code').distinct().order_by('product_code')
            
            # Create a list of product-like objects for the dropdown
            product_list = []
            for bom_product in bom_products:
                product_list.append({
                    'id': bom_product['product_code'],  # Use product_code as ID temporarily
                    'product_code': bom_product['product_code'],
                    'part_number': None,
                    'part_name': None,
                    'display_name': bom_product['product_code'],
                    'is_active': True
                })
            
            return Response(product_list)
        
        serializer = ProductDropdownSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def product_details(self, request):
        """Get complete product details with BOM and material info for MO creation"""
        product_code = request.query_params.get('product_code')
        if not product_code:
            return Response(
                {'error': 'product_code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Try to get product details from Product table
            try:
                product = Product.objects.select_related('customer_c_id', 'material').get(product_code=product_code)
            except Product.DoesNotExist:
                # If product doesn't exist in Product table, create a minimal product object from BOM
                bom_item = BOM.objects.filter(product_code=product_code, is_active=True).first()
                if not bom_item:
                    return Response(
                        {'error': 'Product not found in BOM'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Create a minimal product-like object from BOM
                material = bom_item.material if bom_item.material else None
                
                product = type('Product', (), {
                    'id': product_code,
                    'product_code': product_code,
                    'product_type': bom_item.type,
                    'material': material,
                    'material_type': material.material_type if material else '',
                    'material_name': material.get_material_name_display() if material else '',
                    'grade': material.grade if material else '',
                    'wire_diameter_mm': material.wire_diameter_mm if material else None,
                    'thickness_mm': material.thickness_mm if material else None,
                    'finishing': material.get_finishing_display() if material else '',
                    'weight_kg': material.weight_kg if material else None,
                    'material_type_display': material.get_material_type_display() if material else '',
                    'customer_c_id': None,  # No customer info available from BOM
                    'customer_name': None,
                    'customer_id': None,
                    'customer_industry': None,
                    'get_product_type_display': lambda: 'Spring' if bom_item.type == 'spring' else 'Stamping Part'
                })()
            
            # Get BOM data for this product
            from processes.models import BOM
            from processes.serializers import BOMDetailSerializer
            
            bom_items = BOM.objects.filter(
                product_code=product_code, 
                is_active=True
            ).select_related(
                'process_step__process', 
                'process_step__subprocess', 
                'material'
            ).order_by('process_step__sequence_order')
            
            # Serialize the data
            product_data = ProductBasicSerializer(product).data
            bom_data = BOMDetailSerializer(bom_items, many=True).data
            
            # Extract unique processes and materials
            processes = []
            materials = []
            process_ids = set()
            material_codes = set()
            
            for bom_item in bom_items:
                # Collect unique processes
                if bom_item.process_step.process.id not in process_ids:
                    processes.append({
                        'id': bom_item.process_step.process.id,
                        'name': bom_item.process_step.process.name,
                        'code': bom_item.process_step.process.code
                    })
                    process_ids.add(bom_item.process_step.process.id)
                
                # Collect unique materials
                if bom_item.material and bom_item.material.material_code not in material_codes:
                    materials.append(RawMaterialBasicSerializer(bom_item.material).data)
                    material_codes.add(bom_item.material.material_code)
            
            response_data = {
                'product': product_data,
                'bom_items': bom_data,
                'processes': processes,
                'materials': materials,
                'auto_populate_data': {
                    'product_type': product.get_product_type_display() if hasattr(product, 'get_product_type_display') else '',
                    'material_name': product.material_name if hasattr(product, 'material_name') else '',
                    'material_type': product.material_type if hasattr(product, 'material_type') else '',
                    'grade': product.grade if hasattr(product, 'grade') else '',
                    'wire_diameter_mm': product.wire_diameter_mm if hasattr(product, 'wire_diameter_mm') else None,
                    'thickness_mm': product.thickness_mm if hasattr(product, 'thickness_mm') else None,
                    'finishing': product.finishing if hasattr(product, 'finishing') else '',
                    'weight_kg': product.weight_kg if hasattr(product, 'weight_kg') else None,
                    'material_type_display': product.material_type_display if hasattr(product, 'material_type_display') else ''
                }
            }
            
            return Response(response_data)
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def supervisors(self, request):
        """Get supervisors for dropdown"""
        # You might want to filter by role/permission here
        supervisors = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        serializer = UserDropdownSerializer(supervisors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def customers(self, request):
        """Get customers for dropdown"""
        from third_party.models import Customer
        from third_party.serializers import CustomerListSerializer
        
        customers = Customer.objects.filter(is_active=True).order_by('name')
        serializer = CustomerListSerializer(customers, many=True)
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

    @action(detail=True, methods=['patch'])
    def update_mo_details(self, request, pk=None):
        """Update MO supervisor and shift (Manager only)"""
        mo = self.get_object()
        
        # Check if user is manager or production_head
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if not any(role in ['manager', 'production_head'] for role in user_roles):
            return Response(
                {'error': 'Only managers or production heads can update MO details'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow updates for certain statuses
        if mo.status not in ['submitted', 'gm_approved', 'mo_approved', 'on_hold', 'rm_allocated']:
            return Response(
                {'error': f'Cannot update MO in {mo.status} status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update allowed fields
        allowed_fields = ['assigned_supervisor', 'shift']
        updated_fields = []
        
        for field in allowed_fields:
            if field in request.data:
                if field == 'assigned_supervisor':
                    # Validate supervisor exists and has supervisor role
                    supervisor_id = request.data[field]
                    
                    # Handle empty string or None (clearing the supervisor)
                    if not supervisor_id or supervisor_id == '':
                        mo.assigned_supervisor = None
                        updated_fields.append(field)
                    else:
                        try:
                            supervisor = User.objects.get(id=supervisor_id)
                            if not supervisor.user_roles.filter(role__name='supervisor').exists():
                                return Response(
                                    {'error': 'Selected user is not a supervisor'}, 
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            mo.assigned_supervisor = supervisor
                            updated_fields.append(field)
                        except User.DoesNotExist:
                            return Response(
                                {'error': 'Supervisor not found'}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                elif field == 'shift':
                    shift_value = request.data[field]
                    # Handle empty string or None (clearing the shift)
                    if not shift_value or shift_value == '':
                        mo.shift = None
                        updated_fields.append(field)
                    elif shift_value in ['I', 'II', 'III']:
                        mo.shift = shift_value
                        updated_fields.append(field)
                    else:
                        return Response(
                            {'error': 'Invalid shift value'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
        
        if updated_fields:
            mo.save()
            
            # Create notification if supervisor was assigned
            if 'assigned_supervisor' in updated_fields and mo.assigned_supervisor:
                from notifications.models import Alert, AlertRule
                
                # Create or get alert rule for MO assignments
                alert_rule, _ = AlertRule.objects.get_or_create(
                    name='MO Assignment',
                    alert_type='custom',
                    defaults={'trigger_condition': {}, 'notification_methods': ['in_app']}
                )
                
                # Create alert for supervisor
                Alert.objects.create(
                    alert_rule=alert_rule,
                    title=f'{mo.mo_id} is assigned to you',
                    message=f'Manufacturing Order {mo.mo_id} has been assigned to you. Product: {mo.product_code.display_name}, Quantity: {mo.quantity}',
                    severity='medium',
                    related_object_type='mo',
                    related_object_id=str(mo.id),
                    status='active'
                )
                alert_rule.recipient_users.add(mo.assigned_supervisor)
            
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response({
            'message': f'Updated fields: {", ".join(updated_fields)}',
            'mo': serializer.data
        })

    @action(detail=True, methods=['post'])
    def approve_mo(self, request, pk=None):
        """Approve MO and notify supervisor (Manager only)"""
        mo = self.get_object()
        
        # Check if user is manager or production_head
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if not any(role in ['manager', 'production_head'] for role in user_roles):
            return Response(
                {'error': 'Only managers or production heads can approve MOs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check current status
        if mo.status not in ['submitted', 'on_hold', 'gm_approved']:
            return Response(
                {'error': f'Cannot approve MO in {mo.status} status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if supervisor is assigned
        if not mo.assigned_supervisor:
            return Response(
                {'error': 'Cannot approve MO without assigned supervisor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update MO status
        old_status = mo.status
        mo.status = 'mo_approved'
        mo.save()
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status='mo_approved',
            changed_by=request.user,
            notes=request.data.get('notes', 'MO approved by manager')
        )
        
        # Create notification for supervisor
        from notifications.models import Alert, AlertRule
        
        # Create or get alert rule for MO approval notifications
        alert_rule, created = AlertRule.objects.get_or_create(
            name='MO Approval Notification',
            alert_type='custom',
            defaults={
                'trigger_condition': {'event': 'mo_approved'},
                'notification_methods': ['in_app']
            }
        )
        
        # Create alert for supervisor
        Alert.objects.create(
            alert_rule=alert_rule,
            title=f'Manufacturing Order {mo.mo_id} Assigned',
            message=f'Manufacturing Order {mo.mo_id} has been approved and assigned to you. Product: {mo.product_code.product_code}, Quantity: {mo.quantity}',
            severity='medium',
            related_object_type='mo',
            related_object_id=str(mo.id)
        )
        
        # Add supervisor to alert rule recipients if not already added
        if not alert_rule.recipient_users.filter(id=mo.assigned_supervisor.id).exists():
            alert_rule.recipient_users.add(mo.assigned_supervisor)
        
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response({
            'message': 'MO approved successfully and supervisor notified',
            'mo': serializer.data
        })

    @action(detail=False, methods=['get'])
    def supervisor_dashboard(self, request):
        """Get MOs assigned to current supervisor"""
        # Check if user is supervisor
        if not request.user.user_roles.filter(role__name='supervisor').exists():
            return Response(
                {'error': 'Only supervisors can access this endpoint'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get MOs assigned to this supervisor
        assigned_mos = self.get_queryset().filter(
            assigned_supervisor=request.user,
            status__in=['gm_approved', 'mo_approved', 'rm_allocated', 'in_progress', 'on_hold']
        ).order_by('-created_at')
        
        # Separate by status
        approved_mos = assigned_mos.exclude(status='in_progress')
        in_progress_mos = assigned_mos.filter(status='in_progress')
        
        # Serialize data
        approved_serializer = ManufacturingOrderListSerializer(approved_mos, many=True)
        in_progress_serializer = ManufacturingOrderListSerializer(in_progress_mos, many=True)
        
        return Response({
            'summary': {
                'total_assigned': assigned_mos.count(),
                'pending_start': approved_mos.count(),
                'in_progress': in_progress_mos.count()
            },
            'pending_start': approved_serializer.data,
            'in_progress': in_progress_serializer.data
        })

    @action(detail=True, methods=['post'])
    def start_mo(self, request, pk=None):
        """Start MO (Supervisor only) - moves from mo_approved to in_progress"""
        mo = self.get_object()
        
        # Check if user is supervisor
        if not request.user.user_roles.filter(role__name='supervisor').exists():
            return Response(
                {'error': 'Only supervisors can start MOs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if MO is assigned to this supervisor
        if mo.assigned_supervisor != request.user:
            return Response(
                {'error': 'You can only start MOs assigned to you'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check current status
        if mo.status not in ['mo_approved', 'gm_approved', 'rm_allocated', 'on_hold']:
            return Response(
                {'error': f'Cannot start MO in {mo.status} status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update MO status
        old_status = mo.status
        mo.status = 'in_progress'
        mo.actual_start_date = timezone.now()
        mo.save()
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status='in_progress',
            changed_by=request.user,
            notes=request.data.get('notes', 'MO started by supervisor')
        )
        
        # Initialize processes if not already done
        from processes.models import BOM
        if not mo.process_executions.exists():
            bom_items = BOM.objects.filter(
                product_code=mo.product_code.product_code,
                is_active=True
            ).select_related('process_step__process').distinct('process_step__process')
            
            sequence = 1
            for bom_item in bom_items:
                process = bom_item.process_step.process
                
                MOProcessExecution.objects.get_or_create(
                    mo=mo,
                    process=process,
                    defaults={
                        'sequence_order': sequence,
                        'status': 'pending',
                        'assigned_operator': request.user
                    }
                )
                sequence += 1
        
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response({
            'message': 'MO started successfully',
            'mo': serializer.data
        })


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
