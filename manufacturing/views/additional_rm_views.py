"""
API Views for Additional RM Request functionality
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from ..models.additional_rm import AdditionalRMRequest
from ..serializers.additional_rm_serializers import (
    AdditionalRMRequestListSerializer,
    AdditionalRMRequestDetailSerializer,
    CreateAdditionalRMRequestSerializer,
    ApproveAdditionalRMRequestSerializer,
    RejectAdditionalRMRequestSerializer,
    MarkCompleteAdditionalRMRequestSerializer
)
from ..models.manufacturing_order import ManufacturingOrder


class AdditionalRMRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Additional RM Requests
    
    Permissions:
    - RM Store: Can create, view, and mark complete
    - Manager: Can view, approve, and reject
    - Production Head: Can view only
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'mo', 'requested_by', 'approved_by']
    search_fields = ['request_id', 'mo__mo_id', 'reason']
    ordering_fields = ['requested_at', 'approved_at', 'status']
    ordering = ['-requested_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AdditionalRMRequestListSerializer
        elif self.action in ['create', 'request_additional_rm']:
            return CreateAdditionalRMRequestSerializer
        elif self.action == 'approve':
            return ApproveAdditionalRMRequestSerializer
        elif self.action == 'reject':
            return RejectAdditionalRMRequestSerializer
        elif self.action == 'mark_complete':
            return MarkCompleteAdditionalRMRequestSerializer
        return AdditionalRMRequestDetailSerializer
    
    def get_queryset(self):
        """
        Filter queryset based on user role
        - RM Store: Can see all requests
        - Manager: Can see all requests
        - Production Head: Can see all requests (view only)
        - Others: Can see their own MO requests
        """
        user = self.request.user
        user_roles = user.user_roles.values_list('role__name', flat=True)
        
        # Managers, RM Store, and Production Heads can see all requests
        if any(role in user_roles for role in ['manager', 'rm_store', 'production_head']):
            return AdditionalRMRequest.objects.select_related(
                'mo', 'mo__product_code', 'excess_batch',
                'requested_by', 'approved_by', 'rejected_by', 'marked_complete_by'
            ).all()
        
        # Others can only see requests for their MOs
        return AdditionalRMRequest.objects.select_related(
            'mo', 'mo__product_code', 'excess_batch',
            'requested_by', 'approved_by', 'rejected_by', 'marked_complete_by'
        ).filter(mo__created_by=user)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new additional RM request
        Only RM Store users can create requests
        """
        # Check if user is RM Store
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'rm_store' not in user_roles:
            return Response(
                {'error': 'Only RM Store users can create additional RM requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_obj = serializer.save()
        
        # Return detail serializer
        detail_serializer = AdditionalRMRequestDetailSerializer(request_obj)
        
        return Response(
            {
                'message': 'Additional RM request created successfully',
                'request': detail_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Approve an additional RM request
        Only Managers can approve
        """
        # Check if user is Manager
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'manager' not in user_roles:
            return Response(
                {'error': 'Only Managers can approve additional RM requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        request_obj = self.get_object()
        
        if request_obj.status != 'pending':
            return Response(
                {'error': f'Cannot approve request in {request_obj.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(
            data=request.data,
            context={'request_obj': request_obj}
        )
        serializer.is_valid(raise_exception=True)
        
        # Approve the request
        try:
            request_obj.approve(
                manager_user=request.user,
                approved_quantity_kg=serializer.validated_data['approved_quantity_kg'],
                notes=serializer.validated_data.get('approval_notes', '')
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return updated request
        detail_serializer = AdditionalRMRequestDetailSerializer(request_obj)
        
        return Response({
            'message': 'Additional RM request approved successfully',
            'request': detail_serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Reject an additional RM request
        Only Managers can reject
        """
        # Check if user is Manager
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'manager' not in user_roles:
            return Response(
                {'error': 'Only Managers can reject additional RM requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        request_obj = self.get_object()
        
        if request_obj.status != 'pending':
            return Response(
                {'error': f'Cannot reject request in {request_obj.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Reject the request
        try:
            request_obj.reject(
                manager_user=request.user,
                reason=serializer.validated_data['rejection_reason']
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return updated request
        detail_serializer = AdditionalRMRequestDetailSerializer(request_obj)
        
        return Response({
            'message': 'Additional RM request rejected',
            'request': detail_serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """
        Mark an additional RM request as complete
        Only RM Store users can mark complete
        """
        # Check if user is RM Store
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        if 'rm_store' not in user_roles:
            return Response(
                {'error': 'Only RM Store users can mark requests as complete'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        request_obj = self.get_object()
        
        if request_obj.status != 'approved':
            return Response(
                {'error': f'Cannot mark request as complete in {request_obj.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if can be marked complete (30-minute delay logic)
        if not request_obj.can_mark_complete:
            return Response(
                {
                    'error': 'Cannot mark as complete yet. The excess batch must complete the next process and 30 minutes must pass.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Mark as complete
        try:
            request_obj.mark_complete(
                rm_store_user=request.user,
                notes=serializer.validated_data.get('completion_notes', '')
            )
            
            # Update MO completion status
            mo = request_obj.mo
            mo.rm_completion_status = 'completed'
            mo.save()
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return updated request
        detail_serializer = AdditionalRMRequestDetailSerializer(request_obj)
        
        return Response({
            'message': 'Additional RM request marked as complete. MO moved to completed tab.',
            'request': detail_serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """
        Get all pending additional RM requests (for Manager/PH approval tab)
        """
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        
        if not any(role in user_roles for role in ['manager', 'production_head']):
            return Response(
                {'error': 'Only Managers and Production Heads can view pending approvals'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_requests = self.get_queryset().filter(status='pending')
        serializer = AdditionalRMRequestListSerializer(pending_requests, many=True)
        
        return Response({
            'count': pending_requests.count(),
            'requests': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='by-mo/(?P<mo_id>[^/.]+)')
    def by_mo(self, request, mo_id=None):
        """
        Get all additional RM requests for a specific MO
        """
        try:
            mo = ManufacturingOrder.objects.get(id=mo_id)
        except ManufacturingOrder.DoesNotExist:
            return Response(
                {'error': 'Manufacturing Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        requests = self.get_queryset().filter(mo=mo)
        serializer = AdditionalRMRequestListSerializer(requests, many=True)
        
        return Response({
            'mo_id': mo.mo_id,
            'mo_rm_summary': mo.get_rm_summary(),
            'requests': serializer.data
        })

