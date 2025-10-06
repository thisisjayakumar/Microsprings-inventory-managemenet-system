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
    MOProcessExecution, MOProcessStepExecution, MOProcessAlert, Batch
)
from .serializers import (
    ManufacturingOrderListSerializer, ManufacturingOrderDetailSerializer,
    PurchaseOrderListSerializer, PurchaseOrderDetailSerializer,
    ProductDropdownSerializer, RawMaterialDropdownSerializer,
    VendorDropdownSerializer, UserDropdownSerializer,
    ProductBasicSerializer, RawMaterialBasicSerializer, VendorBasicSerializer,
    ManufacturingOrderWithProcessesSerializer, MOProcessExecutionListSerializer,
    MOProcessExecutionDetailSerializer, MOProcessStepExecutionSerializer,
    MOProcessAlertSerializer, BatchListSerializer, BatchDetailSerializer
)
from products.models import Product
from inventory.models import RawMaterial, RMStockBalance
from third_party.models import Vendor
from .rm_calculator import RMCalculator
from decimal import Decimal

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

    @action(detail=True, methods=['post'], url_path='complete-rm-allocation', permission_classes=[IsAuthenticated])
    def complete_rm_allocation(self, request, pk=None):
        """
        Complete RM allocation (RM Store only) - changes status to rm_allocated
        """
        mo = self.get_object()
        
        # Check if user is RM Store
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'rm_store' not in user_roles:
            return Response(
                {'error': 'Only RM Store users can complete RM allocation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate MO is assigned to this RM Store user
        if mo.assigned_rm_store != request.user:
            return Response(
                {'error': 'This MO is not assigned to you'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate MO status
        if mo.status not in ['on_hold', 'in_progress']:
            return Response(
                {'error': f'Cannot complete allocation for MO in {mo.status} status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Change status to rm_allocated
        old_status = mo.status
        mo.status = 'rm_allocated'
        mo.rm_allocated_at = timezone.now()
        mo.rm_allocated_by = request.user
        mo.save()
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status='rm_allocated',
            changed_by=request.user,
            notes=request.data.get('notes', 'All RM allocated to batches by RM Store')
        )
        
        serializer = self.get_serializer(mo)
        return Response({
            'message': f'RM allocation completed for MO {mo.mo_id}',
            'mo': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='send-remaining-to-scrap', permission_classes=[IsAuthenticated])
    def send_remaining_to_scrap(self, request, pk=None):
        """
        Send remaining RM to scrap for this MO
        Expected payload: { "scrap_rm_kg": 0.26 } or { "send_all_remaining": true }
        """
        mo = self.get_object()
        send_all = request.data.get('send_all_remaining', False)
        scrap_rm_kg = request.data.get('scrap_rm_kg')
        
        # Calculate remaining RM
        product = mo.product_code
        total_rm_required = None
        
        if product.material_type == 'coil' and product.grams_per_product:
            total_grams = mo.quantity * product.grams_per_product
            base_rm_kg = Decimal(str(total_grams / 1000))
            tolerance = mo.tolerance_percentage or Decimal('2.00')
            tolerance_factor = Decimal('1') + (tolerance / Decimal('100'))
            total_rm_required = float(base_rm_kg * tolerance_factor)
        
        if total_rm_required is None:
            return Response(
                {'error': 'Cannot calculate RM for this product type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate cumulative RM released from batches
        batches = Batch.objects.filter(mo=mo).exclude(status='cancelled')
        cumulative_rm_released = Decimal('0')
        
        for batch in batches:
            batch_quantity_grams = batch.planned_quantity
            batch_rm_base_kg = Decimal(str(batch_quantity_grams / 1000))
            tolerance = mo.tolerance_percentage or Decimal('2.00')
            tolerance_factor = Decimal('1') + (tolerance / Decimal('100'))
            batch_rm = batch_rm_base_kg * tolerance_factor
            cumulative_rm_released += batch_rm
        
        remaining_rm_kg = float(Decimal(str(total_rm_required)) - cumulative_rm_released)
        
        if remaining_rm_kg <= 0:
            return Response(
                {'error': 'No remaining RM to send to scrap'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine scrap amount
        if send_all:
            scrap_kg = remaining_rm_kg
        elif scrap_rm_kg is not None:
            try:
                scrap_kg = float(scrap_rm_kg)
                if scrap_kg <= 0:
                    return Response(
                        {'error': 'scrap_rm_kg must be positive'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if scrap_kg > remaining_rm_kg:
                    return Response(
                        {'error': f'Scrap amount ({scrap_kg} kg) exceeds remaining RM ({remaining_rm_kg:.3f} kg)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'scrap_rm_kg must be a valid number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'error': 'Either scrap_rm_kg or send_all_remaining must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add scrap to MO
        scrap_grams = int(scrap_kg * 1000)
        mo.scrap_rm_weight += scrap_grams
        mo.save()
        
        serializer = self.get_serializer(mo)
        return Response({
            'message': f'Sent {scrap_kg:.3f} kg of RM to scrap for MO {mo.mo_id}',
            'mo': serializer.data,
            'scrap_rm_kg': mo.scrap_rm_weight / 1000,
            'remaining_rm_after': max(0, remaining_rm_kg - scrap_kg)
        })

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
            
            # Extract unique processes and materials (optimized)
            processes = []
            materials = []
            process_steps = []
            process_ids = set()
            material_ids = set()
            
            for bom_item in bom_items:
                # Collect unique processes
                if bom_item.process_step.process.id not in process_ids:
                    processes.append({
                        'id': bom_item.process_step.process.id,
                        'name': bom_item.process_step.process.name,
                        'code': bom_item.process_step.process.code
                    })
                    process_ids.add(bom_item.process_step.process.id)
                
                # Collect unique materials with available_quantity
                if bom_item.material and bom_item.material.id not in material_ids:
                    material_data = RawMaterialBasicSerializer(bom_item.material).data
                    materials.append(material_data)
                    material_ids.add(bom_item.material.id)
                
                # Collect simplified process steps (without redundant material data)
                process_steps.append({
                    'process_step_name': bom_item.process_step.step_name,
                    'process_name': bom_item.process_step.process.name,
                    'sequence_order': bom_item.process_step.sequence_order,
                    'material_id': bom_item.material.id if bom_item.material else None,
                    'material_code': bom_item.material.material_code if bom_item.material else None
                })
            
            response_data = {
                'product': product_data,
                'process_steps': sorted(process_steps, key=lambda x: x['sequence_order']),
                'processes': processes,
                'materials': materials
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
        # Filter by supervisor role
        supervisors = User.objects.filter(
            is_active=True,
            user_roles__role__name='supervisor'
        ).distinct().order_by('first_name', 'last_name')
        serializer = UserDropdownSerializer(supervisors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def rm_store_users(self, request):
        """Get RM store users for dropdown"""
        # Filter by rm_store role
        rm_store_users = User.objects.filter(
            is_active=True,
            user_roles__role__name='rm_store'
        ).distinct().order_by('first_name', 'last_name')
        serializer = UserDropdownSerializer(rm_store_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def customers(self, request):
        """Get customers for dropdown"""
        from third_party.models import Customer
        from third_party.serializers import CustomerListSerializer
        
        customers = Customer.objects.filter(is_active=True).order_by('name')
        serializer = CustomerListSerializer(customers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def calculate_rm_requirement(self, request):
        """
        Calculate RM requirement for a Manufacturing Order
        Supports both coil and sheet materials
        """
        try:
            product_code = request.data.get('product_code')
            quantity = request.data.get('quantity')
            tolerance_percentage = request.data.get('tolerance_percentage', 2.00)
            scrap_percentage = request.data.get('scrap_percentage')
            
            if not product_code or not quantity:
                return Response(
                    {'error': 'product_code and quantity are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get product
            try:
                product = Product.objects.select_related('material').get(product_code=product_code)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Product not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            material = product.material
            if not material:
                return Response(
                    {'error': 'Product has no associated material'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get available stock
            try:
                stock_balance = RMStockBalance.objects.get(raw_material=material)
                available_quantity = stock_balance.available_quantity
            except RMStockBalance.DoesNotExist:
                available_quantity = Decimal('0')
            
            calculator = RMCalculator()
            
            # Calculate based on material type
            if material.material_type == 'coil':
                # For coil materials
                if not product.grams_per_product:
                    return Response(
                        {'error': 'Product must have grams_per_product defined for coil materials'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                calculation = calculator.calculate_rm_for_coil(
                    quantity=int(quantity),
                    grams_per_product=product.grams_per_product,
                    tolerance_percentage=Decimal(str(tolerance_percentage)),
                    scrap_percentage=Decimal(str(scrap_percentage)) if scrap_percentage else None
                )
                
                # Check availability
                availability = calculator.check_rm_availability(
                    required_amount=calculation['final_required_kg'],
                    available_amount=available_quantity,
                    material_type='coil'
                )
                
                return Response({
                    'material_type': 'coil',
                    'calculation': calculation,
                    'availability': availability,
                    'material_info': {
                        'material_code': material.material_code,
                        'material_name': material.material_name,
                        'grade': material.grade,
                        'wire_diameter_mm': str(material.wire_diameter_mm) if material.wire_diameter_mm else None,
                    }
                })
            
            elif material.material_type == 'sheet':
                # For sheet materials
                if not all([product.length_mm, product.breadth_mm, material.length_mm, material.breadth_mm]):
                    return Response(
                        {'error': 'Product and material must have length and breadth defined for sheet materials'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                calculation = calculator.calculate_rm_for_sheet(
                    quantity=int(quantity),
                    product_length_mm=product.length_mm,
                    product_breadth_mm=product.breadth_mm,
                    sheet_length_mm=material.length_mm,
                    sheet_breadth_mm=material.breadth_mm,
                    tolerance_percentage=Decimal(str(tolerance_percentage)),
                    scrap_percentage=Decimal(str(scrap_percentage)) if scrap_percentage else None
                )
                
                # Check availability (in sheets)
                availability = calculator.check_rm_availability(
                    required_amount=Decimal(str(calculation['final_required_sheets'])),
                    available_amount=available_quantity,
                    material_type='sheet'
                )
                
                return Response({
                    'material_type': 'sheet',
                    'calculation': calculation,
                    'availability': availability,
                    'material_info': {
                        'material_code': material.material_code,
                        'material_name': material.material_name,
                        'grade': material.grade,
                        'thickness_mm': str(material.thickness_mm) if material.thickness_mm else None,
                        'length_mm': str(material.length_mm) if material.length_mm else None,
                        'breadth_mm': str(material.breadth_mm) if material.breadth_mm else None,
                    }
                })
            
            else:
                return Response(
                    {'error': 'Invalid material type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Calculation error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        if mo.status not in ['on_hold', 'rm_allocated']:
            return Response(
                {'error': f'Cannot update MO in {mo.status} status. MO must be in On Hold or RM Allocated status to update.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update allowed fields
        allowed_fields = ['assigned_rm_store', 'assigned_supervisor', 'shift']
        updated_fields = []
        
        for field in allowed_fields:
            if field in request.data:
                if field == 'assigned_rm_store':
                    # Validate rm_store user exists and has rm_store role
                    rm_store_id = request.data[field]
                    
                    # Handle empty string or None (clearing the rm_store user)
                    if not rm_store_id or rm_store_id == '':
                        mo.assigned_rm_store = None
                        updated_fields.append(field)
                    else:
                        try:
                            rm_store_user = User.objects.get(id=rm_store_id)
                            if not rm_store_user.user_roles.filter(role__name='rm_store').exists():
                                return Response(
                                    {'error': 'Selected user is not an RM store user'}, 
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            mo.assigned_rm_store = rm_store_user
                            updated_fields.append(field)
                        except User.DoesNotExist:
                            return Response(
                                {'error': 'RM store user not found'}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                elif field == 'assigned_supervisor':
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
                    message=f'Manufacturing Order {mo.mo_id} has been assigned to you. Product: {mo.product_code.product_code}, Quantity: {mo.quantity}',
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
        
        # Check current status - can only approve when RM is allocated
        if mo.status != 'rm_allocated':
            return Response(
                {'error': f'Cannot approve MO in {mo.status} status. MO must be in RM Allocated status to approve.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if supervisor is assigned
        if not mo.assigned_supervisor:
            return Response(
                {'error': 'Cannot approve MO without assigned supervisor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update MO status to in_progress and set actual start date
        old_status = mo.status
        mo.status = 'in_progress'
        mo.actual_start_date = timezone.now()
        mo.save()
        
        # Reduce RM quantities based on mo.rm_required_kg
        if mo.rm_required_kg > 0:
            try:
                from inventory.models import RawMaterial
                # Find the raw material associated with this MO's product
                raw_material = mo.product_code.material
                if raw_material and raw_material.quantity_on_hand >= mo.rm_required_kg:
                    raw_material.quantity_on_hand -= mo.rm_required_kg
                    raw_material.save()
                else:
                    return Response(
                        {'error': 'Insufficient raw material quantity available'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                return Response(
                    {'error': f'Error reducing RM quantity: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status='in_progress',
            changed_by=request.user,
            notes=request.data.get('notes', 'MO approved by manager - Production started')
        )
        
        # Create notification for supervisor
        from notifications.models import Alert, AlertRule
        
        # Create or get alert rule for production start notifications
        alert_rule, created = AlertRule.objects.get_or_create(
            name='Production Start Notification',
            alert_type='custom',
            defaults={
                'trigger_condition': {'event': 'production_started'},
                'notification_methods': ['in_app']
            }
        )
        
        # Create alert for supervisor
        Alert.objects.create(
            alert_rule=alert_rule,
            title=f'Production Started: {mo.mo_id}',
            message=f'Manufacturing Order {mo.mo_id} has been approved and production has started. You are assigned as supervisor. Product: {mo.product_code.product_code}, Quantity: {mo.quantity}',
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rm_approve(self, request, pk=None):
        """Approve MO for RM allocation (RM Store user only)"""
        mo = self.get_object()
        
        # Check if user is rm_store
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'rm_store' not in user_roles:
            return Response(
                {'error': 'Only RM store users can approve RM allocation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check current status - can only approve when on_hold
        if mo.status != 'on_hold':
            return Response(
                {'error': f'Cannot approve RM allocation for MO in {mo.status} status. MO must be in On Hold status.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if assigned to this rm_store user
        if mo.assigned_rm_store != request.user:
            return Response(
                {'error': 'You can only approve MOs assigned to you'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update MO status to rm_allocated
        old_status = mo.status
        mo.status = 'rm_allocated'
        mo.rm_allocated_at = timezone.now()
        mo.rm_allocated_by = request.user
        mo.save()
        
        # Create status history
        MOStatusHistory.objects.create(
            mo=mo,
            from_status=old_status,
            to_status='rm_allocated',
            changed_by=request.user,
            notes=request.data.get('notes', 'Raw materials verified and allocated by RM store')
        )
        
        serializer = ManufacturingOrderWithProcessesSerializer(mo)
        return Response({
            'message': 'RM allocation approved successfully!',
            'mo': serializer.data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def rm_store_dashboard(self, request):
        """Get MOs assigned to current RM Store user grouped by status"""
        # Check if user is rm_store
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'rm_store' not in user_roles:
            return Response(
                {'error': 'Only RM store users can access this dashboard'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get MOs assigned to this RM store user
        base_queryset = ManufacturingOrder.objects.filter(
            assigned_rm_store=request.user
        ).select_related(
            'product_code', 'product_code__customer_c_id', 'customer_c_id',
            'assigned_supervisor', 'created_by'
        ).prefetch_related('batches')
        
        # Separate by status
        on_hold_mos = base_queryset.filter(status='on_hold').order_by('-created_at')
        in_progress_mos = base_queryset.filter(status='in_progress').order_by('-created_at')
        # For RM Store, "completed" means rm_allocated or fully completed
        completed_mos = base_queryset.filter(status__in=['rm_allocated', 'completed']).order_by('-created_at')
        
        # Serialize data
        on_hold_serializer = ManufacturingOrderListSerializer(on_hold_mos, many=True)
        in_progress_serializer = ManufacturingOrderListSerializer(in_progress_mos, many=True)
        completed_serializer = ManufacturingOrderListSerializer(completed_mos, many=True)
        
        return Response({
            'summary': {
                'pending_approvals': on_hold_mos.count(),
                'in_progress': in_progress_mos.count(),
                'completed': completed_mos.count(),
                'total': base_queryset.count()
            },
            'on_hold': on_hold_serializer.data,
            'in_progress': in_progress_serializer.data,
            'completed': completed_serializer.data
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


class BatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Batch management - RM Store users can create batches
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mo', 'status', 'assigned_operator', 'assigned_supervisor']
    search_fields = ['batch_id', 'mo__mo_id', 'product_code__product_code']
    ordering_fields = ['created_at', 'planned_start_date', 'status', 'progress_percentage']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimized queryset with select_related and prefetch_related"""
        queryset = Batch.objects.select_related(
            'mo', 'product_code', 'assigned_operator', 'assigned_supervisor', 
            'created_by', 'current_process_step'
        ).prefetch_related('mo__product_code')
        
        # Filter by MO if specified
        mo_id = self.request.query_params.get('mo_id')
        if mo_id:
            queryset = queryset.filter(mo_id=mo_id)
        
        return queryset

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return BatchListSerializer
        return BatchDetailSerializer

    def perform_create(self, serializer):
        """Create batch - automatically handled by serializer"""
        serializer.save()

    @action(detail=False, methods=['get'], url_path='mo-batch-summary/(?P<mo_id>[^/.]+)')
    def mo_batch_summary(self, request, mo_id=None):
        """
        Get comprehensive batch summary for an MO including:
        - Total RM required for MO (with tolerance)
        - Cumulative RM released across all batches
        - Remaining RM that can be allocated
        - % completion based on batches
        """
        try:
            mo = ManufacturingOrder.objects.select_related('product_code').get(id=mo_id)
        except ManufacturingOrder.DoesNotExist:
            return Response(
                {'error': 'Manufacturing Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        product = mo.product_code
        
        # Calculate total RM required for entire MO
        total_rm_required = None
        rm_unit = None
        
        if product.material_type == 'coil' and product.grams_per_product:
            # For coil-based products (springs)
            total_grams = mo.quantity * product.grams_per_product
            base_rm_kg = Decimal(str(total_grams / 1000))
            
            # Apply tolerance
            tolerance = mo.tolerance_percentage or Decimal('2.00')
            tolerance_factor = Decimal('1') + (tolerance / Decimal('100'))
            total_rm_required = float(base_rm_kg * tolerance_factor)
            rm_unit = 'kg'
            
        elif product.material_type == 'sheet' and product.pcs_per_strip:
            # For sheet-based products (press components)
            strips_calc = product.calculate_strips_required(mo.quantity)
            total_rm_required = strips_calc.get('strips_required', 0)
            rm_unit = 'strips'
        
        # Get all batches for this MO
        batches = Batch.objects.filter(mo=mo).exclude(status='cancelled')
        
        # Calculate cumulative RM released and scrapped
        cumulative_rm_released = Decimal('0')
        cumulative_scrap_rm = Decimal('0')
        batch_details = []
        
        for batch in batches:
            batch_rm = Decimal('0')
            
            # NOTE: planned_quantity is now stored in GRAMS (not pieces)
            # User enters RM in kg, frontend converts to grams
            batch_quantity_grams = batch.planned_quantity
            
            # Convert grams to kg
            batch_rm_base_kg = Decimal(str(batch_quantity_grams / 1000))
            
            # Apply tolerance
            tolerance = mo.tolerance_percentage or Decimal('2.00')
            tolerance_factor = Decimal('1') + (tolerance / Decimal('100'))
            batch_rm = batch_rm_base_kg * tolerance_factor

            cumulative_rm_released += batch_rm
            
            # Add scrap RM (stored in grams)
            batch_scrap_kg = Decimal(str(batch.scrap_rm_weight / 1000))
            cumulative_scrap_rm += batch_scrap_kg
            
            batch_details.append({
                'batch_id': batch.batch_id,
                'planned_quantity': batch.planned_quantity,  # in grams
                'rm_base_kg': float(batch_rm_base_kg),
                'rm_released': float(batch_rm),
                'scrap_rm_kg': float(batch_scrap_kg),
                'status': batch.status,
                'created_at': batch.created_at
            })
        
        # Add MO-level scrap (remaining RM sent to scrap)
        mo_scrap_kg = Decimal(str(mo.scrap_rm_weight / 1000))
        
        # Calculate remaining and percentage
        remaining_rm = None
        completion_percentage = 0
        
        if total_rm_required is not None:
            # Remaining = Total - Released - Already scrapped at MO level
            remaining_rm = float(Decimal(str(total_rm_required)) - cumulative_rm_released - mo_scrap_kg)
            if remaining_rm < 0:
                remaining_rm = 0
            
            if total_rm_required > 0:
                completion_percentage = min(
                    100, 
                    float((cumulative_rm_released / Decimal(str(total_rm_required))) * Decimal('100'))
                )
        
        return Response({
            'mo_id': mo.mo_id,
            'mo_quantity': mo.quantity,
            'material_type': product.material_type,
            'total_rm_required': total_rm_required,
            'rm_unit': rm_unit,
            'cumulative_rm_released': float(cumulative_rm_released),
            'cumulative_scrap_rm': float(cumulative_scrap_rm),
            'mo_scrap_rm': float(mo_scrap_kg),
            'remaining_rm': remaining_rm,
            'completion_percentage': round(completion_percentage, 2),
            'batch_count': batches.count(),
            'batches': batch_details,
            'tolerance_percentage': float(mo.tolerance_percentage) if mo.tolerance_percentage else 2.00
        })
    
    @action(detail=True, methods=['post'], url_path='add-scrap-rm')
    def add_scrap_rm(self, request, pk=None):
        """
        Add scrap RM weight to a batch
        Expected payload: { "scrap_rm_kg": 1.5 }
        """
        batch = self.get_object()
        scrap_rm_kg = request.data.get('scrap_rm_kg')
        
        if scrap_rm_kg is None:
            return Response(
                {'error': 'scrap_rm_kg is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            scrap_rm_kg = float(scrap_rm_kg)
            if scrap_rm_kg < 0:
                return Response(
                    {'error': 'scrap_rm_kg must be non-negative'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'scrap_rm_kg must be a valid number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert kg to grams and add to existing scrap
        scrap_rm_grams = int(scrap_rm_kg * 1000)
        batch.scrap_rm_weight += scrap_rm_grams
        batch.save()
        
        serializer = self.get_serializer(batch)
        return Response({
            'message': f'Added {scrap_rm_kg} kg of scrap RM to batch {batch.batch_id}',
            'batch': serializer.data,
            'total_scrap_rm_kg': batch.scrap_rm_weight / 1000
        })
    
    @action(detail=False, methods=['get'])
    def by_mo(self, request):
        """Get batches for a specific MO"""
        mo_id = request.query_params.get('mo_id')
        if not mo_id:
            return Response(
                {'error': 'mo_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batches = self.get_queryset().filter(mo_id=mo_id)
        serializer = self.get_serializer(batches, many=True)
        
        # Calculate summary
        total_planned = sum(b.planned_quantity for b in batches)
        total_completed = sum(b.actual_quantity_completed for b in batches)
        
        return Response({
            'batches': serializer.data,
            'summary': {
                'total_batches': batches.count(),
                'total_planned_quantity': total_planned,
                'total_completed_quantity': total_completed,
                'completion_percentage': (total_completed / total_planned * 100) if total_planned > 0 else 0
            }
        })

    @action(detail=True, methods=['post'])
    def start_batch(self, request, pk=None):
        """Start a batch - updates status to in_process"""
        batch = self.get_object()
        
        if batch.status != 'created':
            return Response(
                {'error': 'Batch can only be started from created status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batch.status = 'in_process'
        batch.actual_start_date = timezone.now()
        batch.save()
        
        serializer = self.get_serializer(batch)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_batch(self, request, pk=None):
        """Complete a batch"""
        batch = self.get_object()
        data = request.data
        
        if batch.status not in ['in_process', 'quality_check']:
            return Response(
                {'error': 'Batch must be in process or quality check to complete'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batch.status = 'completed'
        batch.actual_end_date = timezone.now()
        batch.actual_quantity_completed = data.get('actual_quantity_completed', batch.planned_quantity)
        batch.scrap_quantity = data.get('scrap_quantity', 0)
        batch.progress_percentage = 100
        batch.save()
        
        # Check if MO is fully completed
        mo = batch.mo
        total_completed = sum(b.actual_quantity_completed for b in mo.batches.filter(status='completed'))
        if total_completed >= mo.quantity:
            mo.status = 'completed'
            mo.actual_end_date = timezone.now()
            mo.save()
            
            # Create status history
            MOStatusHistory.objects.create(
                mo=mo,
                from_status='in_progress',
                to_status='completed',
                changed_by=request.user,
                notes=f'MO completed with batch: {batch.batch_id}'
            )
        
        serializer = self.get_serializer(batch)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_progress(self, request, pk=None):
        """Update batch progress"""
        batch = self.get_object()
        data = request.data
        
        if 'progress_percentage' in data:
            progress = float(data['progress_percentage'])
            if not (0 <= progress <= 100):
                return Response(
                    {'error': 'Progress must be between 0 and 100'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            batch.progress_percentage = progress
        
        if 'actual_quantity_completed' in data:
            batch.actual_quantity_completed = data['actual_quantity_completed']
        
        if 'notes' in data:
            batch.notes = data['notes']
        
        batch.save()
        
        serializer = self.get_serializer(batch)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get batch statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'created': queryset.filter(status='created').count(),
            'in_process': queryset.filter(status='in_process').count(),
            'completed': queryset.filter(status='completed').count(),
            'overdue': sum(1 for batch in queryset if batch.is_overdue)
        }
        
        return Response(stats)
