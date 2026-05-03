from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny

from geology.services.ore_production_service import get_tonnage_by_dome


class TonnageByDomeAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dome_id = request.query_params.get("dome_id")

        if not dome_id:
            return Response({"detail": "dome_id is required"}, status=400)

        try:
            dome_id = int(dome_id)
        except ValueError:
            return Response({"detail": "dome_id must be integer"}, status=400)

        total = get_tonnage_by_dome(dome_id)

        return Response({
            "dome_id": dome_id,
            "total_tonnage": total
        })