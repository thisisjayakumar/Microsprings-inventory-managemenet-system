from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ManufacturingOrderViewSet, PurchaseOrderViewSet,
    MOProcessExecutionViewSet, MOProcessStepExecutionViewSet, MOProcessAlertViewSet,
    BatchViewSet
)
from .batch_process_views import BatchProcessExecutionViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'manufacturing-orders', ManufacturingOrderViewSet, basename='manufacturingorder')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'process-executions', MOProcessExecutionViewSet, basename='processexecution')
router.register(r'step-executions', MOProcessStepExecutionViewSet, basename='stepexecution')
router.register(r'process-alerts', MOProcessAlertViewSet, basename='processalert')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'batch-process-executions', BatchProcessExecutionViewSet, basename='batchprocessexecution')

app_name = 'manufacturing'

urlpatterns = [
    path('api/', include(router.urls)),
]

# Available API endpoints:
"""
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

Note: For raw materials and vendors dropdowns, use the existing APIs:
- Raw Materials: GET /api/inventory/raw-materials/ (from inventory app)
- Vendors: GET /api/third-party/vendors/?vendor_type=rm_vendor (from third_party app)
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
"""
