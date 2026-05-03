from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    # Accounts App
    path("api/auth/", include("accounts.api.urls")),
    # Master App
    path("api/master/", include("master.api.urls")),
    # Geology App
    path("api/geology/", include("geology.api.urls")),
    path('api/geology/raw/', include('geology.urls')),
    # Mining App
    path("api/mining/", include("mining.api.urls")),
    # Selling App
    path("api/selling/", include("selling.api.urls")),
    # Imports App
    path("api/tasks/", include("imports.api.urls")),
    # analytics App
    path('api/analytics/', include('analytics.api.urls')),
    path('api/analytics/raw/', include('analytics.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)