from rest_framework import filters
from core.permissions import GlobalMasterPermission
from geology.models import ProductionsConfig
from rest_framework.permissions import IsAuthenticated
from .serializers import ProductionConfigSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class ProductionConfigViewSet(MasterBaseViewSet):
    queryset = ProductionsConfig.objects.all().order_by("key")
    serializer_class = ProductionConfigSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]


    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["key","value","is_active"]
    ordering_fields  = ["id", "key"]


    soft_delete_field = None


