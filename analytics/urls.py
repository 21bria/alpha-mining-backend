from django.urls import path, include

urlpatterns = [
    path('mining/', include('analytics.views.mining.urls')),
    path('mining/daily/', include('analytics.views.daily.urls')),
    path('geology/', include('analytics.views.geology.urls')),
    path('barging/', include('analytics.views.barging.urls')),
    path('inventory/', include('analytics.views.inventory.urls')),
    path('fuel/', include('analytics.views.fuel.urls')),
    path('weather/', include('analytics.views.weather.urls')),
    path('compile/', include('analytics.views.compile.urls')),

    # GIS
    path('gis/', include('analytics.views.gis.urls')),

    # Ai
    path("ai/", include("analytics.views.ai.urls")),
]