from django.urls import path, include
from rest_framework.routers import DefaultRouter

from analytics.api.export_views import ExportJobDownloadView
from .export_job_views import ExportJobDetailView

from analytics.api.sample_crm.views import sampleCrmRoaviewSet
from analytics.api.sample_crm.views_mral import sampleCrmMralviewSet

from analytics.api.sample_duplicated.views import sampleDupRoaviewSet
from analytics.api.sample_duplicated.views_mral import sampleDupMralviewSet

from analytics.api.bod_weekly.views import BodWeeklyReportViewSet,BodWeeklyDocumentViewSet


router = DefaultRouter()

router.register(r"sample-crm-roa", sampleCrmRoaviewSet, basename="sample-crm-roa")
router.register(r"sample-crm-mral", sampleCrmMralviewSet, basename="sample-crm-mral")

router.register(r"sample-duplicated-roa", sampleDupRoaviewSet, basename="sample-duplicated-roa")
router.register(r"sample-duplicated-mral", sampleDupMralviewSet, basename="sample-duplicated-mral")

router.register(r"bod-weekly-report",BodWeeklyReportViewSet,basename="bod-weekly-report")

router.register(r"bod-weekly-document", BodWeeklyDocumentViewSet,basename="bod-weekly-document")

urlpatterns = [
    path("export-jobs/<uuid:pk>/",ExportJobDetailView.as_view(),name="report-export-job-detail"),
    path( "export-jobs/<uuid:pk>/download/",ExportJobDownloadView.as_view(),name="report-export-job-download"),

    path("", include(router.urls)),
]