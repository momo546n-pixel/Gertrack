from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TaskViewSet, WeeklyReportViewSet

router = DefaultRouter()
router.register('projects', ProjectViewSet,     basename='project')
router.register('tasks',    TaskViewSet,         basename='task')
router.register('reports',  WeeklyReportViewSet, basename='weekly-report')

urlpatterns = router.urls