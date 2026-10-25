from .views import WarehouseViewSet
from rest_framework.routers import DefaultRouter
from .views import StockMovementViewSet



router = DefaultRouter()
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('movements', StockMovementViewSet, basename='stock-movement')

urlpatterns = router.urls