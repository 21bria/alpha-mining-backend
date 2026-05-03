from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from master.api.division.views import DivisionViewSet

router = DefaultRouter()
# router.register(r"divisions", DivisionViewSet, basename="masters-divisions")


urlpatterns = [
    path("lookups/", include("master.api.lookups.urls")),  # call urls lookups ini penting
    *router.urls,
]