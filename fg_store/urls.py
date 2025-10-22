from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dispatch-batches', views.DispatchBatchViewSet)
router.register(r'dispatch-transactions', views.DispatchTransactionViewSet)
router.register(r'stock-alerts', views.FGStockAlertViewSet)
router.register(r'dispatch-orders', views.DispatchOrderViewSet)
router.register(r'dashboard', views.FGStoreDashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
