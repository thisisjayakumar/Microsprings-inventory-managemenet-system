from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatrolDutyViewSet,
    PatrolUploadViewSet,
    PatrolAlertViewSet,
    PatrolDashboardViewSet
)

router = DefaultRouter()
router.register(r'duties', PatrolDutyViewSet, basename='patrol-duty')
router.register(r'uploads', PatrolUploadViewSet, basename='patrol-upload')
router.register(r'alerts', PatrolAlertViewSet, basename='patrol-alert')
router.register(r'dashboard', PatrolDashboardViewSet, basename='patrol-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]

