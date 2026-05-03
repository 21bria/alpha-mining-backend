from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from core.permissions import GlobalMasterPermission
from master.models import StockFactories
from rest_framework.permissions import IsAuthenticated
from .serializers import StockFactoriesSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class StockFactoriesViewSet(MasterBaseViewSet):
    queryset = StockFactories.objects.all().order_by("factory_stock")
    serializer_class = StockFactoriesSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["factory_stock", "description"]
    ordering_fields  = ["id", "factory_stock"]

    export_fields    = ["id", "factory_stock", "description"]
    template_headers = ["factory_stock", "description"]

    soft_delete_field = None


    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "Stock_factories_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Stock_factories_import_template.xlsx"
        )