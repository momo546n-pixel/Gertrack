from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/',       include('apps.accounts.urls')),
    path('api/accounts/',   include('apps.accounts.urls')),
    path('api/products/',   include('apps.products.urls')),
    path('api/suppliers/',  include('apps.suppliers.urls')),
    path('api/stock/',      include('apps.stock.urls')),
    path('api/operations/', include('apps.operations.urls')),
    path('api/requests/',   include('apps.requests.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)