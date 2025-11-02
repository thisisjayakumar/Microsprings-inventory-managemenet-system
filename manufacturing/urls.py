from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ManufacturingOrderViewSet, PurchaseOrderViewSet,
    MOProcessExecutionViewSet, MOProcessStepExecutionViewSet, MOProcessAlertViewSet,
    BatchViewSet, OutsourcingRequestViewSet, RawMaterialAllocationViewSet,
    # Workflow API views
    create_mo_workflow, approve_mo, allocate_rm_to_mo, assign_process_to_operator,
    reassign_process, allocate_batch_to_process, receive_batch_by_operator,
    complete_process, verify_finished_goods,
    # Heat number API
    get_available_heat_numbers_for_mo
)
from .views.batch_views import BatchProcessExecutionViewSet
from .views.additional_rm_views import AdditionalRMRequestViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'manufacturing-orders', ManufacturingOrderViewSet, basename='manufacturingorder')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'process-executions', MOProcessExecutionViewSet, basename='processexecution')
router.register(r'step-executions', MOProcessStepExecutionViewSet, basename='stepexecution')
router.register(r'process-alerts', MOProcessAlertViewSet, basename='processalert')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'batch-process-executions', BatchProcessExecutionViewSet, basename='batchprocessexecution')
router.register(r'outsourcing', OutsourcingRequestViewSet, basename='outsourcingrequest')
router.register(r'rm-allocations', RawMaterialAllocationViewSet, basename='rmallocation')
router.register(r'additional-rm-requests', AdditionalRMRequestViewSet, basename='additionalrmrequest')

app_name = 'manufacturing'

urlpatterns = [
    path('', include(router.urls)),
    
    # Enhanced Workflow API endpoints
    path('workflow/create-mo/', create_mo_workflow, name='create_mo_workflow'),
    path('workflow/approve-mo/', approve_mo, name='approve_mo'),
    path('workflow/allocate-rm/', allocate_rm_to_mo, name='allocate_rm_to_mo'),
    path('workflow/assign-process/', assign_process_to_operator, name='assign_process_to_operator'),
    path('workflow/reassign-process/', reassign_process, name='reassign_process'),
    path('workflow/allocate-batch/', allocate_batch_to_process, name='allocate_batch_to_process'),
    path('workflow/receive-batch/', receive_batch_by_operator, name='receive_batch_by_operator'),
    path('workflow/complete-process/', complete_process, name='complete_process'),
    path('workflow/verify-fg/', verify_finished_goods, name='verify_finished_goods'),
    
    # Heat number management
    path('manufacturing-orders/<int:mo_id>/available-heat-numbers/', get_available_heat_numbers_for_mo, name='get_available_heat_numbers_for_mo'),
]

# Available API endpoints:
"""
Enhanced Manufacturing Workflow:
- POST   /api/workflow/create-mo/                    - Create MO and initialize approval workflow
- POST   /api/workflow/approve-mo/                    - Manager approves MO
- POST   /api/workflow/allocate-rm/                   - RM Store allocates raw materials to MO
- POST   /api/workflow/assign-process/                - Production Head assigns process to operator
- POST   /api/workflow/reassign-process/              - Production Head reassigns process to different operator
- POST   /api/workflow/allocate-batch/                - RM Store allocates batch to specific process
- POST   /api/workflow/receive-batch/                 - Operator receives batch and starts process
- POST   /api/workflow/complete-process/              - Operator completes process
- POST   /api/workflow/verify-fg/                     - Quality check for finished goods

Manufacturing Orders:
- GET    /api/manufacturing-orders/                    - List all MOs (with filtering, search, pagination)
- POST   /api/manufacturing-orders/                    - Create new MO
- GET    /api/manufacturing-orders/{id}/               - Get specific MO details
- PUT    /api/manufacturing-orders/{id}/               - Update MO
- PATCH  /api/manufacturing-orders/{id}/               - Partial update MO
- DELETE /api/manufacturing-orders/{id}/               - Delete MO
- POST   /api/manufacturing-orders/{id}/change_status/ - Change MO status
- GET    /api/manufacturing-orders/dashboard_stats/    - Get dashboard statistics
- GET    /api/manufacturing-orders/products/           - Get products dropdown
- GET    /api/manufacturing-orders/supervisors/        - Get supervisors dropdown

Purchase Orders:
- GET    /api/purchase-orders/                         - List all POs (with filtering, search, pagination)
- POST   /api/purchase-orders/                         - Create new PO
- GET    /api/purchase-orders/{id}/                    - Get specific PO details
- PUT    /api/purchase-orders/{id}/                    - Update PO
- PATCH  /api/purchase-orders/{id}/                    - Partial update PO
- DELETE /api/purchase-orders/{id}/                    - Delete PO
- POST   /api/purchase-orders/{id}/change_status/      - Change PO status
- GET    /api/purchase-orders/dashboard_stats/         - Get dashboard statistics

Outsourcing Requests:
- GET    /api/outsourcing/                             - List all outsourcing requests (with filtering, search, pagination)
- POST   /api/outsourcing/                             - Create new outsourcing request
- GET    /api/outsourcing/{id}/                        - Get specific outsourcing request details
- PUT    /api/outsourcing/{id}/                        - Update outsourcing request
- PATCH  /api/outsourcing/{id}/                        - Partial update outsourcing request
- DELETE /api/outsourcing/{id}/                        - Delete outsourcing request
- POST   /api/outsourcing/{id}/send/                   - Send outsourcing request (creates OUT inventory transactions)
- POST   /api/outsourcing/{id}/return_items/          - Mark request as returned (creates IN inventory transactions)
- POST   /api/outsourcing/{id}/close/                  - Close outsourcing request
- GET    /api/outsourcing/summary/                     - Get outsourcing summary statistics

Note: For raw materials and vendors dropdowns, use the existing APIs:
- Raw Materials: GET /api/inventory/raw-materials/ (from inventory app)
- Vendors: GET /api/third-party/vendors/?vendor_type=outsource_vendor (from third_party app)
Both APIs return complete data, so no separate detail endpoints are needed.

Query Parameters for Filtering:
Manufacturing Orders:
- status: draft, submitted, gm_approved, rm_allocated, in_progress, completed, cancelled, on_hold
- priority: low, medium, high, urgent
- shift: I, II, III
- material_type: coil, sheet
- assigned_supervisor: user_id
- start_date: YYYY-MM-DD
- end_date: YYYY-MM-DD
- search: searches in mo_id, product_code, part_number, customer_order_reference
- ordering: created_at, planned_start_date, delivery_date, mo_id (add - for descending)

Purchase Orders:
- status: draft, submitted, gm_approved, gm_created_po, vendor_confirmed, partially_received, completed, cancelled, rejected
- material_type: coil, sheet
- vendor_name: vendor_id
- expected_date: YYYY-MM-DD
- start_date: YYYY-MM-DD
- end_date: YYYY-MM-DD
- search: searches in po_id, rm_code, vendor_name
- ordering: created_at, expected_date, po_id, total_amount (add - for descending)

Outsourcing Requests:
- status: draft, sent, returned, closed
- vendor: vendor_id
- created_by: user_id
- search: searches in request_id, vendor__name, vendor_contact_person
- ordering: created_at, expected_return_date, date_sent (add - for descending)

Example API Calls:
1. Create MO:
   POST /api/manufacturing-orders/
   {
     "product_code_id": 1,
     "quantity": 100,
     "assigned_supervisor_id": 2,
     "shift": "I",
     "planned_start_date": "2024-01-15T09:00:00Z",
     "planned_end_date": "2024-01-20T17:00:00Z",
     "priority": "high",
     "delivery_date": "2024-01-25"
   }

2. Create PO:
   POST /api/purchase-orders/
   {
     "rm_code_id": 1,
     "vendor_name_id": 1,
     "quantity_ordered": 500,
     "expected_date": "2024-01-30",
     "unit_price": "25.50"
   }

3. Change MO Status:
   POST /api/manufacturing-orders/1/change_status/
   {
     "status": "gm_approved",
     "notes": "Approved by GM for immediate production"
   }

4. Get filtered MOs:
   GET /api/manufacturing-orders/?status=in_progress&priority=high&ordering=-created_at

5. Get dashboard stats:
   GET /api/manufacturing-orders/dashboard_stats/
   GET /api/purchase-orders/dashboard_stats/

6. Create Outsourcing Request:
   POST /api/outsourcing/
   {
     "vendor_id": 1,
     "expected_return_date": "2024-02-15",
     "vendor_contact_person": "John Smith",
     "notes": "Coating process",
     "items_data": [
       {
         "mo_number": "MO-20240115-0001",
         "product_code": "SPRING-001",
         "qty": 1000,
         "kg": 5.5,
         "notes": "Coating required"
       }
     ]
   }

7. Send Outsourcing Request:
   POST /api/outsourcing/1/send/
   {
     "date_sent": "2024-01-20",
     "vendor_contact_person": "John Smith"
   }

8. Mark Request as Returned:
   POST /api/outsourcing/1/return_items/
   {
     "collection_date": "2024-02-10",
     "collected_by_id": 2,
     "returned_items": [
       {
         "id": 1,
         "returned_qty": 1000,
         "returned_kg": 5.5
       }
     ]
   }

9. Get Outsourcing Summary:
   GET /api/outsourcing/summary/
"""
