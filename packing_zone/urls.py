from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PackingBatchViewSet, PackingTransactionViewSet, LooseStockViewSet,
    MergeRequestViewSet, StockAdjustmentViewSet, PackingLabelViewSet,
    FGStockViewSet, PackingDashboardViewSet
)

router = DefaultRouter()
router.register(r'batches', PackingBatchViewSet, basename='packing-batch')
router.register(r'transactions', PackingTransactionViewSet, basename='packing-transaction')
router.register(r'loose-stock', LooseStockViewSet, basename='loose-stock')
router.register(r'merge-requests', MergeRequestViewSet, basename='merge-request')
router.register(r'adjustments', StockAdjustmentViewSet, basename='stock-adjustment')
router.register(r'labels', PackingLabelViewSet, basename='packing-label')
router.register(r'fg-stock', FGStockViewSet, basename='fg-stock')
router.register(r'dashboard', PackingDashboardViewSet, basename='packing-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]

