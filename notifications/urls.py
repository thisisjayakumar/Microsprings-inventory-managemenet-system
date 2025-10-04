from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlertViewSet, AlertRuleViewSet, NotificationLogViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'alert-rules', AlertRuleViewSet, basename='alertrule')
router.register(r'notification-logs', NotificationLogViewSet, basename='notificationlog')

app_name = 'notifications'

urlpatterns = [
    path('api/', include(router.urls)),
]

# Available API endpoints:
"""
Notifications:
- GET    /api/alerts/                           - List user's alerts
- GET    /api/alerts/my_notifications/          - Get active notifications for current user
- GET    /api/alerts/unread_count/              - Get count of unread notifications
- POST   /api/alerts/{id}/acknowledge/          - Acknowledge an alert
- POST   /api/alerts/{id}/dismiss/              - Dismiss an alert
- GET    /api/alert-rules/                      - List alert rules (Manager only)
- POST   /api/alert-rules/                      - Create alert rule (Manager only)
- GET    /api/notification-logs/                - List user's notification delivery logs

Example API Calls:
1. Get my notifications:
   GET /api/alerts/my_notifications/

2. Acknowledge alert:
   POST /api/alerts/1/acknowledge/

3. Get unread count:
   GET /api/alerts/unread_count/
"""
