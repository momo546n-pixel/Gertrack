from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, LogoutView, ProfileView, AuditLogListView,
    AdminRequestViewSet, ProjectManagerViewSet, MagasinierAccountViewSet,
    AuditCenterViewSet,
)

router = DefaultRouter()
router.register('admin-requests', AdminRequestViewSet, basename='admin-request')
router.register('project-managers', ProjectManagerViewSet, basename='project-manager')
router.register('magasiniers', MagasinierAccountViewSet, basename='magasinier-account')
router.register('audit-center', AuditCenterViewSet, basename='audit-center')

urlpatterns = [
    path('login/',      CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/',     LogoutView.as_view(),                name='logout'),
    path('refresh/',    TokenRefreshView.as_view(),          name='token_refresh'),
    path('profile/',    ProfileView.as_view(),               name='profile'),
    path('audit-logs/', AuditLogListView.as_view(),          name='audit_logs'),
    path('', include(router.urls)),
]