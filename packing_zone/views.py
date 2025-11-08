from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    PackingBatch, PackingTransaction, LooseStock, MergedHeatNumber,
    MergeRequest, StockAdjustment, PackingLabel, FGStock
)
from .serializers import (
    PackingBatchListSerializer, PackingBatchDetailSerializer,
    PackingBatchCreateSerializer, PackingBatchVerifySerializer,
    PackingBatchReportSerializer, PackingTransactionListSerializer,
    PackingTransactionDetailSerializer, PackingTransactionCreateSerializer,
    LooseStockSerializer, MergedHeatNumberSerializer,
    MergeRequestListSerializer, MergeRequestDetailSerializer,
    MergeRequestCreateSerializer, MergeRequestApproveSerializer,
    MergeRequestRejectSerializer, StockAdjustmentListSerializer,
    StockAdjustmentDetailSerializer, StockAdjustmentCreateSerializer,
    StockAdjustmentApproveSerializer, StockAdjustmentRejectSerializer,
    PackingLabelSerializer, PackingLabelCreateSerializer,
    FGStockSerializer, PackingDashboardStatsSerializer
)
from .permissions import (
    IsPackingZoneUser, IsProductionHeadOrAdmin,
    IsManagerOrAbove, IsPackingZoneUserOrManagerAbove
)
from authentication.models import CustomUser
from products.models import Product


class PackingBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing packing batches
    - Packing Zone User: Full access
    - Production Head: Full access (for releasing holds)
    - Manager: Read-only access
    """
    queryset = PackingBatch.objects.all().select_related(
        'product', 'verified_by', 'released_by'
    )
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return PackingBatchListSerializer
        elif self.action in ['retrieve']:
            return PackingBatchDetailSerializer
        elif self.action in ['create']:
            return PackingBatchCreateSerializer
        elif self.action == 'verify':
            return PackingBatchVerifySerializer
        elif self.action == 'report_issue':
            return PackingBatchReportSerializer
        return PackingBatchDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        heat_no = self.request.query_params.get('heat_no')
        if heat_no:
            queryset = queryset.filter(heat_no=heat_no)
        
        mo_id = self.request.query_params.get('mo_id')
        if mo_id:
            queryset = queryset.filter(mo_id=mo_id)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a batch"""
        batch = self.get_object()
        
        if batch.status != 'to_be_verified':
            return Response(
                {'error': 'Only batches in to_be_verified status can be verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batch.verify(request.user)
        serializer = PackingBatchDetailSerializer(batch)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def report_issue(self, request, pk=None):
        """Report an issue with a batch"""
        batch = self.get_object()
        serializer = PackingBatchReportSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        batch.report_issue(
            reason=serializer.validated_data['reason'],
            notes=serializer.validated_data.get('notes', ''),
            actual_kg=serializer.validated_data.get('actual_kg')
        )
        
        response_serializer = PackingBatchDetailSerializer(batch)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductionHeadOrAdmin])
    def release_from_hold(self, request, pk=None):
        """Release batch from hold (PH only)"""
        batch = self.get_object()
        
        if batch.status != 'on_hold':
            return Response(
                {'error': 'Only batches on hold can be released'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batch.release_from_hold(request.user)
        serializer = PackingBatchDetailSerializer(batch)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def to_be_packed(self, request):
        """Get batches ready to be packed (verified status)"""
        batches = self.get_queryset().filter(status='verified')
        
        # Group by product and heat number
        grouped = {}
        for batch in batches:
            key = f"{batch.product_code}_{batch.heat_no}"
            if key not in grouped:
                grouped[key] = {
                    'product_code': batch.product_code,
                    'ipc': batch.ipc,
                    'heat_no': batch.heat_no,
                    'grams_per_product': batch.grams_per_product,
                    'packing_size': batch.packing_size,
                    'batches': [],
                    'total_kg': Decimal('0.000')
                }
            grouped[key]['batches'].append({
                'id': batch.id,
                'mo_id': batch.mo_id,
                'available_kg': batch.available_quantity_kg
            })
            grouped[key]['total_kg'] += batch.available_quantity_kg
        
        return Response(list(grouped.values()))


class PackingTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing packing transactions
    - Packing Zone User: Full access
    - Production Head: Full access
    - Manager: Read-only access
    """
    queryset = PackingTransaction.objects.all().select_related(
        'product', 'packed_by'
    ).prefetch_related('batches')
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return PackingTransactionListSerializer
        elif self.action in ['retrieve']:
            return PackingTransactionDetailSerializer
        elif self.action in ['create']:
            return PackingTransactionCreateSerializer
        return PackingTransactionDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        heat_no = self.request.query_params.get('heat_no')
        if heat_no:
            queryset = queryset.filter(heat_no=heat_no)
        
        # Date filters
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(packed_date__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(packed_date__date__lte=end_date)
        
        # User filter (for personal activity log)
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(packed_by_id=user_id)
        elif self.request.query_params.get('my_transactions') == 'true':
            queryset = queryset.filter(packed_by=self.request.user)
        
        return queryset.order_by('-packed_date')
    
    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        """Get current user's packing transactions"""
        transactions = self.get_queryset().filter(packed_by=request.user)
        
        # Filter by date if provided
        today = request.query_params.get('today') == 'true'
        if today:
            transactions = transactions.filter(packed_date__date=date.today())
        
        serializer = PackingTransactionListSerializer(transactions, many=True)
        return Response(serializer.data)


class LooseStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing loose stock
    - Packing Zone User: Full access
    - Production Head: Full access
    - Manager: Read-only access
    """
    queryset = LooseStock.objects.all().select_related('product')
    serializer_class = LooseStockSerializer
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        heat_no = self.request.query_params.get('heat_no')
        if heat_no:
            queryset = queryset.filter(heat_no=heat_no)
        
        # Filter old stock (>50 days)
        old_only = self.request.query_params.get('old_only')
        if old_only == 'true':
            cutoff_date = timezone.now() - timedelta(days=50)
            queryset = queryset.filter(first_added_date__lt=cutoff_date)
        
        return queryset.order_by('product_code', 'heat_no')
    
    @action(detail=False, methods=['get'])
    def old_stock(self, request):
        """Get loose stock older than 50 days (for merge eligibility)"""
        cutoff_date = timezone.now() - timedelta(days=50)
        old_stock = self.get_queryset().filter(
            first_added_date__lt=cutoff_date,
            loose_kg__gt=0
        )
        
        # Group by product
        grouped = {}
        for stock in old_stock:
            if stock.product_code not in grouped:
                grouped[stock.product_code] = {
                    'product_code': stock.product_code,
                    'ipc': stock.ipc,
                    'stocks': []
                }
            grouped[stock.product_code]['stocks'].append({
                'id': stock.id,
                'heat_no': stock.heat_no,
                'loose_kg': stock.loose_kg,
                'loose_pieces': stock.loose_pieces,
                'age_days': stock.age_days
            })
        
        return Response(list(grouped.values()))


class MergeRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing merge requests
    - Packing Zone User: Create and view own requests
    - Production Head: Approve/reject requests
    - Manager: Read-only access
    """
    queryset = MergeRequest.objects.all().select_related(
        'product', 'requested_by', 'reviewed_by', 'merged_heat_number'
    )
    
    def get_permissions(self):
        """Dynamic permissions based on action"""
        if self.action in ['approve', 'reject']:
            return [IsProductionHeadOrAdmin()]
        return [IsPackingZoneUserOrManagerAbove()]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return MergeRequestListSerializer
        elif self.action in ['retrieve']:
            return MergeRequestDetailSerializer
        elif self.action in ['create']:
            return MergeRequestCreateSerializer
        elif self.action == 'approve':
            return MergeRequestApproveSerializer
        elif self.action == 'reject':
            return MergeRequestRejectSerializer
        return MergeRequestDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        # User filter
        user = self.request.user
        active_role = user.user_roles.filter(is_active=True).select_related('role').first()
        
        if active_role and active_role.role.name == 'packing_zone':
            # Packing users see only their own requests
            queryset = queryset.filter(requested_by=user)
        
        return queryset.order_by('-requested_date')
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductionHeadOrAdmin])
    def approve(self, request, pk=None):
        """Approve merge request (PH only)"""
        merge_request = self.get_object()
        serializer = MergeRequestApproveSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if merge_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve and create merged heat number
        merged = merge_request.approve(
            request.user,
            serializer.validated_data['merged_heat_no']
        )
        
        # Update loose stock - remove individual heat numbers and add merged
        for heat_data in merge_request.heat_numbers_data:
            try:
                loose = LooseStock.objects.get(
                    product_code=merge_request.product_code,
                    heat_no=heat_data['heat_no']
                )
                loose.reduce_loose(
                    Decimal(str(heat_data['kg'])),
                    heat_data['pieces']
                )
                # Delete if empty
                if loose.loose_kg <= 0:
                    loose.delete()
            except LooseStock.DoesNotExist:
                pass
        
        # Create new loose stock with merged heat number
        LooseStock.objects.create(
            product_code=merge_request.product_code,
            product=merge_request.product,
            ipc=merge_request.ipc,
            heat_no=merged.merged_heat_no,
            loose_kg=merge_request.total_kg,
            loose_pieces=merge_request.total_pieces,
            grams_per_product=merge_request.heat_numbers_data[0].get('grams_per_product', 0)
        )
        
        response_serializer = MergeRequestDetailSerializer(merge_request)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductionHeadOrAdmin])
    def reject(self, request, pk=None):
        """Reject merge request (PH only)"""
        merge_request = self.get_object()
        serializer = MergeRequestRejectSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if merge_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        merge_request.reject(
            request.user,
            serializer.validated_data.get('notes', '')
        )
        
        response_serializer = MergeRequestDetailSerializer(merge_request)
        return Response(response_serializer.data)


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stock adjustments
    - Packing Zone User: Create and view own adjustments
    - Production Head: Approve/reject adjustments
    - Manager: Read-only access
    """
    queryset = StockAdjustment.objects.all().select_related(
        'product', 'requested_by', 'reviewed_by'
    )
    
    def get_permissions(self):
        """Dynamic permissions based on action"""
        if self.action in ['approve', 'reject']:
            return [IsProductionHeadOrAdmin()]
        return [IsPackingZoneUserOrManagerAbove()]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return StockAdjustmentListSerializer
        elif self.action in ['retrieve']:
            return StockAdjustmentDetailSerializer
        elif self.action in ['create']:
            return StockAdjustmentCreateSerializer
        elif self.action == 'approve':
            return StockAdjustmentApproveSerializer
        elif self.action == 'reject':
            return StockAdjustmentRejectSerializer
        return StockAdjustmentDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        # User filter
        user = self.request.user
        active_role = user.user_roles.filter(is_active=True).select_related('role').first()
        
        if active_role and active_role.role.name == 'packing_zone':
            # Packing users see only their own adjustments
            queryset = queryset.filter(requested_by=user)
        
        return queryset.order_by('-requested_date')
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductionHeadOrAdmin])
    def approve(self, request, pk=None):
        """Approve stock adjustment (PH only)"""
        adjustment = self.get_object()
        
        if adjustment.status != 'pending':
            return Response(
                {'error': 'Only pending adjustments can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update loose stock
        try:
            loose_stock = LooseStock.objects.get(
                product_code=adjustment.product_code,
                ipc=adjustment.ipc,
                heat_no=adjustment.heat_no
            )
            loose_stock.reduce_loose(
                adjustment.adjustment_kg,
                adjustment.adjustment_pieces
            )
            
            # Delete if empty
            if loose_stock.loose_kg <= 0:
                loose_stock.delete()
        except LooseStock.DoesNotExist:
            return Response(
                {'error': 'Loose stock not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        adjustment.approve(request.user)
        serializer = StockAdjustmentDetailSerializer(adjustment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductionHeadOrAdmin])
    def reject(self, request, pk=None):
        """Reject stock adjustment (PH only)"""
        adjustment = self.get_object()
        serializer = StockAdjustmentRejectSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if adjustment.status != 'pending':
            return Response(
                {'error': 'Only pending adjustments can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        adjustment.reject(
            request.user,
            serializer.validated_data.get('notes', '')
        )
        
        response_serializer = StockAdjustmentDetailSerializer(adjustment)
        return Response(response_serializer.data)


class PackingLabelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing packing labels
    - Packing Zone User: Create and view labels
    - Production Head: Full access
    - Manager: Read-only access
    """
    queryset = PackingLabel.objects.all().select_related(
        'product', 'printed_by', 'merged_heat_no', 'packing_transaction'
    )
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return PackingLabelCreateSerializer
        return PackingLabelSerializer
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        ipc = self.request.query_params.get('ipc')
        if ipc:
            queryset = queryset.filter(ipc=ipc)
        
        heat_no = self.request.query_params.get('heat_no')
        if heat_no:
            queryset = queryset.filter(heat_no=heat_no)
        
        # Date filters
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(printed_date__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(printed_date__date__lte=end_date)
        
        return queryset.order_by('-printed_date')
    
    @action(detail=True, methods=['post'])
    def reprint(self, request, pk=None):
        """Reprint a label"""
        label = self.get_object()
        label.reprint()
        serializer = PackingLabelSerializer(label)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def traceability_export(self, request):
        """Export traceability data (PH and Manager)"""
        # Get filter params
        mo_id = request.query_params.get('mo_id')
        customer_name = request.query_params.get('customer_name')
        product_code = request.query_params.get('product_code')
        ipc = request.query_params.get('ipc')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if mo_id:
            # Filter through packing transaction
            queryset = queryset.filter(packing_transaction__batches__mo_id=mo_id)
        
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        if ipc:
            queryset = queryset.filter(ipc=ipc)
        
        if start_date:
            queryset = queryset.filter(printed_date__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(printed_date__date__lte=end_date)
        
        serializer = PackingLabelSerializer(queryset, many=True)
        return Response(serializer.data)


class FGStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing FG stock
    - Packing Zone User: Full access
    - Production Head: Full access
    - Manager: Read-only access
    """
    queryset = FGStock.objects.all().select_related('product')
    serializer_class = FGStockSerializer
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    def get_queryset(self):
        """Filter queryset based on query params"""
        queryset = super().get_queryset()
        
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        
        heat_no = self.request.query_params.get('heat_no')
        if heat_no:
            queryset = queryset.filter(heat_no=heat_no)
        
        return queryset.order_by('product_code', 'heat_no')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get FG stock summary grouped by product"""
        queryset = self.get_queryset()
        
        # Group by product
        summary = {}
        for stock in queryset:
            if stock.product_code not in summary:
                summary[stock.product_code] = {
                    'product_code': stock.product_code,
                    'ipc': stock.ipc,
                    'total_packs': 0,
                    'by_heat_no': []
                }
            summary[stock.product_code]['total_packs'] += stock.total_packs
            summary[stock.product_code]['by_heat_no'].append({
                'heat_no': stock.heat_no,
                'packs': stock.total_packs,
                'packing_size': stock.packing_size
            })
        
        return Response(list(summary.values()))


class PackingDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for packing zone dashboard statistics
    """
    permission_classes = [IsPackingZoneUserOrManagerAbove]
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dashboard statistics"""
        stats = {
            'to_be_verified': PackingBatch.objects.filter(status='to_be_verified').count(),
            'verified': PackingBatch.objects.filter(status='verified').count(),
            'on_hold': PackingBatch.objects.filter(status='on_hold').count(),
            'packed_today': PackingTransaction.objects.filter(
                packed_date__date=date.today()
            ).count(),
            'pending_merge_requests': MergeRequest.objects.filter(status='pending').count(),
            'pending_adjustments': StockAdjustment.objects.filter(status='pending').count(),
            'total_loose_kg': LooseStock.objects.aggregate(
                total=Sum('loose_kg')
            )['total'] or Decimal('0.000'),
            'total_fg_packs': FGStock.objects.aggregate(
                total=Sum('total_packs')
            )['total'] or 0,
        }
        
        serializer = PackingDashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def product_list(self, request):
        """Get list of products for dropdown"""
        products = Product.objects.filter(is_active=True).values(
            'id', 'product_code', 'product_name', 'internal_product_code'
        )
        return Response(products)

