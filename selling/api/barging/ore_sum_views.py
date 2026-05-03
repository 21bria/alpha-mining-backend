from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from master.models import SellingCode
from selling.services.barging_adjustment import get_barging_totals_by_code


class TonnageByCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code_lot = request.query_params.get("code_lot")
        code_lot_id = request.query_params.get("code_lot_id")

        if not code_lot and not code_lot_id:
            return Response(
                {"detail": "code_lot or code_lot_id is required"},
                status=400,
            )

        selling_code = None

        # kalau kirim id
        if code_lot_id:
            try:
                selling_code = (
                    SellingCode.objects
                    .only("id", "code")
                    .get(pk=code_lot_id)
                )
            except SellingCode.DoesNotExist:
                return Response(
                    {"detail": f"SellingCode with id={code_lot_id} not found"},
                    status=404,
                )

            code_lot = str(selling_code.code).strip()

        # kalau kirim code string
        else:
            code_lot = str(code_lot).strip()
            selling_code = (
                SellingCode.objects
                .only("id", "code")
                .filter(code__iexact=code_lot)
                .first()
            )

        totals = get_barging_totals_by_code(code_lot)

        return Response({
            "code_lot_id": getattr(selling_code, "id", None),
            "code_lot": code_lot,
            "total_tonnage": float(totals["tonnage"]),
            "total_ritase": totals["ritase"],
        })