from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProcessViewSet, SubProcessViewSet, ProcessStepViewSet, BOMViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'processes', ProcessViewSet, basename='process')
router.register(r'subprocesses', SubProcessViewSet, basename='subprocess')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'bom', BOMViewSet, basename='bom')

app_name = 'processes'

urlpatterns = [
    path('api/', include(router.urls)),
]

# Available API endpoints:
"""
Processes:
- GET    /api/processes/                    - List all processes (with filtering, search, pagination)
- POST   /api/processes/                    - Create new process
- GET    /api/processes/{id}/               - Get specific process details
- PUT    /api/processes/{id}/               - Update process
- PATCH  /api/processes/{id}/               - Partial update process
- DELETE /api/processes/{id}/               - Delete process
- GET    /api/processes/dropdown/           - Get processes dropdown
- GET    /api/processes/{id}/subprocesses/  - Get subprocesses for specific process
- GET    /api/processes/{id}/process_steps/ - Get process steps for specific process

SubProcesses:
- GET    /api/subprocesses/                 - List all subprocesses (with filtering, search, pagination)
- POST   /api/subprocesses/                 - Create new subprocess
- GET    /api/subprocesses/{id}/            - Get specific subprocess details
- PUT    /api/subprocesses/{id}/            - Update subprocess
- PATCH  /api/subprocesses/{id}/            - Partial update subprocess
- DELETE /api/subprocesses/{id}/            - Delete subprocess
- GET    /api/subprocesses/dropdown/        - Get subprocesses dropdown (optionally filtered by process)
- GET    /api/subprocesses/{id}/process_steps/ - Get process steps for specific subprocess

Process Steps:
- GET    /api/process-steps/                - List all process steps (with filtering, search, pagination)
- POST   /api/process-steps/                - Create new process step
- GET    /api/process-steps/{id}/           - Get specific process step details
- PUT    /api/process-steps/{id}/           - Update process step
- PATCH  /api/process-steps/{id}/           - Partial update process step
- DELETE /api/process-steps/{id}/           - Delete process step
- GET    /api/process-steps/dropdown/       - Get process steps dropdown (optionally filtered by process/subprocess)
- GET    /api/process-steps/{id}/bom_items/ - Get BOM items for specific process step

BOM (Bill of Materials):
- GET    /api/bom/                          - List all BOM items (with filtering, search, pagination)
- POST   /api/bom/                          - Create new BOM item
- GET    /api/bom/{id}/                     - Get specific BOM item details
- PUT    /api/bom/{id}/                     - Update BOM item
- PATCH  /api/bom/{id}/                     - Partial update BOM item
- DELETE /api/bom/{id}/                     - Delete BOM item
- GET    /api/bom/by_product/               - Get BOM items by product code and type
- GET    /api/bom/raw_materials/            - Get raw materials dropdown
- GET    /api/bom/dashboard_stats/          - Get BOM dashboard statistics

Query Parameters for Filtering:
Processes:
- is_active: true/false
- code: integer
- search: searches in name, code, description
- ordering: name, code, created_at (add - for descending)

SubProcesses:
- process: process_id
- search: searches in name, description, process__name
- ordering: name, created_at, process__name (add - for descending)

Process Steps:
- process: process_id
- subprocess: subprocess_id
- search: searches in step_name, step_code, description, process__name, subprocess__name
- ordering: step_name, sequence_order, created_at (add - for descending)

BOM:
- type: spring, stamp
- process_step: process_step_id
- material: material_id
- is_active: true/false
- search: searches in product_code, process_step__step_name, process_step__process__name, material__product_code, material__material_name
- ordering: product_code, type, created_at (add - for descending)

Example API Calls:
1. Create Process:
   POST /api/processes/
   {
     "name": "Spring Manufacturing",
     "code": 100,
     "description": "Complete spring manufacturing process",
     "is_active": true
   }

2. Create SubProcess:
   POST /api/subprocesses/
   {
     "process": 1,
     "name": "Wire Drawing",
     "description": "Drawing wire to required diameter"
   }

3. Create Process Step:
   POST /api/process-steps/
   {
     "step_name": "Initial Wire Preparation",
     "step_code": "WP001",
     "process": 1,
     "subprocess": 1,
     "sequence_order": 1,
     "description": "Prepare wire for drawing process"
   }

4. Create BOM Item:
   POST /api/bom/
   {
     "product_code": "SPR-001",
     "type": "spring",
     "process_step": 1,
     "material_id": 1,
     "is_active": true
   }

5. Get BOM by Product:
   GET /api/bom/by_product/?product_code=SPR-001&type=spring

6. Get Subprocesses for Process:
   GET /api/subprocesses/dropdown/?process_id=1

7. Get Process Steps for Subprocess:
   GET /api/process-steps/dropdown/?subprocess_id=1

8. Get filtered Process Steps:
   GET /api/process-steps/?process=1&ordering=sequence_order

9. Search Processes:
   GET /api/processes/?search=spring&is_active=true

10. Get BOM Dashboard Stats:
    GET /api/bom/dashboard_stats/
"""
