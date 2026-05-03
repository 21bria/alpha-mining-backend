from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from core.permissions import GlobalMasterPermission
from master.models import SellingSurveyor
from rest_framework.permissions import IsAuthenticated
from .serializers import SellingSurveyorSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class SellingSurveyorViewSet(MasterBaseViewSet):
    queryset = SellingSurveyor.objects.all().order_by("name_surveyor")
    serializer_class = SellingSurveyorSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["code_surveyor","name_surveyor", "description","status"]
    ordering_fields  = ["id","code_surveyor" ,"name_surveyor"]

    export_fields    = ["id","code_surveyor" ,"name_surveyor", "description"]
    template_headers = ["code_surveyor","name_surveyor", "description"]

    soft_delete_field = None


    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "Surveyor_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Surveyor_import_template.xlsx"
        )