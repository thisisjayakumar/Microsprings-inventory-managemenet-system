from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch
from django.db import transaction
from django.contrib.auth import get_user_model

from products.models import Product
from .models import RMStockBalance, RawMaterial
from .serializers import (
    ProductListSerializer, ProductCreateUpdateSerializer,
    RMStockBalanceSerializer, RMStockBalanceUpdateSerializer,
    ProductStockDashboardSerializer, RawMaterialBasicSerializer
)
from authentication.models import UserRole, Role

User = get_user_model()


class IsRMStoreUser(permissions.BasePermission):
    """
    Custom permission to only allow RM Store users to access inventory management
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has rm_store role
        try:
            user_roles = UserRole.objects.filter(
                user=request.user, 
                is_active=True,
                role__name='rm_store'
            ).exists()
            return user_roles
        except:
            return False


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product management - accessible by RM Store users
    """
    permission_classes = [IsAuthenticated, IsRMStoreUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_type', 'spring_type']
    search_fields = ['product_code', 'internal_product_code', 'material__material_name']
    ordering_fields = ['product_code', 'internal_product_code', 'created_at']
    ordering = ['internal_product_code']
    
    def get_queryset(self):
        """Optimized queryset with prefetch_related for stock balances"""
        return Product.objects.select_related('material', 'customer_c_id', 'created_by').prefetch_related(
            Prefetch('stock_balances', queryset=RMStockBalance.objects.all())
        )
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get products with stock information for RM Store dashboard"""
        products = self.get_queryset()
        serializer = ProductStockDashboardSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get products dropdown for selection"""
        products = Product.objects.all().order_by('internal_product_code')
        data = [
            {
                'id': product.id,
                'internal_product_code': product.internal_product_code,
                'product_code': product.product_code,
                'display_name': f"{product.internal_product_code} - {product.product_code}"
            }
            for product in products
        ]
        return Response(data)


class RMStockBalanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RMStockBalance management - accessible by RM Store users
    """
    permission_classes = [IsAuthenticated, IsRMStoreUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__product_code', 'product__internal_product_code']
    ordering_fields = ['available_quantity', 'last_updated']
    ordering = ['-last_updated']
    
    def get_queryset(self):
        """Optimized queryset with select_related"""
        return RMStockBalance.objects.select_related('product', 'product__material')
    
    def get_serializer_class(self):
        """Use RMStockBalanceSerializer for all operations"""
        return RMStockBalanceSerializer
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update stock balances using internal_product_code
        Expected payload: [{"internal_product_code": "ABC123", "available_quantity": 100}, ...]
        """
        serializer = RMStockBalanceUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            updated_records = []
            
            with transaction.atomic():
                for item in serializer.validated_data:
                    product = Product.objects.only("id").get(
                        internal_product_code=item['internal_product_code']
                    )
                    
                    # Use bulk_create with update_conflicts as requested
                    stock_balance, created = RMStockBalance.objects.update_or_create(
                        product=product,
                        defaults={'available_quantity': item['available_quantity']}
                    )
                    
                    updated_records.append({
                        'internal_product_code': item['internal_product_code'],
                        'available_quantity': stock_balance.available_quantity,
                        'created': created,
                        'last_updated': stock_balance.last_updated
                    })
            
            return Response({
                'message': f'Successfully updated {len(updated_records)} stock records',
                'updated_records': updated_records
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_by_product_code(self, request):
        """
        Update single stock balance using internal_product_code
        Expected payload: {"internal_product_code": "ABC123", "available_quantity": 100}
        """
        serializer = RMStockBalanceUpdateSerializer(data=request.data)
        if serializer.is_valid():
            product = Product.objects.only("id").get(
                internal_product_code=serializer.validated_data['internal_product_code']
            )
            
            # Use the requested bulk_create approach
            stock_balance, created = RMStockBalance.objects.update_or_create(
                product=product,
                defaults={'available_quantity': serializer.validated_data['available_quantity']}
            )
            
            return Response({
                'message': 'Stock balance updated successfully',
                'internal_product_code': serializer.validated_data['internal_product_code'],
                'available_quantity': stock_balance.available_quantity,
                'created': created,
                'last_updated': stock_balance.last_updated
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RawMaterialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for RawMaterial - for dropdown/selection purposes
    """
    permission_classes = [IsAuthenticated, IsRMStoreUser]
    queryset = RawMaterial.objects.all()
    serializer_class = RawMaterialBasicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['material_type', 'material_name']
    search_fields = ['material_code', 'material_name', 'grade']
    ordering_fields = ['material_code', 'material_name']
    ordering = ['material_code']
    
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get raw materials dropdown for product creation"""
        materials = self.get_queryset()
        data = [
            {
                'id': material.id,
                'material_code': material.material_code,
                'material_name': material.material_name,
                'material_type': material.material_type,
                'display_name': f"{material.material_code} - {material.material_name}"
            }
            for material in materials
        ]
        return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for inventory service
    """
    return Response({'status': 'healthy', 'message': 'Inventory service is running'})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsRMStoreUser])
def rm_store_dashboard_stats(request):
    """
    Get dashboard statistics for RM Store users
    """
    try:
        total_products = Product.objects.count()
        products_with_stock = RMStockBalance.objects.filter(available_quantity__gt=0).count()
        products_out_of_stock = RMStockBalance.objects.filter(available_quantity=0).count()
        products_no_stock_record = total_products - RMStockBalance.objects.count()
        
        return Response({
            'total_products': total_products,
            'products_with_stock': products_with_stock,
            'products_out_of_stock': products_out_of_stock,
            'products_no_stock_record': products_no_stock_record,
            'total_stock_records': RMStockBalance.objects.count()
        })
    except Exception as e:
        return Response(
            {'error': 'Failed to fetch dashboard stats', 'detail': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )