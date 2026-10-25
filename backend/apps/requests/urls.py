from rest_framework.routers import DefaultRouter
from .views import UnifiedRequestViewSet, LogisticsStageViewSet, RALBudgetViewSet

router = DefaultRouter()
router.register('logistics-stages', LogisticsStageViewSet, basename='logistics-stage')
router.register('ral-budget', RALBudgetViewSet, basename='ral-budget')
router.register('', UnifiedRequestViewSet, basename='unified-request')

urlpatterns = router.urls