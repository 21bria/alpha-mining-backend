from django.urls import path, include

urlpatterns = [
    path('inventory/', include('geology.views.inventory.urls')),
    # path('production/', include('geology.views.production.urls')),
]