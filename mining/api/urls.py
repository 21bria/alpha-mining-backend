from django.urls import path, include
from rest_framework.routers import DefaultRouter

from mining.api.productions.summary import CompareSummaryView
from mining.api.plan_production.views import planProductionViewSet
from mining.api.plan_barging.views import planBargingViewSet
from mining.api.productions.views import ProductionsViewSet,ProductionsViewCRUDSet
from mining.api.fuel.views import FuelConsumptionViewSet,FuelConsumptionViewCRUDSet
from mining.api.weather.views import WeatherViewSet,WeatherCategoryLookupViewSet
from mining.api.rainfall.views import RainfallPointViewSet,RainfallViewSet
from mining.api.fill_factor.views import FillFactorViewSet
from mining.api.units_activity.views import HmUnitViewSet


router = DefaultRouter()
router.register(r"plan-production", planProductionViewSet, basename="plan-production")
router.register(r"plan-barging", planBargingViewSet, basename="plan-barging")
router.register(r"productions", ProductionsViewSet, basename="productions")
router.register(r"productions-crud", ProductionsViewCRUDSet, basename="productions-crud")
router.register(r"fuel-daily", FuelConsumptionViewSet, basename="fuel-daily")
router.register(r"fuel-daily-crud", FuelConsumptionViewCRUDSet, basename="fuel-daily-crud")
router.register(r"daily-weather", WeatherViewSet, basename="daily-weather")
router.register(r"weather-category", WeatherCategoryLookupViewSet, basename="weather-category")
router.register(r"daily-rainfall", RainfallViewSet, basename="rainfall")
router.register(r"rainfall-points", RainfallPointViewSet, basename="rainfall-points")
router.register(r"fill-factor", FillFactorViewSet, basename="fill-factor")
router.register(r"unit-activity", HmUnitViewSet, basename="units_activity")

urlpatterns = [
    path("production-summary/", CompareSummaryView.as_view(), name="production-summary",),
    *router.urls,
]