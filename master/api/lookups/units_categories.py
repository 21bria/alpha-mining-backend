from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from master.models import unitsCategories
from master.api.lookups.base import BaseLookupViewSet

class UnitsCategoriesLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = unitsCategories.objects.all().order_by("category")

    # search
    search_fields = ["category__icontains", "description__icontains"]

    # fleksibel keys
    allowed_value_keys = {"id", "category"}
    allowed_label_keys = {"category", "category"}

    default_value_key = "id"
    default_label_key = "category"

class UnitsCategoriesListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        qs = unitsCategories.objects.all().order_by("category")

        search = request.GET.get("search")
        if search:
            qs = qs.filter(category__icontains=search)

        data = [
            {
                "id": row.id,
                "category": row.category,
                "label": row.category,
                "value": row.id,
            }
            for row in qs
        ]

        return Response({
            "success": True,
            "list": data
        })