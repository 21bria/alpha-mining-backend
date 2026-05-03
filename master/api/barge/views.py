from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from core.permissions import GlobalMasterPermission
from master.models import BargeUnits
from rest_framework.permissions import IsAuthenticated
from .serializers import BargeUnitsSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class BargeUnitsViewSet(MasterBaseViewSet):
    queryset = BargeUnits.objects.all().order_by("barge_name")
    serializer_class = BargeUnitsSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["barge_code","barge_name", "description","active"]
    ordering_fields  = ["id","barge_code" ,"barge_name"]

    export_fields    = ["id","barge_code" ,"barge_name", "description"]
    template_headers = ["barge_code","barge_name", "description"]

    soft_delete_field = None


    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "Barge_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Barge_import_template.xlsx"
        )