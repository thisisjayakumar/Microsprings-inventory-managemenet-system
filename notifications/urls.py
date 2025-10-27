from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowNotificationViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'workflow-notifications', WorkflowNotificationViewSet, basename='workflownotification')

app_name = 'notifications'

urlpatterns = [
    path('api/', include(router.urls)),
]

# Available API endpoints:
"""
Workflow Notifications API:

- GET    /api/workflow-notifications/                           - List user's workflow notifications
- GET    /api/workflow-notifications/{id}/                      - Get specific workflow notification
- POST   /api/workflow-notifications/{id}/mark_as_read/         - Mark notification as read
- POST   /api/workflow-notifications/{id}/mark_action_taken/    - Mark action as taken

Query Parameters:
- notification_type: Filter by type (e.g., supervisor_assigned, rm_allocation_required)
- is_read: Filter by read status (true/false)
- action_required: Filter by action required status (true/false)
- priority: Filter by priority (low, medium, high, urgent)

Example API Calls:
1. Get unread notifications:
   GET /api/workflow-notifications/?is_read=false

2. Mark notification as read:
   POST /api/workflow-notifications/1/mark_as_read/

3. Get action required notifications:
   GET /api/workflow-notifications/?action_required=true
"""
